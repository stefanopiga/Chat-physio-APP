# Addendum: asyncpg Database Pattern per FisioRAG

**Status**: Active  
**Version**: 1.0  
**Date**: 2025-10-04

## Context

Pattern per query SQL dirette asincrone con PostgreSQL tramite asyncpg, introdotto per Story 4.4 (Document Chunk Explorer). Il progetto utilizza attualmente `supabase-py` con client sincrono esclusivamente tramite `SupabaseVectorStore` di LangChain, senza query SQL dirette.

**Motivazione asyncpg**:
- Endpoint admin richiedono query di aggregazione complesse (MODE() WITHIN GROUP, JOIN, GROUP BY)
- `supabase-py` è wrapper API alto livello non ottimizzato per query SQL dirette
- Performance ottimali con connection pooling nativo
- Pattern async allineato con best practice FastAPI del progetto

**Ambito**: Endpoint admin con query SQL dirette (non sostituisce SupabaseVectorStore per operazioni RAG).

---

## 1. Installazione

### Dipendenza Poetry

**File**: `apps/api/pyproject.toml`

```toml
[tool.poetry.dependencies]
asyncpg = "^0.30.0"
```

**Installazione**:
```bash
cd apps/api
poetry add asyncpg
```

---

## 2. Pattern 1: Connection Pool con Lifespan Events

### Inizializzazione Pool Globale

**File**: `apps/api/api/database.py` (nuovo)

```python
import os
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Pool globale (inizializzato all'avvio dell'app)
db_pool: asyncpg.Pool | None = None


async def init_db_pool():
    """
    Inizializza il connection pool all'avvio di FastAPI.
    
    Configuration:
    - DATABASE_URL: postgresql://user:pass@host:port/dbname
    - min_size: Connessioni minime mantenute nel pool
    - max_size: Connessioni massime nel pool
    - command_timeout: Timeout query in secondi
    - max_inactive_connection_lifetime: Riconnessione dopo inattività (secondi)
    """
    global db_pool
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL non impostata in .env")
    
    db_pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
        max_queries=50000,
        max_inactive_connection_lifetime=300,
    )
    

async def close_db_pool():
    """Chiude il connection pool allo shutdown di FastAPI."""
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None


@asynccontextmanager
async def lifespan(app):
    """
    Context manager per lifecycle events di FastAPI.
    
    Gestisce:
    - Startup: inizializzazione connection pool
    - Shutdown: chiusura pool e cleanup risorse
    """
    await init_db_pool()
    yield
    await close_db_pool()
```

### Integrazione in main.py

**File**: `apps/api/api/main.py`

```python
from contextlib import asynccontextmanager
from .database import lifespan

# Sostituisci: app = FastAPI()
# Con:
app = FastAPI(lifespan=lifespan)
```

**Vantaggi**:
- Pool creato una sola volta all'avvio (no overhead per richiesta)
- Connessioni riutilizzate automaticamente
- Gestione automatica riconnessioni
- Cleanup garantito allo shutdown

**Fonte**: https://magicstack.github.io/asyncpg/current/usage.html#connection-pools

---

## 3. Pattern 2: Dependency Injection per Connessioni

### Dependency per Endpoint

**File**: `apps/api/api/database.py` (continua)

```python
from typing import AsyncGenerator
from fastapi import Depends

async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency per ottenere una connessione dal pool.
    
    Context manager garantisce rilascio connessione anche in caso di eccezione.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(conn: Annotated[asyncpg.Connection, Depends(get_db_connection)]):
            ...
    
    Raises:
        RuntimeError: Se il pool non è stato inizializzato
    """
    if not db_pool:
        raise RuntimeError("Database pool non inizializzato. Verificare lifespan setup.")
    
    async with db_pool.acquire() as connection:
        yield connection
```

### Utilizzo negli Endpoint

**Esempio**: Endpoint Story 4.4 - Lista documenti

