# Addendum: Persistent Conversational Memory Architecture

**Epic**: Epic 9 - Persistent Conversational Memory & Long-term Analytics  
**Related Stories**: 9.1, 9.2  
**Status**: Planned  
**Author**: Architecture Team  
**Last Updated**: 2025-11-06

---

## Overview

This addendum defines the architecture for **persistent long-term conversational memory**, extending the existing SHORT-TERM in-memory implementation (Story 7.1) with database persistence, full history retrieval, and search capabilities.

### Problem Statement

**Current Limitations** (Story 7.1 - SHORT-TERM Memory):
- ❌ Volatile in-memory storage (`chat_messages_store` dictionary)
- ❌ Complete data loss on application restart
- ❌ Limited to last 3 conversational turns (6 messages)
- ❌ No cross-session history access
- ❌ No search or analytics on historical data

**Requirements** (Epic 9 - FR9):
- ✅ Database-backed persistence surviving restarts
- ✅ Unlimited historical retention
- ✅ Full session history retrieval with pagination
- ✅ Full-text search across all conversations
- ✅ Archive/export capabilities
- ✅ Analytics integration for long-term trends

---

## Architecture Solution: Hybrid Memory Pattern

### Design Principle

**Hybrid Two-Level Memory Architecture**:
```
┌────────────────────────────────────────────────────────────────┐
│                HYBRID CONVERSATIONAL MEMORY                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   ┌──────────────────────┐         ┌─────────────────────┐   │
│   │   L1 CACHE LAYER     │         │   L2 STORAGE LAYER  │   │
│   │   (In-Memory)        │◄───────►│   (PostgreSQL DB)   │   │
│   ├──────────────────────┤  sync   ├─────────────────────┤   │
│   │ • Last 3 turns       │         │ • Full history      │   │
│   │ • <2000 tokens       │         │ • Unlimited*        │   │
│   │ • Fast access        │         │ • Persistent        │   │
│   │ • LLM context        │         │ • Searchable        │   │
│   │ • Volatile           │         │ • Archived          │   │
│   └──────────────────────┘         └─────────────────────┘   │
│            ↓                                 ↓                 │
│   ┌──────────────────────────────────────────────────────┐   │
│   │         HybridConversationManager                     │   │
│   │  • Async dual-write (cache + DB)                     │   │
│   │  • Cache-first read with DB fallback                 │   │
│   │  • Feature flag controlled (ENABLE_PERSISTENT_MEMORY)│   │
│   │  • Graceful degradation on DB failure                │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hybrid vs Pure DB** | L1 cache preserves fast LLM context window access (<10ms), L2 provides persistence |
| **Async Writes** | Non-blocking DB writes prevent chat latency impact |
| **Cache-First Reads** | Optimize for hot data (recent conversations), minimize DB load |
| **Feature Flag** | Enable gradual rollout, A/B testing, instant rollback capability |
| **Graceful Degradation** | System remains functional if DB unavailable (fallback to in-memory only) |

---

## Component Architecture

### 1. ConversationPersistenceService (NEW)

**Responsibility**: Abstract all database persistence operations for chat messages.

**Interface**:
```python
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class ConversationPersistenceService:
    """
    Database persistence layer for conversational memory.
    Uses asyncpg for async PostgreSQL operations.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def save_messages(
        self,
        session_id: str,
        messages: List[ConversationMessage]
    ) -> bool:
        """
        Persist multiple messages for a session to database.
        
        Args:
            session_id: Unique session identifier
            messages: List of ConversationMessage objects
        
        Returns:
            bool: True if successful, False otherwise
        
        Notes:
            - Bulk insert for performance
            - Idempotent: duplicate message_ids ignored
            - Non-blocking: called async from HybridConversationManager
        """
        pass
    
    async def load_session_history(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = False
    ) -> List[ConversationMessage]:
        """
        Load historical messages for a session with pagination.
        
        Args:
            session_id: Session to retrieve
            limit: Max messages per page (default 100, max 500)
            offset: Pagination offset
            order_desc: If True, newest first (default: chronological)
        
        Returns:
            List of ConversationMessage objects
        
        Notes:
            - Uses INDEX idx_chat_messages_session_created for performance
            - Excludes archived messages (metadata->>'archived' != 'true')
        """
        pass
    
    async def search_conversations(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SearchResult]:
        """
        Full-text search across all conversation content.
        
        Args:
            query: Search keywords (Italian language)
            date_from: Optional start date filter
            date_to: Optional end date filter
            limit: Max results per page
            offset: Pagination offset
        
        Returns:
            List of SearchResult with highlighted excerpts
        
        Notes:
            - Uses GIN index idx_chat_messages_content_fts
            - PostgreSQL to_tsvector('italian', content) for stemming
            - Relevance score based on ts_rank
        """
        pass
    
    async def archive_session(
        self,
        session_id: str,
        permanent: bool = False
    ) -> bool:
        """
        Archive or permanently delete session.
        
        Args:
            session_id: Session to archive
            permanent: If True, DELETE; if False, soft delete (default)
        
        Returns:
            bool: Success status
        
        Notes:
            - Soft delete: UPDATE metadata SET archived = true
            - Permanent delete: DELETE (admin only, audit logged)
        """
        pass
    
    async def export_session(
        self,
        session_id: str,
        format: Literal["json", "csv"]
    ) -> dict | str:
        """
        Export session in specified format.
        
        Args:
            session_id: Session to export
            format: "json" or "csv"
        
        Returns:
            JSON dict or CSV string
        """
        pass
```

**Database Queries Reference**:

```sql
-- Save messages (bulk insert)
INSERT INTO chat_messages (id, session_id, role, content, source_chunk_ids, metadata, created_at)
SELECT * FROM UNNEST($1::uuid[], $2::text[], $3::text[], $4::text[], $5::uuid[][], $6::jsonb[], $7::timestamptz[])
ON CONFLICT (id) DO NOTHING;

-- Load session history (paginated)
SELECT id, session_id, role, content, source_chunk_ids, metadata, created_at
FROM chat_messages
WHERE session_id = $1
  AND (metadata->>'archived' IS NULL OR metadata->>'archived' != 'true')
ORDER BY created_at ASC
LIMIT $2 OFFSET $3;

-- Full-text search (Italian)
SELECT 
    id, session_id, role, content, created_at,
    ts_rank(to_tsvector('italian', content), plainto_tsquery('italian', $1)) AS relevance
FROM chat_messages
WHERE to_tsvector('italian', content) @@ plainto_tsquery('italian', $1)
  AND created_at >= COALESCE($2, '1970-01-01')
  AND created_at <= COALESCE($3, NOW())
ORDER BY relevance DESC, created_at DESC
LIMIT $4 OFFSET $5;

-- Archive session (soft delete)
UPDATE chat_messages
SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{archived}', 'true'::jsonb)
WHERE session_id = $1;

-- Permanent delete (admin only)
DELETE FROM chat_messages WHERE session_id = $1;
```

---

### 2. HybridConversationManager (REFACTOR)

**Responsibility**: Orchestrate L1 cache and L2 persistence, maintaining backward compatibility with existing `ConversationManager`.

**Class Hierarchy**:
```python
ConversationManager (Story 7.1 - existing)
    ↓ extends
HybridConversationManager (Story 9.1 - new)
```

**Key Refactoring**:
```python
from typing import Optional
import asyncio

class HybridConversationManager(ConversationManager):
    """
    Hybrid memory manager with L1 cache + L2 database persistence.
    
    Extends ConversationManager to maintain backward compatibility
    while adding database persistence capabilities.
    """
    
    def __init__(
        self,
        persistence_service: Optional[ConversationPersistenceService] = None,
        enable_persistence: bool = False
    ):
        super().__init__()  # Initialize L1 cache (in-memory)
        self.persistence = persistence_service
        self.persistence_enabled = enable_persistence
        self._write_tasks: List[asyncio.Task] = []
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        source_chunk_ids: Optional[List[str]] = None
    ) -> None:
        """
        Add conversational turn to L1 cache + async write to L2 DB.
        
        Flow:
        1. Call super().add_turn() → updates in-memory cache
        2. If persistence enabled: async write to DB (non-blocking)
        3. Track write task for monitoring
        
        Notes:
            - L1 write is synchronous (fast, in-memory)
            - L2 write is async (non-blocking, fire-and-forget with error handling)
            - If DB write fails, logs error but doesn't block chat
        """
        # L1 cache write (synchronous, fast)
        super().add_turn(session_id, user_message, assistant_message, source_chunk_ids)
        
        # L2 DB write (asynchronous, non-blocking)
        if self.persistence_enabled and self.persistence:
            messages = self._get_messages_for_session(session_id)
            task = asyncio.create_task(
                self._async_persist(session_id, messages)
            )
            self._write_tasks.append(task)
    
    async def _async_persist(
        self,
        session_id: str,
        messages: List[ConversationMessage]
    ) -> None:
        """
        Async persistence with error handling and logging.
        
        Failure modes:
            - DB connection error → log, increment error metric, continue
            - Timeout → log, cancel task, continue
            - Any other error → log, continue
        
        Monitoring:
            - Increment counter: db_writes_attempted
            - Increment counter: db_writes_succeeded / db_writes_failed
            - Histogram: db_write_latency_ms
        """
        try:
            start_time = time.time()
            success = await asyncio.wait_for(
                self.persistence.save_messages(session_id, messages),
                timeout=5.0  # 5s timeout
            )
            latency_ms = (time.time() - start_time) * 1000
            
            if success:
                logger.debug(f"DB persist OK: {session_id}, latency={latency_ms:.0f}ms")
                metrics.increment("db_writes_succeeded")
            else:
                logger.warning(f"DB persist FAILED: {session_id}")
                metrics.increment("db_writes_failed")
            
            metrics.histogram("db_write_latency_ms", latency_ms)
            
        except asyncio.TimeoutError:
            logger.error(f"DB persist TIMEOUT: {session_id}")
            metrics.increment("db_writes_timeout")
        except Exception as e:
            logger.error(f"DB persist ERROR: {session_id}, error={e}")
            metrics.increment("db_writes_error")
    
    async def load_full_history(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ConversationMessage]:
        """
        Load full session history from L2 DB (bypasses L1 cache).
        
        Use cases:
            - User requests conversation history view
            - Admin analytics queries
            - Export operations
        
        Notes:
            - Does NOT populate L1 cache (cache reserved for active context)
            - Uses pagination for large histories
        """
        if not self.persistence_enabled or not self.persistence:
            logger.warning("Persistence not enabled, returning empty history")
            return []
        
        return await self.persistence.load_session_history(
            session_id, limit, offset
        )
    
    def get_context_window(self, session_id: str) -> ChatContextWindow:
        """
        Get L1 cache context window (unchanged from Story 7.1).
        
        Flow:
            1. Read from in-memory chat_messages_store
            2. Apply truncation if exceeds token budget
            3. Return last 3 turns for LLM prompt
        
        Notes:
            - Cache-first, no DB lookup (performance)
            - This is HOT PATH for chat endpoint latency
        """
        return super().get_context_window(session_id)
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear L1 cache for session (DB history untouched).
        
        Use cases:
            - User clicks "New conversation" button
            - Session timeout cleanup
        
        Notes:
            - Only clears in-memory cache
            - DB history remains accessible via load_full_history()
        """
        super().clear_session(session_id)
