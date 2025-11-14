# Addendum Architetturale: Gestione Errori per Servizi Esterni

**Versione:** 1.0  
**Data:** 2025-10-06  
**Stato:** Standard di Progetto  

---

## Sommario Esecutivo

Questa guida definisce gli standard obbligatori per la gestione degli errori nell'interazione con servizi esterni (API, database, vector store). L'obiettivo è prevenire fallimenti silenziosi e garantire diagnosticabilità immediata in caso di errore.

**Principio cardine:** Nessuna operazione I/O verso servizi esterni deve essere eseguita senza un blocco di gestione errori appropriato.

---

## 1. Principi Generali

### 1.1 Regola Fondamentale

Ogni chiamata a un servizio esterno DEVE essere protetta da un blocco `try...except` che:

1. Catturi le eccezioni specifiche del servizio (non solo `Exception`)
2. Registri l'errore con livello di log appropriato
3. Fornisca contesto diagnostico sufficiente (parametri della chiamata, stato dell'operazione)
4. Gestisca il fallimento in modo esplicito (raise, retry, fallback)

### 1.2 Antipattern da Evitare

**NON FARE:**

```python
# ❌ Errore silenzioso
try:
    result = external_service.call()
except:
    pass

# ❌ Logging insufficiente
try:
    result = external_service.call()
except Exception as e:
    logger.error("Errore")
    
# ❌ Cattura generica senza specificità
try:
    result = external_service.call()
except Exception:
    raise
```

**FARE:**

```python
# ✅ Gestione esplicita con logging diagnostico
try:
    result = external_service.call(param1, param2)
    logger.info(f"Operazione completata: {len(result)} elementi processati")
except SpecificServiceError as e:
    logger.error(
        f"Fallimento servizio esterno: {type(e).__name__}: {e}",
        extra={"param1": param1, "param2": param2}
    )
    raise
```

### 1.3 Requisiti di Logging

Ogni blocco di gestione errori DEVE loggare:

* **Nome dell'eccezione:** `type(e).__name__`
* **Messaggio dell'errore:** `str(e)`
* **Contesto operativo:** Parametri della chiamata, stato pre-errore
* **Stack trace completo:** Per errori non previsti (usando `logger.exception()`)

---

## 2. OpenAI API (LangChain)

### 2.1 Variabili d'Ambiente Obbligatorie

La libreria `langchain_openai` richiede la seguente configurazione:

| Variabile | Obbligatoria | Descrizione |
|-----------|--------------|-------------|
| `OPENAI_API_KEY` | ✅ Sì | Chiave API OpenAI. Se non fornita come parametro, viene letta automaticamente dall'ambiente |
| `OPENAI_ORG_ID` | ❌ No | ID organizzazione OpenAI (opzionale) |
| `OPENAI_API_VERSION` | ❌ No | Versione API specifica (opzionale) |

**Verifica configurazione:**

```python
import os
from typing import Optional

def validate_openai_config() -> None:
    """Valida la presenza della configurazione OpenAI richiesta."""
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY non configurata. "
            "Impostare la variabile d'ambiente prima di procedere."
        )
    
    if not api_key.startswith("sk-"):
        raise ValueError(
            "OPENAI_API_KEY sembra invalida. "
            "Le chiavi OpenAI iniziano con 'sk-'."
        )
```

### 2.2 Gerarchia Eccezioni OpenAI

La libreria `openai` solleva le seguenti eccezioni (in ordine di specificità):

```python
openai.APIError                    # Classe base per tutti gli errori API
├── openai.APIConnectionError      # Server non raggiungibile
├── openai.APIStatusError          # Errori HTTP (4xx, 5xx)
    ├── openai.AuthenticationError # 401 - Autenticazione fallita
    ├── openai.PermissionDeniedError  # 403 - Permessi insufficienti
    ├── openai.NotFoundError       # 404 - Risorsa non trovata
    ├── openai.RateLimitError      # 429 - Rate limit superato
    ├── openai.InternalServerError # 5xx - Errore server OpenAI
    └── ...
```

### 2.3 Pattern Standard per OpenAIEmbeddings

**QUESTO È IL PATTERN OBBLIGATORIO** per tutte le operazioni di embedding:

```python
import logging
import openai
from langchain_openai import OpenAIEmbeddings
from typing import List

logger = logging.getLogger(__name__)

def generate_embeddings(texts: List[str], model: str = "text-embedding-ada-002") -> List[List[float]]:
    """
    Genera embeddings per una lista di testi usando OpenAI.
    
    Args:
        texts: Lista di testi da processare
        model: Modello di embedding da utilizzare
        
    Returns:
        Lista di vettori di embedding
        
    Raises:
        openai.AuthenticationError: Chiave API invalida o mancante
        openai.APIConnectionError: Impossibile raggiungere il server OpenAI
        openai.RateLimitError: Rate limit superato
        openai.APIStatusError: Altri errori API
    """
    try:
        embeddings = OpenAIEmbeddings(model=model)
        vectors = embeddings.embed_documents(texts)
        
        logger.info(
            f"Generati {len(vectors)} embeddings con successo",
            extra={"model": model, "num_texts": len(texts)}
        )
        return vectors
        
    except openai.AuthenticationError as e:
        logger.error(
            f"Autenticazione OpenAI fallita: {e}. "
            "Verificare OPENAI_API_KEY in .env"
        )
        raise
        
    except openai.APIConnectionError as e:
        logger.error(
            f"Impossibile raggiungere server OpenAI: {e.__cause__}. "
            "Verificare connessione di rete"
        )
        raise
        
    except openai.RateLimitError as e:
        logger.warning(
            f"Rate limit OpenAI raggiunto: {e}. "
            "Implementare retry con backoff esponenziale"
        )
        raise
        
    except openai.APIStatusError as e:
        logger.error(
            f"Errore API OpenAI [{e.status_code}]: {e.response}",
            extra={"status_code": e.status_code}
        )
        raise
        
    except Exception as e:
        logger.exception(
            f"Errore inatteso durante generazione embeddings: {type(e).__name__}: {e}"
        )
        raise
```

### 2.4 Pattern per Singolo Embedding (Query)

```python
def generate_query_embedding(query: str, model: str = "text-embedding-ada-002") -> List[float]:
    """
    Genera embedding per una singola query.
    
    Args:
        query: Testo della query
        model: Modello di embedding
        
    Returns:
        Vettore di embedding
    """
    try:
        embeddings = OpenAIEmbeddings(model=model)
        vector = embeddings.embed_query(query)
        
        logger.debug(f"Embedding query generato: dimensione {len(vector)}")
        return vector
        
    except openai.AuthenticationError as e:
        logger.error(f"Autenticazione OpenAI fallita per query: {e}")
        raise
        
    except openai.APIConnectionError as e:
        logger.error(f"Connessione OpenAI fallita per query: {e.__cause__}")
        raise
        
    except openai.RateLimitError as e:
        logger.warning(f"Rate limit OpenAI per query: {e}")
        raise
        
    except openai.APIStatusError as e:
        logger.error(f"Errore API OpenAI per query [{e.status_code}]: {e.response}")
        raise
```

---

## 3. Supabase VectorStore (LangChain)

### 3.1 Variabili d'Ambiente Obbligatorie

La configurazione del client Supabase richiede:

| Variabile | Obbligatoria | Descrizione |
|-----------|--------------|-------------|
| `SUPABASE_URL` | ✅ Sì | URL del progetto Supabase |
| `SUPABASE_SERVICE_KEY` | ✅ Sì | Service key per autenticazione |

### 3.2 Comportamento del Metodo `add_texts`

**Firma:**
```python
def add_texts(
    self,
    texts: Iterable[str],
    metadatas: Optional[List[Dict[Any, Any]]] = None,
    ids: Optional[List[str]] = None,
    **kwargs: Any
) -> List[str]
```

**Comportamento:**

1. **Successo:** Restituisce `List[str]` con gli ID dei documenti inseriti
2. **Fallimento Totale:** Solleva `Exception("Error inserting: No rows added")` se `result.data` è vuoto
3. **Fallimento Parziale:** Solleva eccezione al primo chunk fallito (operazione non atomica)
4. **Validazione:** Solleva `ValueError` se il numero di metadati/ID non corrisponde al numero di testi

**Importante:** Il metodo processa i dati in chunk (default 500). Un fallimento in qualsiasi chunk interrompe l'operazione.

### 3.3 Eccezioni Possibili

```python
# Eccezioni sollevate da SupabaseVectorStore
ValueError                           # Validazione parametri fallita
Exception("Error inserting: No rows added")  # Upsert restituisce data vuota

# Eccezioni non catturate dal client Supabase
supabase.lib.client_options.ClientOptionsError  # Configurazione client errata
postgrest.exceptions.*              # Errori database (connessione, permessi, schema)
```

### 3.4 Pattern Standard per add_texts

**QUESTO È IL PATTERN OBBLIGATORIO** per l'inserimento di dati nel vector store:

```python
import logging
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import SupabaseVectorStore

logger = logging.getLogger(__name__)

def insert_chunks_to_vectorstore(
    vector_store: SupabaseVectorStore,
    chunks: List[str],
    metadatas: List[Dict[str, Any]],
    chunk_ids: Optional[List[str]] = None
) -> List[str]:
    """
    Inserisce chunk di testo nel vector store con gestione errori robusta.
    
    Args:
        vector_store: Istanza del vector store Supabase
        chunks: Lista di testi da inserire
        metadatas: Metadati associati ai chunk
        chunk_ids: ID opzionali per i chunk
        
    Returns:
        Lista di ID dei chunk inseriti
        
    Raises:
        ValueError: Parametri invalidi o inserimento fallito
        Exception: Errori di connessione o permessi Supabase
    """
    logger.info(
        f"Inizio inserimento {len(chunks)} chunks nel vector store",
        extra={"num_chunks": len(chunks), "has_ids": chunk_ids is not None}
    )
    
    # Validazione pre-inserimento
    if len(chunks) != len(metadatas):
        raise ValueError(
            f"Mismatch: {len(chunks)} chunks ma {len(metadatas)} metadati"
        )
    
    if chunk_ids and len(chunk_ids) != len(chunks):
        raise ValueError(
            f"Mismatch: {len(chunks)} chunks ma {len(chunk_ids)} ID"
        )
    
    try:
        inserted_ids = vector_store.add_texts(
            texts=chunks,
            metadatas=metadatas,
            ids=chunk_ids
        )
        
        # Verifica post-inserimento OBBLIGATORIA
        if not inserted_ids or len(inserted_ids) == 0:
            logger.error(
                "add_texts ha restituito lista vuota - nessun chunk inserito. "
                "Possibili cause: permessi DB, schema tabella, connessione Supabase"
            )
            raise ValueError(
                "Operazione di inserimento fallita: nessun chunk inserito nel vector store"
            )
        
        # Verifica coerenza
        if len(inserted_ids) != len(chunks):
            logger.warning(
                f"Inserimento parziale: {len(inserted_ids)}/{len(chunks)} chunks inseriti"
            )
        
        logger.info(
            f"Inseriti {len(inserted_ids)} chunks con successo",
            extra={"inserted_count": len(inserted_ids)}
        )
        return inserted_ids
        
    except ValueError as e:
        # Errori di validazione o inserimento vuoto
        logger.error(f"Validazione fallita durante inserimento: {e}")
        raise
        
    except Exception as e:
        # Errori del client Supabase (connessione, permessi, schema)
        error_msg = str(e)
        
        if "Error inserting: No rows added" in error_msg:
            logger.error(
                f"Supabase ha rifiutato l'inserimento: {e}. "
                "Verificare: 1) Connessione DB, 2) Permessi tabella, "
                "3) Schema tabella (colonne: id, content, embedding, metadata)"
            )
        else:
            logger.error(
                f"Errore inatteso durante add_texts: {type(e).__name__}: {e}",
                extra={"error_type": type(e).__name__}
            )
        
        raise
```

### 3.5 Pattern per Operazioni Batch

Quando si processano grandi volumi di dati, implementare retry logic:

**Tech Reference**: Per pattern retry avanzati con `node-retry` library, gestione `Retry-After` header, configurazione backoff esponenziale, e best practices, consultare [`docs/tech-reference/03-exponential-backoff.md`](../tech-reference/03-exponential-backoff.md).

```python
import time
from typing import List, Dict, Any

def insert_chunks_with_retry(
    vector_store: SupabaseVectorStore,
    chunks: List[str],
    metadatas: List[Dict[str, Any]],
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> List[str]:
    """
    Inserisce chunk con retry automatico in caso di fallimento.
    
    Args:
        vector_store: Istanza del vector store
        chunks: Testi da inserire
        metadatas: Metadati associati
        max_retries: Numero massimo di tentativi
        retry_delay: Secondi di attesa tra i tentativi
        
    Returns:
        Lista di ID inseriti
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return insert_chunks_to_vectorstore(
                vector_store=vector_store,
                chunks=chunks,
                metadatas=metadatas
            )
            
        except Exception as e:
            last_exception = e
            logger.warning(
                f"Tentativo {attempt + 1}/{max_retries} fallito: {e}. "
                f"Retry tra {retry_delay}s"
            )
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Backoff esponenziale
            else:
                logger.error(
                    f"Inserimento fallito dopo {max_retries} tentativi"
                )
                raise last_exception
```

---

## 4. Checklist Pre-Deployment

Prima di rilasciare codice che interagisce con servizi esterni, verificare:

- [ ] Ogni chiamata API è protetta da `try...except` specifico
- [ ] Ogni blocco `except` logga l'errore con contesto diagnostico
- [ ] Le variabili d'ambiente richieste sono documentate e validate
- [ ] I valori di ritorno sono verificati (non assumere successo implicito)
- [ ] Le eccezioni sono ri-sollevate (o gestite esplicitamente) - no silencing
- [ ] I test coprono scenari di fallimento (mock errori API)

---

## 5. Troubleshooting Rapido

### OpenAI API

| Sintomo | Causa Probabile | Azione |
|---------|----------------|--------|
| `AuthenticationError` | `OPENAI_API_KEY` mancante/invalida | Verificare `.env`, rigenerare chiave su platform.openai.com |
| `APIConnectionError` | Rete non disponibile | Verificare connettività, proxy, firewall |
| `RateLimitError` | Rate limit superato | Implementare backoff, upgrade piano OpenAI |

### Supabase VectorStore

| Sintomo | Causa Probabile | Azione |
|---------|----------------|--------|
| Lista vuota da `add_texts` | Permessi DB insufficienti | Verificare RLS policies, service key |
| `Error inserting: No rows added` | Schema tabella non corrispondente | Verificare colonne: `id`, `content`, `embedding`, `metadata` |
| Timeout connessione | URL Supabase errato | Verificare `SUPABASE_URL` in `.env` |

---

## 6. Riferimenti

### Documentazione Ufficiale

* **OpenAI Python:** https://github.com/openai/openai-python
* **LangChain OpenAI:** https://api.python.langchain.com/en/latest/embeddings/langchain_openai.embeddings.base.OpenAIEmbeddings.html
* **LangChain Supabase:** https://python.langchain.com/api_reference/community/vectorstores/langchain_community.vectorstores.supabase.SupabaseVectorStore.html
* **Supabase LangChain Integration:** https://supabase.com/docs/guides/ai/langchain

### Storia del Documento

| Versione | Data | Modifiche | Autore |
|----------|------|-----------|--------|
| 1.0 | 2025-10-06 | Creazione documento iniziale basato su ricerca Story 2.4.1 | Architetto Software |

---

**Nota:** Questo documento è uno standard di progetto. Ogni deviazione dai pattern qui definiti deve essere motivata e documentata esplicitamente.