```python
from typing import Annotated
from fastapi import Depends
from .database import get_db_connection
import asyncpg

@app.get("/api/v1/admin/documents")
async def get_documents(
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
):
    """
    Recupera lista documenti con metadata aggregati.
    
    Query Features:
    - JOIN con document_chunks
    - MODE() WITHIN GROUP per strategia predominante
    - COUNT aggregato per numero chunk
    """
    query = """
        SELECT 
            d.id,
            d.title,
            d.created_at,
            MODE() WITHIN GROUP (ORDER BY dc.chunking_strategy) as most_used_strategy,
            COUNT(dc.id) as total_chunks
        FROM documents d
        LEFT JOIN document_chunks dc ON d.id = dc.document_id
        GROUP BY d.id, d.title, d.created_at
        ORDER BY d.created_at DESC
    """
    
    rows = await conn.fetch(query)
    return {"documents": [dict(row) for row in rows]}
```

**Vantaggi**:
- Connessione acquisita dal pool automaticamente
- Rilascio garantito con context manager
- Type hints completi per IDE
- Testabile con dependency override

**Fonte**: https://magicstack.github.io/asyncpg/current/usage.html#connection-pools

---

## 4. Pattern 3: Query Parametrizzate

### Placeholder PostgreSQL ($1, $2)

**Security**: asyncpg usa placeholder PostgreSQL nativi per prevenire SQL injection.

```python
from typing import Annotated
from fastapi import Depends, Query
import asyncpg

@app.get("/api/v1/admin/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    strategy: str | None = Query(None, description="Filter by chunking strategy"),
):
    """
    Recupera chunk per documento con filtri opzionali.
    
    Parameters:
    - $1, $2, $3: Placeholder PostgreSQL parametrizzati (SQL injection safe)
    - Filter dinamico: strategia chunk opzionale
    """
    # Query base
    query = """
        SELECT 
            id,
            content,
            chunk_size,
            chunking_strategy,
            position,
            created_at
        FROM document_chunks
        WHERE document_id = $1
    """
    
    params = [document_id]
    
    # Filtro opzionale per strategia
    if strategy:
        query += " AND chunking_strategy = $2"
        params.append(strategy)
        query += " ORDER BY position ASC LIMIT $3 OFFSET $4"
        params.extend([limit, offset])
    else:
        query += " ORDER BY position ASC LIMIT $2 OFFSET $3"
        params.extend([limit, offset])
    
    rows = await conn.fetch(query, *params)
    return {"chunks": [dict(row) for row in rows]}
```

**Metodi asyncpg.Connection**:
- `fetch(query, *args)`: Lista record
- `fetchrow(query, *args)`: Singolo record (o None)
- `fetchval(query, *args)`: Singolo valore scalare
- `execute(query, *args)`: Esecuzione senza risultati (INSERT/UPDATE/DELETE)

**Fonte**: https://magicstack.github.io/asyncpg/current/usage.html

---

## 5. Pattern 4: Aggregazioni Avanzate PostgreSQL

### MODE() WITHIN GROUP

**Use Case**: Trova il valore più frequente in un gruppo (strategia di chunking predominante per documento).

```python
@app.get("/api/v1/admin/documents")
async def get_documents_with_strategy(
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
):
    """
    Aggregazione con MODE() per strategia predominante.
    
    PostgreSQL Aggregation:
    - MODE() WITHIN GROUP: valore più frequente
    - LEFT JOIN: include documenti senza chunk
    - GROUP BY: aggregazione per documento
    """
    query = """
        SELECT 
            d.id,
            d.title,
            d.created_at,
            MODE() WITHIN GROUP (ORDER BY dc.chunking_strategy) as most_used_strategy,
            COUNT(dc.id) as total_chunks,
            AVG(LENGTH(dc.content))::INTEGER as avg_chunk_size
        FROM documents d
        LEFT JOIN document_chunks dc ON d.id = dc.document_id
        GROUP BY d.id, d.title, d.created_at
        ORDER BY d.created_at DESC
    """
    
    rows = await conn.fetch(query)
    return {"documents": [dict(row) for row in rows]}
```

