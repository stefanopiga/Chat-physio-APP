# Sezione 6: Componenti

### 6.1 Componenti Frontend
*   **Authentication Component**: Gestisce i flussi di login/logout interagendo con `Supabase Auth`.
*   **Chat Interface Component**: UI principale per la conversazione RAG.
*   **Admin Panel Component**: UI per la gestione dei codici e la sincronizzazione.
*   **Multi-API Service**: Astrae le chiamate sia all'API di Supabase (per Auth/CRUD) che all'API custom FastAPI (per RAG).

### 6.2 Componenti Backend (FastAPI)
*   **Web API Layer**: Espone gli endpoint `openapi.yml` e valida gli input.
*   **Chat Service (RAG Core)**: Orchestra il processo di ricerca vettoriale e generazione della risposta utilizzando una **LangChain Chain** (costruita con LCEL - LangChain Expression Language).
*   **Ingestion Service**: Gestisce la pipeline asincrona di indicizzazione dei documenti. Dopo Story 6.1 include:
    * Watcher file-system che usa `DocumentExtractor` (PyMuPDF/python-docx) e classificazione LLM controllata dal flag `WATCHER_ENABLE_CLASSIFICATION`.
    * Routing chunking intelligente (`recursive_character_800_160` vs `tabular_structural`) con fallback supervisionato e metriche in `api.ingestion.watcher_metrics` (latency, success/failure, fallback ratio, cache hit-rate).
    * API Sync Jobs manuale invariata, con feature parity rispetto al watcher e indexazione su Supabase.
*   **Data Access Layer (DAL)**: Gestisce le query vettoriali verso Supabase invocando direttamente la RPC `match_document_chunks`, serializzando manualmente gli embedding calcolati con `OpenAIEmbeddings`.
*   **Task Queue (Reliability)**: Celery con Redis come broker e result backend, per l'esecuzione affidabile di job di ingestion/indexing con retry, backoff e tracciamento stato (`PENDING/STARTED/SUCCESS/FAILURE/RETRY`). Vedi addendum HNSW & Async per dettagli operativi.

> Vedi anche: [Addendum: Supabase pgvector & LangChain VectorStore](addendum-pgvector-langchain-supabase.md) per SQL (estensione, tabella, funzione `match_documents`, indici HNSW/IVFFlat) e integrazione `SupabaseVectorStore`/`OpenAIEmbeddings`.
>
> Per la gestione job asincroni e affidabilità dei processi di indicizzazione, vedi [Addendum: Parametri HNSW e Stack Asincrono](addendum-hnsw-params-and-async.md) (sez. 4–5).


## Sezione 6.3: Agente LLM di Pre-Processing Documenti (Classificazione + Chunking)

Questa sezione descrive il componente che, durante l’ingestione, identifica la natura di **documenti accademici e medici** per determinare la strategia di chunking ottimale. L’implementazione si basa su LangChain, con `PydanticOutputParser` per imporre uno schema rigoroso sull’output del modello.

### 6.3.1 Schema di Classificazione (PydanticOutputParser)