```

**Feature Flag Integration**:
```python
# apps/api/api/core/config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Epic 9: Persistent Memory Feature Flag
    enable_persistent_memory: bool = Field(
        default=False,
        env="ENABLE_PERSISTENT_MEMORY",
        description="Enable long-term conversation memory persistence to database"
    )

# apps/api/api/main.py
from api.services.conversation_service import HybridConversationManager
from api.services.persistence_service import ConversationPersistenceService

settings = get_settings()

# Initialize persistence service if enabled
persistence_service = None
if settings.enable_persistent_memory:
    persistence_service = ConversationPersistenceService(db_pool=get_db_pool())

# Initialize conversation manager
conv_manager = HybridConversationManager(
    persistence_service=persistence_service,
    enable_persistence=settings.enable_persistent_memory
)
```

---

## Database Schema

### Existing Table: `chat_messages`

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    source_chunk_ids UUID[],
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### New Indices (Epic 9 Story 9.1)

```sql
-- Primary query pattern: load session history chronologically
CREATE INDEX idx_chat_messages_session_created 
    ON chat_messages(session_id, created_at DESC);

-- Analytics pattern: recent messages across all sessions
CREATE INDEX idx_chat_messages_created_at 
    ON chat_messages(created_at DESC);

-- Full-text search pattern (Italian language)
CREATE INDEX idx_chat_messages_content_fts 
    ON chat_messages 
    USING GIN (to_tsvector('italian', content));

