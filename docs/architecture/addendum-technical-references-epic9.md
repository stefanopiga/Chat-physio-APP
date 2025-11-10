# Addendum: Technical References — Epic 9 Persistent Memory

**Epic**: Epic 9 - Persistent Conversational Memory & Long-term Analytics  
**Related Stories**: 9.1, 9.2  
**Status**: Reference Documentation  
**Last Updated**: 2025-11-06

---

## Overview

Riferimenti tecnici ufficiali per pattern, librerie e tecnologie utilizzate nell'implementazione Epic 9. Documentazione recuperata da fonti autorevoli per garantire implementazione corretta e conforme a best practices.

---

## 1. asyncpg — PostgreSQL Async Driver

### Fonte Ufficiale

- **URL**: https://magicstack.github.io/asyncpg/
- **Versione**: asyncpg 0.30.0 (Python 3.11+)
- **Status Progetto**: ✅ Già installato in `pyproject.toml`

### Concetti Chiave

- **Bulk Insert con `executemany()`**: Prepared statement automatico, riduce roundtrip DB
- **Connection Pooling**: `create_pool()` mantiene connessioni aperte, elimina overhead apertura/chiusura
- **Idempotency**: Hash SHA256 + constraint UNIQUE per prevenire duplicati
- **Batch Processing**: Usare `UNNEST` PostgreSQL per performance ottimali
- **Transaction Context**: Obbligatorio per atomicità multi-record

### Pattern Implementativo — Bulk Insert

```python
import asyncpg
from datetime import datetime
from typing import List, Tuple

async def bulk_insert_conversations(
    pool: asyncpg.Pool,
    records: List[Tuple[str, str, str, dict, datetime]]
) -> int:
    """
    Bulk insert conversazioni con idempotency key.
    
    Args:
        pool: Connection pool asyncpg
        records: (conversation_id, user_id, session_id, metadata, timestamp)
    
    Returns:
        Numero record inseriti (esclude duplicati)
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            stmt = """
                INSERT INTO conversations (
                    conversation_id, user_id, session_id, 
                    metadata, created_at, idempotency_key
                )
                SELECT 
                    unnest($1::text[]),
                    unnest($2::text[]),
                    unnest($3::text[]),
                    unnest($4::jsonb[]),
                    unnest($5::timestamptz[]),
                    encode(digest(unnest($1::text[]) || unnest($2::text[]), 'sha256'), 'hex')
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING conversation_id
            """
            
            conv_ids, user_ids, session_ids, metadatas, timestamps = zip(*records)
            
            result = await conn.fetch(
                stmt,
                list(conv_ids), list(user_ids), 
                list(session_ids), list(metadatas), list(timestamps)
            )
            
            return len(result)

# Connection Pool Initialization
async def init_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host='localhost',
        database='fisiorag',
        user='postgres',
        password='password',
        min_size=5,       # Minimo connessioni
        max_size=20,      # Massimo connessioni
        command_timeout=60.0
    )
```

### Integration Notes Story 9.1

- **Task 1.2**: `ConversationPersistenceService.save_messages()` usa bulk insert con batch 100 record
- **Task 3.2**: `HybridConversationManager` dependency injection per connection pool globale
- **Pattern Idempotency**: Constraint UNIQUE su `idempotency_key` = `sha256(session_id + timestamp + content_hash)`
- **Transaction Scope**: Wrappare bulk insert in `async with conn.transaction()` per rollback atomico

### Performance Considerations

- **Pool Size**: Evitare `max_size > 50`, PostgreSQL degrada con troppe connessioni
- **Statement Cache**: asyncpg caching automatico (`statement_cache_size=100`)
- **Timeout**: `command_timeout=60s` per prevenire query hung
- **Idempotency Key**: SHA256 → 64 caratteri, validare con `CHECK (length(idempotency_key) = 64)`

---

## 2. aiofiles — Async File I/O

### Fonte Ufficiale

- **URL**: https://pypi.org/project/aiofiles/
- **Versione**: 25.1.0 (Python 3.11+)
- **License**: Apache 2.0
- **Status Progetto**: ❌ NON installato — Richiesto per Story 9.1 Task 8

### Installazione Richiesta

```bash
cd apps/api
poetry add aiofiles
```

### Concetti Chiave