**Note**:
- `MODE()` restituisce `null` se nessun valore non-null presente
- In caso di tie (più valori con stessa frequenza), sceglie arbitrariamente il primo
- Richiede PostgreSQL 9.4+

**Fonte**: https://www.postgresql.org/docs/current/functions-aggregate.html (Tabella 9.64 - Ordered-Set Aggregate Functions)

---

## 6. Pattern 5: Gestione Errori e Transazioni

### Transazioni Esplicite

```python
from asyncpg import UniqueViolationError, ForeignKeyViolationError

@app.post("/api/v1/admin/documents/{document_id}/chunks")
async def create_chunk(
    document_id: int,
    chunk_data: ChunkCreate,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
):
    """
    Crea chunk con transazione automatica.
    
    Transaction:
    - Rollback automatico su eccezione
    - Commit automatico su successo
    """
    async with conn.transaction():
        query = """
            INSERT INTO document_chunks 
            (document_id, content, chunk_size, chunking_strategy)
            VALUES ($1, $2, $3, $4)
            RETURNING id, created_at
        """
        try:
            row = await conn.fetchrow(
                query,
                document_id,
                chunk_data.content,
                len(chunk_data.content),
                chunk_data.strategy
            )
            return {"id": row["id"], "created_at": row["created_at"]}
        except UniqueViolationError:
            raise HTTPException(status_code=409, detail="Chunk già esistente")
        except ForeignKeyViolationError:
            raise HTTPException(status_code=404, detail="Document non trovato")
```

**Eccezioni asyncpg**:
- `UniqueViolationError`: Violazione constraint UNIQUE
- `ForeignKeyViolationError`: Violazione foreign key
- `PostgresError`: Eccezione base (catch-all)
- `InterfaceError`: Errore connessione/pool

**Fonte**: https://magicstack.github.io/asyncpg/current/usage.html#transactions

---

## 6. Pattern 6: PostgreSQL Advisory Locks per Concurrency Safety

### Use Case: Coordinamento Processi Concorrenti

**Context**: Embedding generation (Story 6.4) richiede coordinamento tra watcher async e batch script per evitare race conditions su stesso documento.

**PostgreSQL Advisory Locks**:
- Lightweight, session-scoped o transaction-scoped
- Non bloccano operazioni DB (solo coordinamento applicativo)
- Due modalità: blocking (`pg_advisory_lock`) e non-blocking (`pg_try_advisory_lock`)
- Due signature: single bigint key o dual int4 keys (namespace + id)

### Pattern: Advisory Lock con Namespace

```python
from typing import Annotated
from fastapi import Depends
import asyncpg

async def acquire_document_lock(
    conn: asyncpg.Connection,
    document_id: str,
    namespace: str = "docs_ns"
) -> bool:
    """
    Acquisisce advisory lock su documento con namespace.
    
    Args:
        conn: Connection asyncpg
        document_id: UUID documento
        namespace: Namespace per evitare collisioni (default: "docs_ns")
    
    Returns:
        True se lock acquisito, False se già locked
    
    Note:
        - Usa hashtext() DB-side per chiavi stabili cross-process
        - Evita Python hash() (instabile tra processi/seed)
        - Lock rilasciato automaticamente a fine transazione o conn.close()
    """
    query = """
        SELECT pg_try_advisory_lock(
            hashtext($1),
            hashtext($2::text)
        )
    """
    result = await conn.fetchval(query, namespace, document_id)
    return result


async def release_document_lock(
    conn: asyncpg.Connection,
    document_id: str,
    namespace: str = "docs_ns"
):
    """Rilascia advisory lock manualmente."""
    query = """
        SELECT pg_advisory_unlock(
            hashtext($1),
            hashtext($2::text)
        )
    """
    await conn.execute(query, namespace, document_id)
```

### Example: Watcher Embedding Generation con Lock