-- Archive filter pattern: exclude archived sessions
CREATE INDEX idx_chat_messages_metadata_archived
    ON chat_messages((metadata->>'archived'))
    WHERE (metadata->>'archived') IS NOT NULL;
```

**Index Size Estimates**:
- `idx_chat_messages_session_created`: ~500KB per 10K messages
- `idx_chat_messages_created_at`: ~200KB per 10K messages
- `idx_chat_messages_content_fts`: ~2MB per 10K messages (GIN index overhead)
- Total overhead: ~2.7MB per 10K messages

**Annual Storage Estimate**:
- Messages/day: 50
- Messages/year: 18,250
- Raw data: ~3.6MB (200 bytes/msg * 18,250)
- Indices: ~5MB (overhead)
- **Total: ~9MB/year** (well within Supabase Free Tier 500MB)

---

## API Endpoints (Story 9.2)

### GET /chat/sessions/{sessionId}/history/full

**Purpose**: Retrieve complete historical messages for a session.

**Request**:
```http
GET /api/v1/chat/sessions/abc-123/history/full?limit=100&offset=0
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `limit` (optional, default 100, max 500): Messages per page
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "session_id": "abc-123",
  "messages": [
    {
      "id": "msg-uuid-1",
      "role": "user",
      "content": "Quali sono gli esercizi per la lombalgia?",
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "assistant",
      "content": "Gli esercizi raccomandati includono...",
      "source_chunk_ids": ["chunk-1", "chunk-2"],
      "created_at": "2025-01-15T10:30:05Z"
    }
  ],
  "total_count": 234,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