- **Thread Pool Delegation**: Operazioni I/O delegate a thread separato, non blocca event loop
- **Context Manager**: `async with aiofiles.open()` garantisce chiusura automatica
- **Append-Only Mode**: `mode='a'` per JSONL log, atomic write garantito da filesystem
- **Async Iteration**: `async for line in f` per parsing incrementale senza caricamento completo in RAM

### Pattern Implementativo — JSONL Append-Only Log

```python
import aiofiles
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

async def append_conversation_log(
    log_path: Path,
    conversation_id: str,
    event_type: str,
    payload: Dict[str, Any]
) -> None:
    """
    Append atomic a JSONL log per durable outbox.
    
    Args:
        log_path: Path JSONL (es: .data/persistence_outbox.jsonl)
        conversation_id: ID conversazione
        event_type: Tipo evento ('message_added', 'flushed')
        payload: Dati evento
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "conversation_id": conversation_id,
        "event_type": event_type,
        "payload": payload
    }
    
    async with aiofiles.open(log_path, mode='a', encoding='utf-8') as f:
        await f.write(json.dumps(log_entry) + '\n')
        await f.flush()  # Flush esplicito per durability

async def read_conversation_log(
    log_path: Path,
    conversation_id: str
) -> list[Dict[str, Any]]:
    """
    Lettura incrementale JSONL con filtraggio.
    
    Returns:
        Eventi relativi a conversation_id
    """
    events = []
    
    if not log_path.exists():
        return events
    
    async with aiofiles.open(log_path, mode='r', encoding='utf-8') as f:
        async for line in f:
            try:
                event = json.loads(line.strip())
                if event.get('conversation_id') == conversation_id:
                    events.append(event)
            except json.JSONDecodeError:
                continue  # Skip corrupted line
    
    return events
```

### Integration Notes Story 9.1

- **Task 8**: `OutboxPersistenceQueue` usa JSONL per `.data/persistence_outbox.jsonl`
- **Durability Pattern**: Append a JSONL ogni DB write failure, retry background loop
- **File per Session**: Un JSONL file per sessione: `.data/conversations_{session_id}.jsonl`
- **Recovery**: Al riavvio, leggere JSONL e ricostruire stato L1 da eventi non-flushed

### Performance Considerations

- **Append Contention**: aiofiles lock interno, evitare append concorrenti stesso file
- **Corruption Risk**: Solo ultima linea corrotta se write interrotto, resto recuperabile
- **Batch Writes**: Buffer max 50 eventi in memoria prima flush per ridurre I/O overhead
- **Handle Leak**: Sempre context manager, mai apertura diretta

---

## 3. Circuit Breaker Pattern

### Fonte Ufficiale

- **URL**: https://martinfowler.com/bliki/CircuitBreaker.html
- **Autore**: Martin Fowler (March 6, 2014)
- **Riferimento**: Michael Nygard - "Release It" book

### Concetti Chiave

- **State Machine**: CLOSED (normale) → OPEN (fail-fast) → HALF_OPEN (test recovery)
- **Failure Threshold**: Circuito apre quando `failure_count >= threshold` (default 5)
- **Timeout Reset**: Dopo timeout (default 60s), passa a HALF_OPEN per recovery test
- **Thread Pool Protection**: Evita exhaustion su servizi non-responsive
- **Monitor Integration**: Ogni cambio stato deve triggerare alert

### Pattern Implementativo

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerOpen(Exception):
    """Exception quando circuito aperto."""
    pass

class AsyncCircuitBreaker:
    """
    Circuit breaker per PostgreSQL connections.
    Pattern adattato da Martin Fowler per async/await Python.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Determina stato corrente considerando timeout."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                return CircuitState.HALF_OPEN
        return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Verifica se timeout scaduto per tentativo reset."""
        return (
            self._last_failure_time is not None
            and datetime.utcnow() - self._last_failure_time > self.timeout
        )
    
    async def call(self, func, *args, **kwargs):
        """
        Esegui funzione protetta da circuit breaker.
        
        Raises:
            CircuitBreakerOpen: Se circuito aperto
        """
        async with self._lock:
            current_state = self.state
            
            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpen(
                    f"Circuit breaker OPEN: {self._failure_count} failures"
                )
            
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except self.expected_exception as e:
                await self._on_failure()
                raise e
    
    async def _on_success(self) -> None:
        """Reset circuit breaker dopo successo."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = None
    
    async def _on_failure(self) -> None:
        """Incrementa failure e potenzialmente apri circuito."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