```python
@app.post("/watcher/process-document/{document_id}")
async def process_document_with_lock(
    document_id: str,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
):
    """
    Processa documento con advisory lock per evitare race con batch.
    
    Flow:
    1. Acquisisce lock (blocking)
    2. Genera embeddings
    3. Lock rilasciato automaticamente a fine transazione
    """
    # Blocking lock - attende se batch sta già processando
    await conn.execute("""
        SELECT pg_advisory_lock(hashtext('docs_ns'), hashtext($1::text))
    """, document_id)
    
    try:
        # Genera embeddings (funzione esistente)
        await generate_embeddings(document_id, conn)
        
        logger.info({
            "event": "watcher_indexing_complete",
            "document_id": document_id,
            "lock_coordinated": True
        })
        
        return {"status": "processed", "document_id": document_id}
    finally:
        # Release lock
        await conn.execute("""
            SELECT pg_advisory_unlock(hashtext('docs_ns'), hashtext($1::text))
        """, document_id)
```

### Example: Batch Script con Non-Blocking Lock

```python
async def batch_process_documents(conn: asyncpg.Connection):
    """
    Batch processing con pg_try_advisory_lock (non-blocking).
    
    Flow:
    1. Query documenti
    2. Per ogni documento, tenta lock non-blocking
    3. Skip se già locked (watcher in corso)
    4. Processa solo documenti lockati
    """
    docs = await conn.fetch("""
        SELECT id FROM documents WHERE status='completed'
    """)
    
    for doc in docs:
        # Non-blocking lock - skip se già locked
        locked = await conn.fetchval("""
            SELECT pg_try_advisory_lock(hashtext('docs_ns'), hashtext($1::text))
        """, str(doc['id']))
        
        if not locked:
            logger.info({
                "event": "batch_doc_skipped",
                "reason": "locked_by_watcher",
                "doc_id": str(doc['id'])
            })
            continue
        
        try:
            await generate_embeddings(doc['id'], conn)
            logger.info({
                "event": "batch_doc_indexed",
                "document_id": str(doc['id'])
            })
        finally:
            await conn.execute("""
                SELECT pg_advisory_unlock(hashtext('docs_ns'), hashtext($1::text))
            """, str(doc['id']))
```

### Quando Usare Advisory Locks

**✅ Use Advisory Locks quando:**
- Processi concorrenti devono coordinarsi su stessa risorsa
- Lock non deve bloccare letture DB (solo coordinamento app-level)
- Performance critical (lightweight, no table locks)
- Cross-process coordination necessaria

**❌ NON usare Advisory Locks quando:**
- Serve atomicità transazionale (usa `conn.transaction()`)
- Serve protezione row-level DB (usa `SELECT ... FOR UPDATE`)
- Coordinamento cross-database (advisory locks sono PostgreSQL-specific)
- Lock permanenti necessari (advisory locks rilasciati a conn close)

### Gotchas & Best Practices

**⚠️ Evitare Python `hash()`:**
```python
# ❌ BAD: hash() instabile tra processi
lock_id = hash(str(document_id))

# ✅ GOOD: hashtext() DB-side stabile
await conn.execute("""
    SELECT pg_advisory_lock(hashtext('ns'), hashtext($1))
""", document_id)
```

**⚠️ Lock Scope:**
- Session-scoped: persiste fino a `conn.close()` o explicit unlock
- Transaction-scoped: usa `pg_advisory_xact_lock()` (auto-release a COMMIT/ROLLBACK)

```python
# Session-scoped (manual unlock necessario)
await conn.execute("SELECT pg_advisory_lock(hashtext('ns'), hashtext($1))", doc_id)
# ... do work ...
await conn.execute("SELECT pg_advisory_unlock(hashtext('ns'), hashtext($1))", doc_id)

# Transaction-scoped (auto-release)
async with conn.transaction():
    await conn.execute("SELECT pg_advisory_xact_lock(hashtext('ns'), hashtext($1))", doc_id)
    # ... do work ...
    # Lock released automatically on commit/rollback
```

**⚠️ Deadlock Prevention:**
- Acquisire locks sempre in stesso ordine
- Usare timeout con `pg_try_advisory_lock()` invece di blocking indefinito
- Consider using transaction-scoped locks per auto-cleanup