**Implementation**:
```python
@router.get("/sessions/{session_id}/history/full")
@rate_limit(60)  # 60 requests per minute
async def get_session_history(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Load full session history with pagination."""
    messages = await conv_manager.load_full_history(session_id, limit, offset)
    total_count = await persistence_service.count_session_messages(session_id)
    
    return {
        "session_id": session_id,
        "messages": [msg.dict() for msg in messages],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(messages) < total_count
    }
```

---

### GET /chat/sessions/search

**Purpose**: Full-text search across all user conversations.

**Request**:
```http
GET /api/v1/chat/sessions/search?query=lombalgia&date_from=2025-01-01&limit=50
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `query` (required): Search keywords
- `date_from` (optional): ISO 8601 date filter (start)
- `date_to` (optional): ISO 8601 date filter (end)
- `limit` (optional, default 50, max 100): Results per page
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "query": "lombalgia",
  "filters": {
    "date_from": "2025-01-01",
    "date_to": null
  },
  "matches": [
    {
      "session_id": "abc-123",
      "message_id": "msg-uuid-2",
      "role": "assistant",
      "excerpt": "...esercizi per <b>lombalgia</b> includono stretching...",
      "created_at": "2025-01-15T10:30:05Z",
      "relevance_score": 0.89
    },
    {
      "session_id": "def-456",
      "message_id": "msg-uuid-5",
      "role": "user",
      "excerpt": "Quali esercizi per <b>lombalgia</b> acuta?",
      "created_at": "2025-01-10T14:20:00Z",
      "relevance_score": 0.76
    }
  ],
  "total_matches": 12,
  "limit": 50,
  "offset": 0
}
```

**Implementation Note**: Uses PostgreSQL `to_tsvector('italian', content)` for Italian language stemming and search.

---

### DELETE /chat/sessions/{sessionId}/archive

**Purpose**: Archive (soft delete) or permanently delete session.