```

### Integration Notes Story 9.1

- **Task 3.9-3.12**: Wrappare ogni DB operation in circuit breaker
- **Threshold**: `failure_threshold=3` (3 consecutive failures = circuito OPEN)
- **Timeout**: `timeout_seconds=30` (30s prima tentativo HALF_OPEN)
- **Metric**: `circuit_breaker_open` gauge (0=CLOSED, 1=OPEN)
- **Multiple Breakers**: Read operations vs write operations separati

### Critical Considerations

- **Lock Contention**: `asyncio.Lock` introduce overhead, non usare in hot path <1ms
- **False Positive**: Threshold troppo basso → aperture spurie, monitorare distribution
- **Cascading Failure**: Circuito deve aprire PRIMA thread pool exhaustion
- **Manual Override**: Endpoint admin per forzare CLOSED/OPEN stato

---

## 4. Durable Outbox Pattern

### Fonte Ufficiale

- **URL**: https://microservices.io/patterns/data/transactional-outbox.html
- **Autore**: Chris Richardson - Microservices.io
- **Pattern Type**: Transactional Messaging

### Concetti Chiave

- **Transactional Write**: Evento in `outbox` table nella STESSA transaction dei dati business
- **Message Relay**: Background worker legge outbox e invia eventi, delete dopo delivery
- **Idempotency Key**: Consumer gestisce duplicati, relay può inviare stesso messaggio più volte
- **Eventual Consistency**: Eventi non immediati ma asincroni, delay accettabile
- **Dead-Letter Queue**: Eventi con >10 retry falliti → DLQ per analisi manuale

### Pattern Implementativo

```python
import asyncpg
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any
from enum import Enum

class OutboxStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