**⚠️ Key Namespace Conventions:**
- Usa namespace distintivi per evitare collisioni (es. `docs_ns`, `jobs_ns`, `cache_ns`)
- Documentare chiavi lock nel codice
- Consider centralized lock key registry per progetti grandi

### Testing Advisory Locks

```python
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.asyncio
async def test_advisory_lock_coordination():
    """Test che advisory locks prevengano race condition."""
    document_id = "test-doc-123"
    
    # Simula processi concorrenti
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(asyncio.run, watcher_process(document_id))
        future2 = executor.submit(asyncio.run, batch_process(document_id))
        
        result1 = future1.result()
        result2 = future2.result()
    
    # Verifica coordinamento
    assert result1['processed'] != result2['processed']  # Solo uno processa
    assert result1['skipped'] or result2['skipped']      # Altro skips
```

**Fonte**: https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS

**Related Story**: Story 6.4 - RAG Activation: Embedding Generation (`docs/stories/6.4.rag-activation-embedding-generation-watcher.md`)

---

## 7. Pattern 7: Query Parameter Classes (FastAPI)

### Raggruppamento Parametri Complessi

**Use Case**: Endpoint con molti parametri di filtro/paginazione.

```python
from typing import Annotated
from fastapi import Depends, Query

class PaginationParams:
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Max records to return")
    ):
        self.skip = skip
        self.limit = limit


class ChunkFilterParams:
    def __init__(
        self,
        strategy: str | None = Query(None, description="Filter by chunking strategy"),
        min_size: int | None = Query(None, ge=0, description="Minimum chunk size"),
        sort_by: str = Query("created_at", regex="^(created_at|size|position)$")
    ):
        self.strategy = strategy
        self.min_size = min_size
        self.sort_by = sort_by


@app.get("/api/v1/admin/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    pagination: Annotated[PaginationParams, Depends()],
    filters: Annotated[ChunkFilterParams, Depends()]
):
    """
    Endpoint con parametri raggruppati in classi riutilizzabili.
    
    Vantaggi:
    - Riutilizzo classi su più endpoint
    - Validazione centralizzata
    - Documentazione OpenAPI auto-generata
    - Type hints completi
    """
    # Build query dinamica
    query_parts = ["SELECT * FROM document_chunks WHERE document_id = $1"]
    params = [document_id]
    param_idx = 2
    
    if filters.strategy:
        query_parts.append(f"AND chunking_strategy = ${param_idx}")
        params.append(filters.strategy)
        param_idx += 1
    
    if filters.min_size:
        query_parts.append(f"AND LENGTH(content) >= ${param_idx}")
        params.append(filters.min_size)
        param_idx += 1
    
    query_parts.append(f"ORDER BY {filters.sort_by}")
    query_parts.append(f"LIMIT ${param_idx} OFFSET ${param_idx + 1}")
    params.extend([pagination.limit, pagination.skip])
    
    query = " ".join(query_parts)
    rows = await conn.fetch(query, *params)
    
    return {"chunks": [dict(row) for row in rows]}
```

**Vantaggi**:
- Eliminazione ripetizione parametri
- Classi testabili separatamente
- Documentazione automatica OpenAPI
- Type hints IDE

**Fonte**: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/

---

## 8. Configuration

### Variabile d'Ambiente DATABASE_URL

**File**: `apps/api/.env`

```bash
# PostgreSQL Connection String
DATABASE_URL=postgresql://user:password@host:port/database

# Formato per Supabase:
# DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

**Note**:
- Usare connection pooler Supabase (porta 6543) per performance
- Format: `postgresql://user:password@host:port/database`
- asyncpg supporta SSL automaticamente per connessioni Supabase

**Fonte**: https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler

---

## 9. Testing Patterns

### Mock Connection per Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db_connection():
    """Mock asyncpg.Connection per testing."""
    conn = AsyncMock(spec=asyncpg.Connection)
    
    # Mock fetch result
    conn.fetch.return_value = [
        {"id": 1, "title": "Doc 1", "total_chunks": 10},
        {"id": 2, "title": "Doc 2", "total_chunks": 5},
    ]
    
    return conn