**Request**:
```http
DELETE /api/v1/chat/sessions/abc-123/archive?permanent=false
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `permanent` (optional, default false): 
  - `false`: Soft delete (sets `metadata.archived = true`)
  - `true`: Permanent DELETE (Admin only, audit logged)

**Response** (200 OK):
```json
{
  "archived": true,
  "session_id": "abc-123",
  "permanent": false,
  "message": "Session soft-deleted successfully"
}
```

**Authorization**:
- Soft delete: Any authenticated user (own sessions only)
- Permanent delete: Admin role required

---

## Performance Characteristics

### Read Performance

| Operation | Source | Latency Target | Notes |
|-----------|--------|----------------|-------|
| **get_context_window()** | L1 cache | <10ms | HOT PATH: in-memory dict lookup |
| **load_full_history()** | L2 DB | <500ms p95 | Indexed query, paginated |
| **search_conversations()** | L2 DB | <800ms p95 | GIN index FTS, complexity O(log n) |

### Write Performance

| Operation | Mode | Latency Target | Notes |
|-----------|------|----------------|-------|
| **add_turn() L1 write** | Sync | <5ms | In-memory update, blocking |
| **add_turn() L2 write** | Async | N/A | Fire-and-forget, non-blocking |
| **DB persist completion** | Async | <100ms p95 | Background task, monitored |

### Cache Performance

**Target Metrics**:
- **Cache Hit Rate**: >95% (for active sessions)
- **Cache Miss Penalty**: <500ms (DB fallback query)
- **Memory Overhead**: ~2KB per active session (~200 sessions = 400KB)

**Cache Invalidation**: No explicit invalidation needed. L1 cache is ephemeral per process instance.

---

## Failure Modes & Graceful Degradation

### Scenario 1: Database Unavailable

**Symptoms**: Connection errors, timeouts on DB operations.

**Behavior**:
1. `add_turn()` succeeds (L1 cache write)
2. Async DB write fails, logged as error
3. Metrics incremented: `db_writes_failed`
4. Chat functionality continues uninterrupted
5. User sees no impact (in-memory mode)

**Recovery**: When DB restored, new messages persist normally. Historical gap remains.

---

### Scenario 2: Feature Flag Disabled

**Behavior**:
1. `HybridConversationManager` initialized without persistence
2. All operations use L1 cache only (Story 7.1 behavior)
3. System behaves identically to pre-Epic-9

**Use Case**: Instant rollback if issues detected.

---

### Scenario 3: DB Write Latency Spike

**Symptoms**: `db_write_latency_ms` metric >500ms sustained.

**Behavior**:
1. Async writes queue up (non-blocking)
2. If queue depth >100 tasks, log warning
3. Chat latency unaffected (async design)
4. Monitor for DB scaling needs

**Mitigation**: Alert triggers investigation, potential DB optimization or scaling.

---

## Monitoring & Observability

### Key Metrics (Story 9.1)

```python
# Performance metrics
metrics.histogram("db_write_latency_ms", latency)
metrics.histogram("db_read_latency_ms", latency)

# Success/Failure counters
metrics.increment("db_writes_succeeded")
metrics.increment("db_writes_failed")
metrics.increment("db_writes_timeout")
metrics.increment("cache_hits")
metrics.increment("cache_misses")

# Business metrics
metrics.gauge("active_sessions_count", count)
metrics.gauge("persistent_messages_count", count)
metrics.histogram("session_message_count", count)
```

### Logging

```python
logger.info("Persistence enabled", extra={
    "feature_flag": settings.enable_persistent_memory
})

logger.debug("DB persist OK", extra={
    "session_id": session_id,
    "message_count": len(messages),
    "latency_ms": latency
})

logger.error("DB persist FAILED", extra={
    "session_id": session_id,
    "error": str(e),
    "retry_count": retry
})
```

### Alerts

```yaml
- name: db_write_failure_rate
  condition: db_writes_failed / db_writes_attempted > 0.05
  severity: warning
  duration: 5m

- name: db_write_latency_high
  condition: db_write_latency_ms p95 > 500ms
  severity: warning
  duration: 10m

- name: cache_hit_rate_low
  condition: cache_hits / (cache_hits + cache_misses) < 0.90
  severity: info
  duration: 15m