Fonte: [How to use output parsers to parse an LLM response into structured format](https://python.langchain.com/docs/how_to/output_parser_structured/), [link sospetto rimosso].

```python
from pydantic import BaseModel, Field, model_validator
from langchain_core.output_parsers import PydanticOutputParser

class Classification(BaseModel):
    classificazione: str = Field(description="classe assegnata al documento (es. TESTO_ACCADEMICO_DENSO)")
    motivazione: str = Field(description="spiegazione concisa della classificazione")
    confidenza: float = Field(description="valore tra 0 e 1")

    @model_validator(mode="before")
    @classmethod
    def check_confidence(cls, values: dict) -> dict:
        c = values.get("confidenza")
        if c is not None and not (0.0 <= c <= 1.0):
            raise ValueError("confidenza fuori range [0,1]")
        return values

parser = PydanticOutputParser(pydantic_object=Classification)
```

### 6.3.2 Integrazione nel PromptTemplate

Le istruzioni di formattazione del parser vengono iniettate nel prompt, specializzato per l'analisi di materiale di studio.

Fonte: [How to use output parsers to parse an LLM response into structured format](https://python.langchain.com/docs/how_to/output_parser_structured/), [link sospetto rimosso].

```python
from langchain_core.prompts import PromptTemplate

format_instructions = parser.get_format_instructions()

prompt = PromptTemplate(
    template=(
        "Sei un esperto nell'analizzare documenti accademici e medici.\n"
        "Classifica il testo fornito secondo una delle categorie definite.\n"
        "Considera la presenza di testo denso, tabelle, elenchi e figure.\n"
        "Rispetta rigorosamente il seguente schema JSON:\n{format_instructions}\n\n"
        "Testo da analizzare:\n{documento}\n"
    ),
    input_variables=["documento"],
    partial_variables={"format_instructions": format_instructions},
)
```

### 6.3.3 Catena LCEL e Modello

Composizione LCEL: `prompt | llm | parser`.

Fonte: [How to use output parsers to parse an LLM response into structured format](https://python.langchain.com/docs/how_to/output_parser_structured/), [link sospetto rimosso].

```python
from langchain_openai import OpenAI

# Un modello instruct è adatto per compiti di classificazione diretta
model = OpenAI(model_name="gpt-3.5-turbo-instruct", temperature=0.0)

chain = prompt | model | parser
```

### 6.3.4 Esecuzione End-to-End (Funzione di utilità)

Esecuzione end-to-end: input stringa (testo del documento), output oggetto Pydantic validato.

```python
# (Le definizioni di Pydantic, Parser, Prompt e Chain sono le stesse delle sezioni precedenti)

def classifica_documento_accademico(testo: str) -> Classification:
    """Invoca la catena di classificazione per materiale di studio."""
    return chain.invoke({"documento": testo})

# Esempio:
# testo_sbobina = "La mitosi è un processo di divisione cellulare..."
# output = classifica_documento_accademico(testo_sbobina)
# print(output)  # Oggetto Pydantic validato (Classification)
```

### 6.3.5 Uso nel Processo di Ingestion

- La `classificazione` guida la scelta dello splitter: `RecursiveCharacterTextSplitter` per `TESTO_ACCADEMICO_DENSO`, uno splitter più sofisticato (es. basato su tabelle o sezioni) per `PAPER_SCIENTIFICO_MISTO`.
- La `confidenza` (< 0.70) può attivare un fallback a una strategia di chunking più generica e sicura.
- La `motivazione` è registrata in `Document.metadata` per audit e debugging.

---



### 6.3.6 Endpoint di Classificazione (FastAPI + LangChain)

Implementazione dell'endpoint `/classify` che utilizza la catena LangChain per classificare il testo e restituisce un output Pydantic validato.

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field, confloat
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser

# 1. Definizione del Modello Pydantic per l'output
class ClassificazioneOutput(BaseModel):
    classificazione: str = Field(description="La categoria del documento (es. PAPER_SCIENTIFICO_MISTO)")
    motivazione: str = Field(description="Spiegazione della classificazione basata sul contenuto")
    confidenza: confloat(ge=0, le=1) = Field(description="Livello di confidenza da 0.0 a 1.0")

# 2. Creazione della Catena LangChain
def create_classification_chain():
    parser = PydanticOutputParser(pydantic_object=ClassificazioneOutput)
    prompt = PromptTemplate(
        template=(
            "Classifica il seguente documento di studio medico/accademico secondo una delle seguenti categorie: "
            "[TESTO_ACCADEMICO_DENSO, PAPER_SCIENTIFICO_MISTO, DOCUMENTO_TABELLARE].\n"
            "Spiega brevemente la motivazione della tua scelta.\n"
            "Rispetta rigorosamente il seguente schema JSON:\n{format_instructions}\n\n"
            "Testo:\n{testo}\n"
        ),
        input_variables=["testo"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return prompt | llm | parser

chain = create_classification_chain()

# 3. Creazione dell'Applicazione FastAPI
app = FastAPI()
class ClassificationInput(BaseModel):
    testo: str

@app.post("/classify", response_model=ClassificazioneOutput)
async def classify_document(payload: ClassificationInput) -> ClassificazioneOutput:
    result = chain.invoke({"testo": payload.testo})
    # log_model_as_json(result)
    return result
```

### 6.3.7 Logging Strutturato dell'Output di Classificazione

Registrazione dell'output come JSON pulito tramite Pydantic per un facile monitoraggio.

```python
import logging
from pydantic import BaseModel

def log_model_as_json(model: BaseModel) -> None:
    """Registra un modello Pydantic come stringa JSON."""
    logger = logging.getLogger("app")
    # Assumendo che il logger sia già configurato per output JSON
    logger.info(model.model_dump_json())

# Esempio d'uso
# classification_result = ClassificazioneOutput(...)
# log_model_as_json(classification_result)
```

### 6.3.8 Categorie Minime di Classificazione (Contesto Medico/Universitario)

- **TESTO_ACCADEMICO_DENSO**: Per sbobine, capitoli di libri o testi con prevalenza di prosa continua.
- **PAPER_SCIENTIFICO_MISTO**: Per articoli o documenti che contengono un mix significativo di testo, tabelle, elenchi e riferimenti a figure.
- **DOCUMENTO_TABELLARE**: Per documenti composti quasi esclusivamente da tabelle, come appendici di dati o risultati di laboratorio.

### 6.3.9 Testing: Mock della Catena LCEL

Esempio di test dell'endpoint `/classify` che simula la risposta della catena per una categoria specifica.

```python
from fastapi.testclient import TestClient
from main import app, ClassificazioneOutput
import main

def test_classify_endpoint_for_paper(mocker):
    """Testa la classificazione di un paper scientifico misto."""
    mock_result = ClassificazioneOutput(
        classificazione="PAPER_SCIENTIFICO_MISTO",
        motivazione="Il testo contiene paragrafi, una tabella e riferimenti a figure.",
        confidenza=0.98
    )
    mocker.patch.object(main.chain, "invoke", return_value=mock_result)

    client = TestClient(app)
    response = client.post("/classify", json={"testo": "..."})

    assert response.status_code == 200
    assert response.json()["classificazione"] == "PAPER_SCIENTIFICO_MISTO"
```

### 6.3.10 Classification Cache (Story 2.9)

Per ridurre la latenza della pipeline di ingestion, Story 2.9 introduce un layer di caching Redis per i risultati di classificazione.
- **Storage**: Redis DB isolato (default DB 1) con namespace `classification:v1:{sha256}`.
- **Configurazione**: flag `CLASSIFICATION_CACHE_ENABLED`, TTL `CLASSIFICATION_CACHE_TTL_SECONDS` (default 7 giorni), opzionale `CLASSIFICATION_CACHE_REDIS_URL`.
- **Fallback**: se Redis non e' raggiungibile, la funzione degrada a LLM diretto (`classification_cache_error` log).
- **Osservabilita'**: eventi `classification_cache_hit/miss`, metriche p50/p95 esposte su `GET /api/v1/admin/knowledge-base/classification-cache/metrics`.
- **Invalidazione**: endpoint admin `DELETE /api/v1/admin/knowledge-base/classification-cache/{digest}` per cancellare entry specifiche e `DELETE /api/v1/admin/knowledge-base/classification-cache` per flush completo.

## Sezione 6.4: Batch Ingestion Client (Story 2.10)

Story 2.10 introduce lo script `scripts/ingestion/ingest_all_documents.py` per processare in blocco la knowledge base locale. Le linee guida operative sono consolidate nel documento interno [Documentazione Tecnica per Story 2.10](../reports/Documentazione-Tecnica-per-Story2.10.md); questa sezione ne riassume i requisiti architetturali chiave e li collega alle fonti ufficiali.

### 6.4.1 Rate limiting e retry lato client

- L'endpoint `/api/v1/admin/knowledge-base/sync-jobs` e' protetto da Traefik e SlowAPI. La configurazione gateway (vedi `docker-compose.yml:44-46`) applica media 30 req/min con burst 10, mentre il router documenta il limite SlowAPI di 10 req/min (vedi `apps/api/api/routers/knowledge_base.py:213`).
- Traefik e SlowAPI non inviano l'header `Retry-After`; il client deve quindi combinare throttle proattivo (sleep ~6-7 secondi fra call) con exponential backoff + full jitter quando riceve 429 o errori di rete. Fonte: [RFC 6585, sezione 4](https://datatracker.ietf.org/doc/html/rfc6585), [AWS Architecture Blog - Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/).
- In presenza di header `Retry-After` (future evoluzioni) va rispettato il valore server. In assenza, adottare `delay = min(60, 2**attempt * base_delay + random_jitter)` come da esempio nello script di riferimento.

### 6.4.2 Stato persistente e ripresa run

- Il flag CLI `--state-file` abilita la ripresa idempotente. Lo stato deve essere scritto con operazione atomica: scrittura su file temporaneo nella stessa directory e `os.replace()` finale (pattern documentato in [Python tempfile](https://docs.python.org/3/library/tempfile.html) e [ActiveState Safe Atomic Write](https://code.activestate.com/recipes/579097-safely-and-atomically-write-to-a-file/)).
- Lo stato memorizza elenco file processati, fallimenti e timestamp; aggiornare lo snapshot dopo blocchi logici (es. ogni 10 file) per minimizzare riesecuzioni.

### 6.4.3 Parsing resiliente dei documenti

- L'estrazione da `.docx` deve intercettare `docx.opc.exceptions.PackageNotFoundError`, `PermissionError` e generiche `Exception` per evitare che un singolo file corrotto interrompa il batch. Referenza: [python-docx API](https://python-docx.readthedocs.io/en/latest/api/document.html) e issue [python-openxml #758](https://github.com/python-openxml/python-docx/issues/758).
- Lo script deve loggare il file saltato e aggiornare il report finale (`--report`) includendo la causa.

### 6.4.4 Osservabilita' e reporting

- Log strutturati per ogni file: esito (`success`/`skipped`/`failed`), `job_id`, numero chunk inseriti (se disponibile), latenza totale e tentativi. I log seguono il formato JSON line gia' adottato dal backend (`apps/api/api/knowledge_base/indexer.py`).
- Il report finale (AC3) produce `reports/batch_ingestion_report.md` piu' output CSV/JSON con gli stessi campi dei log per facilitare audit.

### 6.4.5 Riferimenti chiave

- Documento interno: [Documentazione Tecnica per Story 2.10](../reports/Documentazione-Tecnica-per-Story2.10.md).
- RFC 6585 - 429 Too Many Requests.
- AWS Architecture Blog - Exponential Backoff and Jitter.
- Python tempfile documentation e ActiveState Safe Atomic Write.
- python-docx API e relative issue note.