async def write_to_outbox(
    conn: asyncpg.Connection,
    aggregate_id: str,
    event_type: str,
    payload: Dict[str, Any]
) -> str:
    """
    Inserisce evento in outbox nella stessa transazione.
    
    Returns:
        Idempotency key generato
    """
    idempotency_key = hashlib.sha256(
        f"{aggregate_id}:{event_type}:{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()
    
    await conn.execute("""
        INSERT INTO outbox (
            idempotency_key, aggregate_id, event_type,
            payload, status, retry_count, created_at
        ) VALUES ($1, $2, $3, $4, $5, 0, NOW())
        ON CONFLICT (idempotency_key) DO NOTHING
    """, idempotency_key, aggregate_id, event_type, 
        payload, OutboxStatus.PENDING.value)
    
    return idempotency_key

async def relay_outbox_messages(pool: asyncpg.Pool) -> int:
    """
    Background worker: processa outbox con exponential backoff.
    
    Returns:
        Numero messaggi processati
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # SELECT FOR UPDATE SKIP LOCKED: evita race condition
            messages = await conn.fetch("""
                SELECT id, idempotency_key, aggregate_id, 
                       event_type, payload, retry_count, created_at
                FROM outbox
                WHERE status = $1 
                  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
                ORDER BY created_at ASC
                LIMIT 100
                FOR UPDATE SKIP LOCKED
            """, OutboxStatus.PENDING.value)
            
            processed = 0
            for msg in messages:
                try:
                    await _publish_event(msg['event_type'], msg['payload'])
                    
                    # Success: marca completed
                    await conn.execute("""
                        UPDATE outbox 
                        SET status = $1, completed_at = NOW()
                        WHERE id = $2
                    """, OutboxStatus.COMPLETED.value, msg['id'])
                    
                    processed += 1
                    
                except Exception as e:
                    retry_count = msg['retry_count'] + 1
                    
                    if retry_count >= 10:
                        # Dead-letter queue
                        await conn.execute("""
                            UPDATE outbox 
                            SET status = $1, error_message = $2
                            WHERE id = $3
                        """, OutboxStatus.FAILED.value, str(e), msg['id'])
                    else:
                        # Exponential backoff: 1s, 2s, 4s, 8s, ..., 60s max
                        backoff_seconds = min(2 ** retry_count, 60)
                        next_retry = datetime.utcnow() + timedelta(seconds=backoff_seconds)
                        
                        await conn.execute("""
                            UPDATE outbox 
                            SET retry_count = $1, next_retry_at = $2, error_message = $3
                            WHERE id = $4
                        """, retry_count, next_retry, str(e), msg['id'])
            
            return processed
```

### Integration Notes Story 9.1

- **Task 8**: Ogni modifica conversazione scrive evento in outbox nella stessa transaction
- **Background Relay**: Job scheduled ogni 5 secondi esegue `relay_outbox_messages()`
- **Idempotency**: `conversation_id + event_type + timestamp` garantisce unicità
- **DLQ Monitoring**: Alert quando `status='failed'` count > 0

### Critical Considerations

- **Transaction Size**: Ogni write business + outbox, dimensione raddoppia
- **Relay Scaling**: Worker singolo max 100 msg/s, multiple workers con `SKIP LOCKED`
- **Retry Storm**: Exponential backoff obbligatorio, linear retry causa storm
- **Key Collision**: SHA256 improbabile, constraint UNIQUE previene duplicati

---

## 5. PostgreSQL Full-Text Search — Italian

### Fonte Ufficiale

- **URL**: https://www.postgresql.org/docs/current/textsearch.html
- **Versione**: PostgreSQL 13+ (Italian language support nativo)

### Concetti Chiave

- **Configuration 'italian'**: Snowball stemmer riduce parole a radice (es: "parlare" → "parl")
- **`to_tsvector('italian', text)`**: Parsing in tokens, rimuove stop words ("il", "di", "che")
- **`plainto_tsquery('italian', query)`**: Parsing query senza sintassi complessa, user-friendly
- **GIN Index**: Indice invertito, dimensione ~50% testo originale
- **`ts_rank()`**: Ranking per relevance, considera frequenza e posizione lexeme

### Pattern Implementativo

```sql
-- Schema con colonna tsvector precompilata
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    
    -- tsvector generata automaticamente
    content_fts tsvector GENERATED ALWAYS AS (
        to_tsvector('italian', coalesce(content, ''))
    ) STORED
);

-- GIN index per FTS ottimale
CREATE INDEX idx_conversations_fts 
ON conversations USING GIN (content_fts);

-- Partial index: solo record non archiviati
CREATE INDEX idx_conversations_fts_active
ON conversations USING GIN (content_fts)
WHERE (metadata->>'archived')::boolean IS NOT TRUE;
```

**Query con Ranking**:

```python
async def search_conversations_fts(
    conn: asyncpg.Connection,
    user_id: str,
    search_query: str,
    limit: int = 10
) -> list[dict]:
    """FTS con ranking italiano."""
    results = await conn.fetch("""
        SELECT 
            conversation_id, content, created_at,
            ts_rank(content_fts, plainto_tsquery('italian', $2)) AS rank
        FROM conversations
        WHERE 
            user_id = $1
            AND content_fts @@ plainto_tsquery('italian', $2)
            AND (metadata->>'archived')::boolean IS NOT TRUE
        ORDER BY rank DESC, created_at DESC
        LIMIT $3
    """, user_id, search_query, limit)
    
    return [dict(row) for row in results]
```

**Query con Highlighting**:

```python
async def search_with_highlight(
    conn: asyncpg.Connection,
    search_query: str
) -> list[dict]:
    """FTS con evidenziazione match."""
    results = await conn.fetch("""
        SELECT 
            conversation_id,
            ts_headline(
                'italian', content,
                plainto_tsquery('italian', $1),
                'StartSel=<b>, StopSel=</b>, MaxWords=50, MinWords=25'
            ) AS highlighted_content,
            ts_rank(content_fts, plainto_tsquery('italian', $1)) AS rank
        FROM conversations
        WHERE content_fts @@ plainto_tsquery('italian', $1)
        ORDER BY rank DESC
        LIMIT 20
    """, search_query)
    
    return [dict(row) for row in results]
```

### Integration Notes Story 9.1

- **Task 2**: Indice `idx_chat_messages_content_fts` usa GIN + `to_tsvector('italian')`
- **Colonna Generated**: `content_fts tsvector GENERATED ALWAYS`, sync automatico
- **Partial Index**: Solo record attivi, riduce size ~30%
- **Query Optimization**: Sempre `plainto_tsquery()` per input utente raw

### Performance Considerations

- **GIN Index Size**: ~50% dimensione `content`, 1M conversazioni 500MB → 250MB index
- **Update Overhead**: GIN rebuild parziale ogni INSERT/UPDATE, write ~20% più lente
- **Stop Words**: 150+ parole comuni rimosse, query solo stop words → risultati vuoti
- **Injection Prevention**: `plainto_tsquery()` sanitizza automaticamente

---

## 6. PostgreSQL Partial Indices

### Fonte Ufficiale

- **URL**: https://www.postgresql.org/docs/current/indexes-partial.html
- **Versione**: PostgreSQL 13+ (Feature disponibile da PG 7.2)

### Concetti Chiave

- **Partial Index**: Indice su subset righe definito da predicate WHERE
- **Use Case**: Escludere valori comuni (archiviati, soft-deleted), riduzione 50-80%
- **Query Planner**: Usa partial index SOLO se query WHERE implica matematicamente predicate
- **JSONB Indexing**: `(metadata->>'archived')` extract performante con partial predicate
- **Size Reduction**: Partial su 20% righe attive = index 5x più piccolo

### Pattern Implementativo

```sql
-- Partial index: solo conversazioni NON archiviate
CREATE INDEX idx_conversations_active_user
ON conversations (user_id, created_at)
WHERE (metadata->>'archived')::boolean IS NOT TRUE;

-- Partial FTS: solo record attivi
CREATE INDEX idx_conversations_fts_active  
ON conversations USING GIN (content_fts)
WHERE (metadata->>'archived')::boolean IS NOT TRUE;

-- Partial: session_id ultimi 30 giorni
CREATE INDEX idx_conversations_recent_sessions
ON conversations (session_id, created_at)
WHERE created_at >= NOW() - INTERVAL '30 days';

-- UNIQUE constraint partial: idempotency solo pending
CREATE UNIQUE INDEX idx_outbox_idempotency_pending
ON outbox (idempotency_key)
WHERE status = 'pending';
```

**Query che Beneficiano Partial Index**:

```python
async def get_active_conversations(
    conn: asyncpg.Connection,
    user_id: str,
    limit: int = 50
) -> list[dict]:
    """
    Query conversazioni attive.
    PostgreSQL usa idx_conversations_active_user (partial).
    """
    # WHERE match partial predicate → index usage automatico
    results = await conn.fetch("""
        SELECT conversation_id, session_id, content, created_at
        FROM conversations
        WHERE 
            user_id = $1
            AND (metadata->>'archived')::boolean IS NOT TRUE
        ORDER BY created_at DESC
        LIMIT $2
    """, user_id, limit)
    
    return [dict(row) for row in results]
```

**Verifica Index Usage**:

```python
async def analyze_index_usage(conn: asyncpg.Connection) -> dict:
    """Verifica quale index planner seleziona."""
    explain_result = await conn.fetch("""
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
        SELECT * FROM conversations
        WHERE 
            user_id = 'test-user'
            AND (metadata->>'archived')::boolean IS NOT TRUE
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    plan = explain_result[0]['QUERY PLAN'][0]
    
    return {
        'index_used': 'idx_conversations_active_user' in str(plan),
        'execution_time_ms': plan['Execution Time'],
        'total_cost': plan['Plan']['Total Cost']
    }
```

### Integration Notes Story 9.1

- **Task 2**: Indice `idx_chat_messages_metadata_archived` è partial index
- **Query Pattern**: Tutte query L2 devono includere `WHERE (metadata->>'archived')::boolean IS NOT TRUE`
- **Maintenance**: Dopo archivio batch, PostgreSQL rimuove automaticamente entry, no REINDEX
- **Verification**: EXPLAIN ANALYZE ogni query critica, verificare "Index Scan"

### Critical Considerations

- **Size Reduction**: Dataset 80% archiviati → partial 5x più piccolo (500MB → 100MB)
- **Planner Strict**: `WHERE archived = false` NON match index con `IS NOT TRUE` predicate
- **Maintenance Cost**: Partial rebuild dopo UPDATE che cambia predicate field
- **False Negative**: Query senza predicate esatto triggera Seq Scan, monitorare slow log

---

## Summary — Quick Reference

| Risorsa | Status | Applicazione Story 9.1 |
|---------|--------|------------------------|
| **asyncpg** | ✅ Installato | Task 1, 3: Bulk insert, connection pooling |
| **aiofiles** | ❌ Mancante | Task 8: JSONL outbox log |
| **Circuit Breaker** | 📖 Pattern | Task 3.9-3.12: DB protection |
| **Durable Outbox** | 📖 Pattern | Task 8: Eventual consistency |
| **PG FTS Italian** | 📖 Feature | Task 2: GIN index full-text |
| **PG Partial Index** | 📖 Feature | Task 2: Index optimization |

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-06 | 1.0 | Documentazione tecnica iniziale per Epic 9 | Architecture Team |

---

**Status**: ✅ **READY FOR REFERENCE** — Documentazione completa per implementazione Story 9.1