```

---

## Testing Strategy

### Unit Tests (Story 9.1)

**ConversationPersistenceService**:
- ✅ `save_messages()` bulk insert
- ✅ `load_session_history()` pagination
- ✅ `search_conversations()` FTS with Italian stemming
- ✅ `archive_session()` soft/permanent delete

**HybridConversationManager**:
- ✅ `add_turn()` dual-write (cache + DB)
- ✅ `get_context_window()` cache-first read
- ✅ `load_full_history()` DB fallback
- ✅ Graceful degradation when DB unavailable

### Integration Tests (Story 9.1)

```python
async def test_hybrid_memory_end_to_end():
    """Test full flow: write cache → write DB → read from DB."""
    manager = HybridConversationManager(persistence_enabled=True)
    
    # Write conversation turn
    manager.add_turn("session-1", "User message", "Assistant response")
    
    # Wait for async DB write
    await asyncio.sleep(0.2)
    
    # Verify L1 cache
    context = manager.get_context_window("session-1")
    assert len(context.messages) == 2
    
    # Verify L2 DB persistence
    history = await manager.load_full_history("session-1")
    assert len(history) == 2
    assert history[0].content == "User message"
    assert history[1].content == "Assistant response"
```

### Performance Tests (Story 9.1)

```python
async def test_db_write_latency():
    """Verify DB writes complete within 100ms p95."""
    latencies = []
    for _ in range(100):
        start = time.time()
        await persistence.save_messages(session_id, messages)
        latencies.append(time.time() - start)
    
    p95_latency = np.percentile(latencies, 95)
    assert p95_latency < 0.1  # 100ms threshold
```

---

## Migration & Rollout Strategy

### Phase 1: Deploy with Flag OFF (Day 1)

```bash
# Deploy code with feature disabled
ENABLE_PERSISTENT_MEMORY=false
```

**Goal**: Validate deployment stability, no behavior change.

---

### Phase 2: Canary Rollout (Days 2-3)

```bash
# Enable for 10% of sessions (load balancer routing or user sampling)
ENABLE_PERSISTENT_MEMORY=true  # Applied to 10% instances
```

**Monitoring**:
- DB write latency p95 < 100ms
- Cache hit rate > 95%
- Error rate < 0.1%
- Chat endpoint latency unchanged

**Go/No-Go Decision**: If metrics healthy for 24h → proceed to 50%.

---

### Phase 3: Gradual Expansion (Days 4-5)

```bash
# 50% rollout
ENABLE_PERSISTENT_MEMORY=true  # 50% instances
```

**Continue monitoring**, expand to 100% if stable.

---

### Phase 4: Feature Flag Removal (Week 3)

After 2 weeks stable operation at 100%:
1. Remove `enable_persistent_memory` setting
2. Remove fallback code paths (in-memory only mode)
3. Simplify `HybridConversationManager` (persistence always on)

---

## Related Documentation

**Story References**:
- Story 7.1: Academic Conversational RAG (SHORT-TERM memory baseline)
- Story 9.1: Hybrid Memory Foundation
- Story 9.2: Full History API
- Story 9.3: Frontend History UI

**Architecture References**:
- `addendum-conversational-memory-patterns.md`: SHORT-TERM implementation
- `addendum-asyncpg-database-pattern.md`: Async DB query patterns
- `addendum-technical-references-epic9.md`: **Technical patterns & libraries reference**
- `sezione-4-modelli-di-dati.md`: Database schema

**Technical References** (External):
- asyncpg: Bulk insert, connection pooling → `addendum-technical-references-epic9.md#1`
- aiofiles: Async file I/O → `addendum-technical-references-epic9.md#2`
- Circuit Breaker Pattern (Martin Fowler) → `addendum-technical-references-epic9.md#3`
- Durable Outbox Pattern (Chris Richardson) → `addendum-technical-references-epic9.md#4`
- PostgreSQL FTS Italian → `addendum-technical-references-epic9.md#5`
- PostgreSQL Partial Indices → `addendum-technical-references-epic9.md#6`

**PRD References**:
- `sezione-2-requirements.md`: FR9 requirement
- `sezione-epic-9-dettagli.md`: Epic 9 specification

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-06 | 1.0 | Initial architecture specification | Architecture Team |

---

**Status**: 📝 **PLANNED** — Ready for Story 9.1 Implementation