@pytest.fixture
def client_with_mock_db(mock_db_connection):
    """Test client con database mockato."""
    from main import app
    
    # Override dependency
    app.dependency_overrides[get_db_connection] = lambda: mock_db_connection
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()


def test_get_documents(client_with_mock_db, mock_db_connection):
    """
    Test endpoint con database mockato.
    
    Verifica:
    - Query eseguita correttamente
    - Response serializzato
    """
    response = client_with_mock_db.get("/api/v1/admin/documents")
    
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 2
    
    # Verifica query chiamata
    mock_db_connection.fetch.assert_called_once()
    query_executed = mock_db_connection.fetch.call_args[0][0]
    assert "MODE() WITHIN GROUP" in query_executed
```

---

## 10. Quando Usare asyncpg vs SupabaseVectorStore

### Decision Matrix

| Use Case | Tool Raccomandato | Motivazione |
|----------|-------------------|-------------|
| Operazioni RAG (similarity search, embedding storage) | SupabaseVectorStore (LangChain) | API alto livello, integrazione LangChain, embedding automatici |
| Query SQL complesse (aggregazioni, JOIN, analisi) | asyncpg | Performance ottimali, flessibilità SQL, connection pooling |
| CRUD semplice documenti | SupabaseVectorStore | Astrazione alto livello, meno codice |
| Endpoint admin analytics | asyncpg | Aggregazioni complesse, performance, query custom |
| Batch operations | asyncpg | Transazioni, controllo granulare |

**Regola Generale**: SupabaseVectorStore per RAG, asyncpg per query SQL dirette.

---

## 11. Performance Considerations

### Connection Pool Tuning

**Parametri Raccomandati**:
- **min_size**: 5 (MVP single instance)
- **max_size**: 20 (MVP single instance)
- **command_timeout**: 60 secondi (query complesse)
- **max_inactive_connection_lifetime**: 300 secondi (5 minuti)

**Scaling**:
- Multi-instance deployment: aumentare max_size (es. 50)
- High concurrency: monitoring pool exhaustion con `asyncpg` logs
- Supabase Pooler: usare porta 6543 per connection pooling lato server

---

## 12. Migration Checklist

Checklist per integrazione asyncpg in endpoint esistenti:

### Setup Iniziale
- [ ] Aggiungere `asyncpg = "^0.30.0"` in `pyproject.toml`
- [ ] Creare file `apps/api/api/database.py` con pool setup
- [ ] Aggiungere `DATABASE_URL` in `apps/api/.env`
- [ ] Integrare lifespan in `main.py`
- [ ] Testare pool initialization all'avvio

### Per Ogni Endpoint
- [ ] Endpoint `async def` (non `def`)
- [ ] Dependency `Annotated[asyncpg.Connection, Depends(get_db_connection)]`
- [ ] Query parametrizzate con `$1`, `$2` placeholders
- [ ] Error handling con eccezioni asyncpg tipizzate
- [ ] Unit test con mock connection
- [ ] Documentazione query SQL in docstring

---

## References

### Documentation
- **asyncpg Official**: https://magicstack.github.io/asyncpg/current/
- **PostgreSQL Aggregations**: https://www.postgresql.org/docs/current/functions-aggregate.html
- **FastAPI Dependencies**: https://fastapi.tiangolo.com/tutorial/dependencies/
- **Supabase Connection Pooling**: https://supabase.com/docs/guides/database/connecting-to-postgres

### Related Architecture Docs
- `addendum-fastapi-best-practices.md`: Pattern async/await, dependency injection
- `sezione-3-tech-stack.md`: Tech stack overview
- `addendum-pgvector-langchain-supabase.md`: SupabaseVectorStore (RAG operations)

### Related Stories
- Story 4.4: `docs/stories/4.4-document-chunk-explorer.md` (primo use case asyncpg)

---

**Revision History**:

| Date       | Version | Changes                                      |
|------------|---------|----------------------------------------------|
| 2025-10-04 | 1.0     | Initial version - asyncpg database pattern   |

