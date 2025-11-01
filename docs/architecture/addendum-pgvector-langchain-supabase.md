# Addendum: Supabase pgvector & LangChain VectorStore

## Supabase (pgvector)

- Abilitare estensione `pgvector`  
  - Link: `https://supabase.com/docs/guides/database/extensions/pgvector`  
  - SQL (da Dashboard → Extensions oppure SQL equivalente):
```sql
-- Abilita estensione pgvector (nome estensione: vector)
create extension if not exists vector;
```

- Creare tabella con colonna `vector(dim)`  
  - Link: `https://supabase.com/docs/guides/ai/vector-columns`  
```sql
-- Esempio: tabella document_chunks con embedding a 1536 dimensioni (OpenAI text-embedding-3-small)
create table document_chunks (
  id uuid primary key,
  document_id uuid not null,
  content text not null,
  embedding vector(1536),
  metadata jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

- Funzione SQL per ricerca di similarità (distanza coseno)  
  - Link: `https://supabase.com/docs/guides/ai/vector-columns`  
```sql
-- match per distanza coseno (<=>). Adegua la dimensione al tuo modello.
create or replace function match_document_chunks (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.document_id,
    dc.content,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  where 1 - (dc.embedding <=> query_embedding) > match_threshold
  order by (dc.embedding <=> query_embedding) asc
  limit match_count;
$$;
```

- Indici di similarità (HNSW o IVFFlat)  
  - Panoramica indici: `https://supabase.com/docs/guides/ai/vector-indexes`  
  - HNSW index (consigliato, operatore coseno): `https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes`  
```sql
-- Indice HNSW su colonna embedding con operatore coseno
create index on document_chunks using hnsw (embedding vector_cosine_ops);
```
  - IVFFlat (uso specifico; creare dopo popolamento dati): `https://supabase.com/docs/guides/ai/vector-indexes/ivf-indexes`  
```sql
-- Indice IVFFlat con 100 liste, operatore coseno
create index on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Numero di probes (a sessione)
set ivfflat.probes = 10;
```

- Guida semantic search in Postgres (funzioni e operatori):  
  - Link: `https://supabase.com/docs/guides/ai/semantic-search`


## LangChain (SupabaseVectorStore)

- Documentazione integrazione:  
  - Guida: `https://python.langchain.com/docs/integrations/vectorstores/supabase/`  
  - API reference: `https://python.langchain.com/api_reference/community/vectorstores/langchain_community.vectorstores.supabase.SupabaseVectorStore.html`  
  - Template RAG Supabase (SQL completo e uso): `https://python.langchain.com/v0.1/docs/templates/rag-supabase/`

- Requisiti (da guida): abilitare `pgvector`, creare tabella `documents`, creare funzione `match_documents_chunks`, installare `supabase-py`.

- Inizializzazione client e embeddings; creazione `SupabaseVectorStore` e inserimento documenti:
```python
from supabase.client import Client, create_client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings

# Credenziali Supabase
supabase_url = os.environ["SUPABASE_URL"]
supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# Embeddings OpenAI (vedi sezione Provider)
embeddings = OpenAIEmbeddings()  # model configurato nella sezione successiva

# Inserimento documenti: calcolo embedding + salvataggio su Supabase
vector_store = SupabaseVectorStore.from_documents(
    docs,                      # lista di Document
    embeddings,
    client=supabase,
    table_name="document_chunks",
    query_name="match_document_chunks",
    chunk_size=500,
)

# Oppure collegamento a tabella già popolata
vector_store = SupabaseVectorStore(
    embedding=embeddings,
    client=supabase,
    table_name="document_chunks",
    query_name="match_document_chunks",
)

# Ricerca di similarità (ingestion vs. runtime)

```python
results = vector_store.similarity_search("la tua query")   # usato solo nella pipeline di ingestion
```

> Nota API: metodi disponibili (`add_texts`, `from_documents`, `similarity_search_with_relevance_scores`, `as_retriever("mmr")`, ecc.) nella reference LangChain.

### Runtime attuale (Story 2.11)

Per l'endpoint `/api/v1/chat/query` non adoperiamo più il retriever di LangChain: il backend calcola l'embedding con `OpenAIEmbeddings.embed_query` e invoca direttamente la RPC `match_document_chunks` via `supabase.rpc(...)`, con fallback automatico da soglia 0.6 a 0.0. In pseudocodice:

```python
query_embedding = embeddings.embed_query(query)
response = supabase.rpc(
    "match_document_chunks",
    {
        "query_embedding": query_embedding,
        "match_threshold": threshold or 0.6,
        "match_count": k,
    },
).execute()

hits = [
    {
        "id": row.get("id"),
        "document_id": row.get("document_id"),
        "content": row["content"],
        "metadata": {
            **(row.get("metadata") or {}),
            "id": row.get("id"),
            "document_id": row.get("document_id"),
        },
        "similarity_score": row.get("similarity"),
    }
    for row in response.data or []
]
if not hits and threshold is not None:
    # fallback a soglia più permissiva
    ...
```

Il retriever LangChain rimane in uso per l'inserimento (`add_texts`) ma l'interfaccia di ricerca è ora più snella e sotto controllo completo dell'applicazione.

### Chunk Router e strategia di chunking

- La pipeline di ingestion usa `ChunkRouter` (`apps/api/api/ingestion/chunk_router.py`) per scegliere la strategia:
  - se la classificazione strutturale (`ClassificazioneOutput`) non è disponibile o ha `confidenza < 0.7`, viene usato il fallback `recursive_character_800_160` con prefisso `fallback::`.
  - categorie `TESTO_ACCADEMICO_DENSO` usano la strategia ricorsiva, mentre documenti tabellari o misti passano per `TabularStructuralStrategy`.
- I metadati serializzati per ogni chunk salvano `document_id`, indice e parametri della strategia, permettendo di verificare a posteriori la strategia applicata.
- La verifica dell'unicità dei chunk (script `scripts/validation/verify_chunk_ids.py`) garantisce che l'identificativo del chunk sia riportato anche nella metadata JSON: il backend lo propaga nella risposta API, così l'UI non mostra più `unknown` nelle citazioni.


## Provider di Embedding

- OpenAI Embeddings con LangChain  
  - Guida LangChain `OpenAIEmbeddings`: `https://python.langchain.com/docs/integrations/text_embedding/openai/`  
```python
from langchain_openai import OpenAIEmbeddings

# Impostare OPENAI_API_KEY nell'ambiente
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    # dimensione: 1536
)
```

- Documentazione OpenAI embeddings  
  - Panoramica: `https://platform.openai.com/docs/guides/embeddings`  
  - Modelli: `https://platform.openai.com/docs/models/text-embedding-3-large`  
  - API Reference (endpoint embeddings): `https://platform.openai.com/docs/api-reference/embeddings`


