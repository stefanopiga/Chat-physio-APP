# Epic 9: Persistent Conversational Memory & Long-term Analytics

**Epic ID**: Epic 9  
**Priority**: P2 (Post-MVP Phase 2 Enhancement)  
**Status**: In Progress (Story 9.1-9.2 Done)  
**Estimated Effort**: 31-41 hours base + 6-8h Story 9.6 optional (~1.5-2 settimane)

---

## Epic Overview

### Goal Statement

Implementare un sistema di memoria conversazionale **persistente long-term** che superi i limiti della memoria SHORT-TERM volatile (in-memory) attuale, permettendo agli studenti di accedere allo storico completo delle conversazioni anche dopo riavvio applicazione, e fornendo agli amministratori strumenti avanzati di ricerca, archiviazione e analytics sulle interazioni.

### Current State (Baseline)

**Story 7.1 Implementation**:
- Memoria conversazionale SHORT-TERM (ultimi 3 turni, 6 messaggi)
- Storage in-memory volatile (`chat_messages_store` dictionary)
- Perdita completa cronologia al riavvio applicazione
- Nessuna capacità di ricerca storico sessioni
- Limitata visibilità trend conversazionali per analytics

**Limitations**:
- ❌ Storico perso permanentemente al restart
- ❌ Impossibile analizzare trend long-term
- ❌ Nessun supporto ricerca conversazioni passate
- ❌ Analytics limitata a sessione corrente

### Target State (Epic 9 Completion)

**Enhanced Capabilities**:
- ✅ Memoria persistente su database PostgreSQL (Supabase)
- ✅ Storico completo conversazioni accessibile cross-session
- ✅ API full history retrieval con pagination
- ✅ UI cronologia conversazioni per studenti
- ✅ Search interface full-text su contenuti storici
- ✅ Archive & export capabilities (JSON/CSV)
- ✅ Enhanced analytics dashboard con trend long-term

---

## Business Value & User Impact

### Student Value

**Primary Benefits**:
1. **Continuità Conversazionale**: Riprendere conversazioni precedenti senza perdita contesto
2. **Ricerca Rapida**: Ritrovare rapidamente risposte date in passato
3. **Studio Efficace**: Usare cronologia come risorsa studio integrativa
4. **Persistenza Dati**: Garanzia nessuna perdita informazioni preziose

**Use Cases**:
- Studente riprende studio dopo pausa, vuole rivedere domande fatte ieri
- Studente cerca risposta specifica data settimane fa su argomento X
- Studente esporta cronologia conversazioni per revisione pre-esame

### Admin Value

**Primary Benefits**:
1. **Analytics Approfondita**: Comprensione pattern domande long-term
2. **Quality Assessment**: Valutazione efficacia risposte nel tempo
3. **Content Gap Analysis**: Identificazione argomenti richiesti ma poco coperti
4. **Usage Trends**: Monitoraggio adozione sistema e periodi picco utilizzo

**Use Cases**:
- Professore analizza trend domande per migliorare materiale didattico
- Admin identifica sessioni problematiche per QA
- Admin esporta dati conversazioni per report accademici

---

## Technical Architecture

### Hybrid Memory Pattern

```
┌─────────────────────────────────────────────────────────┐
│              HYBRID CONVERSATIONAL MEMORY               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   L1 Cache (In-Memory)         L2 Storage (Database)   │
│   ┌───────────────────┐        ┌──────────────────┐   │
│   │ Last 3 turns      │        │ Full history     │   │
│   │ Fast access       │        │ Persistent       │   │
│   │ Token budget      │◄──────►│ Searchable       │   │
│   │ <2000 tokens      │ sync   │ Unlimited*       │   │
│   └───────────────────┘        └──────────────────┘   │
│            │                            │               │
│            └────────────┬───────────────┘               │
│                         ▼                               │
│            HybridConversationManager                    │
│            - Async write DB                             │
│            - Cache-first read                           │
│            - Feature flag controlled                    │
│            - Graceful degradation                       │
└─────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. ConversationPersistenceService (NEW)

**Responsibilities**:
- Async write operations to `chat_messages` table
- Bulk load session history from database
- Full-text search implementation
- Archive/soft delete management

**Key Methods**:
```python
class ConversationPersistenceService:
    async def save_messages(session_id: str, messages: List[ConversationMessage])
    async def load_session_history(session_id: str, limit: int = 100, offset: int = 0)
    async def search_conversations(query: str, filters: SearchFilters)
    async def archive_session(session_id: str, soft_delete: bool = True)
    async def export_session(session_id: str, format: ExportFormat)
```

#### 2. HybridConversationManager (REFACTOR)

**Extends**: Current `ConversationManager`  
**New Capabilities**:
- Dual-write: in-memory cache + async DB persistence
- Cache-first read with DB fallback
- Feature flag integration (`ENABLE_PERSISTENT_MEMORY`)
- Graceful degradation if DB unavailable

#### 3. Feature Flag System

**Environment Variable**: `ENABLE_PERSISTENT_MEMORY` (boolean, default: `false`)

**Rollout Strategy**:
1. Deploy with flag OFF (behavior invariato)
2. Canary: Enable per 10% users → monitor 24h
3. Gradual: 10% → 50% → 100% based on metrics
4. Remove flag after 2 weeks stable operation

---

## Database Schema Enhancements

### Existing Table: `chat_messages`

**Current Schema**:
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

### New Indices Required

**Performance Optimization**:
```sql
-- Epic 9 Story 9.1: Indices per query performance
CREATE INDEX idx_chat_messages_session_created 
    ON chat_messages(session_id, created_at DESC);

CREATE INDEX idx_chat_messages_created_at 
    ON chat_messages(created_at DESC);

-- Epic 9 Story 9.2: Full-text search index (Italian)
CREATE INDEX idx_chat_messages_content_fts 
    ON chat_messages 
    USING GIN (to_tsvector('italian', content));
```

**Storage Estimate**:
- Average message: 200 bytes
- Daily usage: 50 messages/day
- Monthly storage: ~300KB
- Annual storage: ~3.6MB
- **Cost**: Within Supabase Free Tier (500MB limit)

---

## User Stories Breakdown

### Story 9.1: Hybrid Memory Foundation (P0) — 12-15h

**Goal**: Implementare layer persistenza e refactoring architettura memoria per supporto hybrid cache + database.

**Acceptance Criteria**:
1. `ConversationPersistenceService` implementato con save/load operations
2. `HybridConversationManager` refactoring da `ConversationManager` completato
3. Feature flag `ENABLE_PERSISTENT_MEMORY` integrato
4. Database indices ottimizzati creati
5. Unit tests >80% coverage nuove classi
6. Integration test: write cache → write DB → read from DB
7. Graceful degradation: se DB fail, fallback a in-memory only

**Technical Tasks**:
- Create `ConversationPersistenceService` class
- Refactor `ConversationManager` → `HybridConversationManager`
- Implement async dual-write pattern
- Add DB indices per query optimization
- Implement feature flag logic
- Write comprehensive test suite

**Dev Notes**:
- Usa `asyncpg` per DB operations (pattern esistente)
- Mantieni backward compatibility con in-memory mode
- Logging dettagliato per debugging dual-write
- Metrics: cache hit rate, DB write latency, errors

---

### Story 9.2: Full History API (P1) — 4-6h

**Goal**: Esporre API REST per recupero storico completo, ricerca full-text e archiviazione sessioni.

**Acceptance Criteria**:
1. Endpoint `GET /chat/sessions/{sessionId}/history/full` implementato
2. Endpoint `GET /chat/sessions/search` con full-text search funzionante
3. Endpoint `DELETE /chat/sessions/{sessionId}/archive` per soft delete
4. Pagination implementata (default 100 items, max 500)
5. Full-text search supporta lingua italiana
6. Rate limiting applicato (60 req/min per user)
7. OpenAPI spec aggiornata con nuovi endpoints

**API Specifications**:

#### GET /chat/sessions/{sessionId}/history/full

**Request**:
```http
GET /chat/sessions/{sessionId}/history/full?limit=100&offset=0
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "Quali sono gli esercizi per lombalgia?",
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Gli esercizi raccomandati per la lombalgia includono...",
      "source_chunk_ids": ["uuid1", "uuid2"],
      "created_at": "2025-01-15T10:30:05Z"
    }
  ],
  "total_count": 234,
  "has_more": true
}
```

#### GET /chat/sessions/search

**Request**:
```http
GET /chat/sessions/search?query=lombalgia&date_from=2025-01-01&limit=50
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "query": "lombalgia",
  "matches": [
    {
      "session_id": "uuid",
      "message_id": "uuid",
      "role": "assistant",
      "excerpt": "...esercizi per <b>lombalgia</b> includono stretching...",
      "created_at": "2025-01-15T10:30:05Z",
      "relevance_score": 0.89
    }
  ],
  "total_matches": 12
}
```

#### DELETE /chat/sessions/{sessionId}/archive

**Request**:
```http
DELETE /chat/sessions/{sessionId}/archive?permanent=false
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "archived": true,
  "session_id": "uuid",
  "permanent": false
}
```

**Dev Notes**:
- Riutilizza auth middleware esistente (JWT Supabase)
- Rate limiting: usa decorator `@rate_limit` esistente
- Full-text search: PostgreSQL `to_tsvector('italian', content)`
- Soft delete: `metadata->>'archived' = 'true'`, non DELETE fisico

---

### Story 9.3: Chat Session Management UI (P1) — 6-7h

**Goal**: Implementare UI React per gestione completa sessioni chat (create, rename, delete, navigation) tramite menu laterale sidebar.

**⚠️ CHANGE NOTE**: Requisiti modificati rispetto versione originale Epic 9. Story originale 9.3 (ConversationTimeline + HistorySearchBar + SessionDetailView) spostata a Story 9.6 come enhancement opzionale. Nuova Story 9.3 implementa funzionalità foundational session management richieste dall'utente.

**Acceptance Criteria**:
1. Sidebar menu implementato con toggle sandwich icon (hamburger) in header
2. Sidebar mostra lista completa conversazioni (session IDs visibili)
3. Click conversazione → carica history e continua in chat principale
4. "New Chat" button crea nuova sessione e pulisce UI
5. Menu 3 pallini (⋮) per ogni conversazione con opzioni "Rename" e "Delete"
6. Rename dialog: input text con conferma/annulla, aggiorna metadata DB
7. Delete dialog: conferma "Sei sicuro?" con opzioni "Prosegui" e "Annulla"
8. Delete elimina completamente da DB (non solo UI) via backend endpoint
9. Sidebar responsive: slide-in overlay mobile, persistent desktop >1024px
10. Backend endpoint `DELETE /chat/sessions/{sessionId}` implementato

**UI Layout Specification**:

```
┌────────┬──────────────────────────────────┐
│ ☰ Logo │         App Header               │  ← Sandwich icon toggle sidebar
├────────┴──────────────────────────────────┤
│                                            │
│  [Sidebar Overlay]    Main Chat Content   │
│  ┌──────────────┐                         │
│  │ + New Chat   │                         │
│  ├──────────────┤                         │
│  │ Conv 1  ⋮    │← Click → load in chat   │
│  │ Conv 2  ⋮    │← ⋮ menu → rename/delete │
│  │ Conv 3  ⋮    │                         │
│  │ Conv 4  ⋮    │                         │
│  └──────────────┘                         │
│                                            │
└────────────────────────────────────────────┘
```

**Interaction Flows**:

1. **New Chat Flow**:
   - Click "New Chat" → generate new sessionId → clear messages array → focus input

2. **Load Conversation Flow**:
   - Click conversation → load history via API (Story 9.2) → populate chat → close sidebar mobile

3. **Rename Flow**:
   - Click ⋮ → "Rename" → dialog con input → conferma → PATCH `/chat/sessions/{id}/metadata` → update UI list

4. **Delete Flow**:
   - Click ⋮ → "Delete" → dialog "Sei sicuro di voler eliminare questa conversazione?" → "Prosegui"/"Annulla"
   - If "Prosegui" → DELETE `/chat/sessions/{id}` → rimuovi da lista UI → se conversazione corrente, trigger "New Chat"

**Technical Components**:

- `ChatSidebar.tsx`: Main sidebar component con lista sessioni
- `SessionListItem.tsx`: Single conversation item con 3-dot menu
- `SessionMenuDropdown.tsx`: Dropdown menu con Rename/Delete
- `RenameDialog.tsx`: Modal input rename con conferma
- `DeleteConfirmDialog.tsx`: Modal conferma eliminazione
- `useSessionManagement.ts`: Custom hook per CRUD operations

**Dev Notes**:
- Sidebar: Shadcn/UI `Sheet` component (mobile) + persistent `aside` (desktop)
- 3-dot menu: Shadcn/UI `DropdownMenu`
- Dialogs: Shadcn/UI `Dialog` + `AlertDialog`
- State: Zustand store per lista sessioni attive
- Backend: nuovo endpoint DELETE con hard delete DB (`DELETE FROM chat_messages WHERE session_id = ?`)

---

### Story 9.4: Archive & Export (P2) — 4-5h

**Goal**: Implementare funzionalità archiviazione sessioni e export dati in formati strutturati.

**Acceptance Criteria**:
1. Soft delete sessioni (mantiene DB, nasconde UI)
2. Permanent delete solo per Admin con conferma doppia
3. Export JSON format implementato
4. Export CSV format implementato
5. Bulk operations: archivia multiple sessioni
6. UI conferma prima delete permanente
7. Admin logs per audit trail delete operations

**Export Formats**:

**JSON Export**:
```json
{
  "session_id": "uuid",
  "created_at": "2025-01-15T10:30:00Z",
  "messages": [
    {
      "role": "user",
      "content": "...",
      "timestamp": "..."
    },
    {
      "role": "assistant",
      "content": "...",
      "sources": ["doc_id_1", "doc_id_2"],
      "timestamp": "..."
    }
  ],
  "metadata": {
    "total_turns": 6,
    "avg_response_time_ms": 3200
  }
}
```

**CSV Export**:
```csv
session_id,timestamp,role,content,sources
uuid,2025-01-15T10:30:00Z,user,"Quali esercizi...",
uuid,2025-01-15T10:30:05Z,assistant,"Gli esercizi...",doc_1;doc_2
```

**Dev Notes**:
- Soft delete: flag `metadata->>'archived' = 'true'`
- Permanent delete: `DELETE FROM chat_messages WHERE session_id = ?`
- Export: streaming response per grandi dataset
- Audit: log in `admin_actions` table con user_id, action, timestamp

---

### Story 9.5: Enhanced Analytics (P2) — 5-7h

**Goal**: Integrare memoria persistente con dashboard analytics esistente (Story 4.2) per analisi trend long-term.

**Acceptance Criteria**:
1. Analytics dashboard mostra metrics long-term (30/60/90 giorni)
2. Trend analysis: domande più frequenti per periodo
3. Session duration distribution chart
4. Peak usage hours heatmap
5. Content gap analysis: argomenti richiesti vs copertura docs
6. Export analytics report (PDF)
7. Real-time metrics + historical data integration

**New Analytics Metrics**:

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| **Total Conversations** | Numero totale sessioni | Daily/Weekly/Monthly |
| **Avg Messages/Session** | Media messaggi per conversazione | Rolling 7/30 giorni |
| **Peak Usage Hours** | Ore giorno con più attività | Heatmap 24h x 7 giorni |
| **Top Keywords** | Argomenti più discussi | Word cloud, top 20 |
| **Response Quality Trend** | Feedback 👍/👎 nel tempo | Time series chart |
| **Session Duration** | Tempo medio conversazione | Distribution histogram |

**Integration Points**:
- Story 4.2 existing dashboard: add new tab "Long-term Analytics"
- Reuse analytics service infrastructure
- PostgreSQL queries: aggregate functions, window functions
- Charts: Recharts library (già usata)

**Dev Notes**:
- Query optimization: pre-aggregate data per performance
- Cache: Redis per analytics queries costose (TTL 1h)
- Export: use Puppeteer per PDF generation
- Permissions: analytics visible only to Admin role

---

### Story 9.6: Advanced History UI (P3 - Optional Enhancement) — 6-8h

**Goal**: Implementare UI avanzata per visualizzazione cronologia conversazioni, ricerca full-text e navigazione storico.

**⚠️ NOTE**: Story originale 9.3 spostata qui come enhancement opzionale. Implementare DOPO Story 9.3 (session management foundational).

**Acceptance Criteria**:
1. `ConversationTimeline` component mostra lista sessioni con preview primo messaggio
2. `HistorySearchBar` component con autocomplete keywords full-text
3. `SessionDetailView` component per espansione singola conversazione
4. Infinite scroll implementato per performance
5. Highlight search terms nei risultati
6. Export session button (JSON download)
7. Responsive design (mobile-first)
8. E2E tests per user flows principali

**UI Components Specifications**:

#### ConversationTimeline

**Purpose**: Lista cronologica sessioni con preview primo messaggio.

**Props**:
```typescript
interface ConversationTimelineProps {
  sessions: ConversationSession[];
  onSessionClick: (sessionId: string) => void;
  onLoadMore: () => void;
  hasMore: boolean;
}
```

**Layout**:
```
┌─────────────────────────────────────────┐
│ 🔍 Search conversations...              │
├─────────────────────────────────────────┤
│ 📅 15 Gen 2025, 10:30                   │
│ Q: Quali esercizi per lombalgia?        │
│ 💬 12 messages                           │
├─────────────────────────────────────────┤
│ 📅 14 Gen 2025, 15:20                   │
│ Q: Come trattare distorsione caviglia?  │
│ 💬 8 messages                            │
├─────────────────────────────────────────┤
│           Load More...                   │
└─────────────────────────────────────────┘
```

#### HistorySearchBar

**Purpose**: Ricerca full-text con suggestions.

**Features**:
- Debounced input (300ms)
- Keyword highlighting in results
- Recent searches cache
- Clear button

#### SessionDetailView

**Purpose**: Espansione conversazione completa con citazioni.

**Features**:
- Conversazione completa user/assistant alternata
- Citazioni espandibili (popover esistente)
- Export button (JSON download)
- "Continue conversation" link to chat

**Dev Notes**:
- Riusa componenti chat esistenti per message rendering
- Infinite scroll: `react-infinite-scroll-component`
- State management: React Query per caching
- Accessibility: keyboard navigation, ARIA labels
- Integra con Story 9.2 (full-text search endpoint già disponibile)

---

## Implementation Timeline

### Phased Rollout Strategy

**Phase 1 - Backend Foundation** (Week 1):
```
Days 1-3: Story 9.1 + 9.2
├── Day 1: ConversationPersistenceService implementation
├── Day 2: HybridConversationManager refactoring + tests
└── Day 3: API endpoints + OpenAPI spec update
```

**Phase 2 - Frontend UX** (Week 1):
```
Day 4-5: Story 9.3
├── Day 4: ConversationTimeline + HistorySearchBar components
└── Day 5: SessionDetailView + E2E tests
```

**Phase 3 - Advanced Features** (Week 2):
```
Days 6-8: Story 9.4 + 9.5
├── Day 6: Archive & Export functionality
├── Day 7: Analytics integration + new charts
└── Day 8: Integration testing + bug fixes
```

**Phase 4 - Rollout** (Week 2-3):
```
Days 9-15: Gradual Production Rollout
├── Day 9: Deploy with feature flag OFF
├── Day 10-11: Canary 10% users, monitor metrics
├── Day 12-13: Rollout 50% users
├── Day 14-15: Full rollout 100%, final monitoring
```

---

## Success Metrics & KPIs

### Technical Metrics

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Cache Hit Rate** | >95% | <90% (investigate) |
| **DB Write Latency** | <100ms p95 | >200ms (alert) |
| **Full History Query** | <500ms p95 | >1000ms (optimize) |
| **Storage Growth** | <10MB/month | >50MB/month (review) |
| **Error Rate** | <0.1% | >1% (incident) |

### Adoption Metrics

| Metric | Target (30 giorni) | Measurement |
|--------|-------------------|-------------|
| **Feature Usage Rate** | >30% active sessions use history | Analytics tracking |
| **Search Queries** | >5% sessions perform search | API metrics |
| **Avg History Views** | >2 views per active user | UI analytics |
| **Export Downloads** | >10 exports/month | Download counter |

### User Satisfaction

| Metric | Target | Collection Method |
|--------|--------|------------------|
| **Bug Reports** | 0 critical bugs | Issue tracker |
| **User Feedback** | >80% positive | In-app survey |
| **Performance Complaints** | 0 complaints | Support tickets |

---

## Risk Assessment & Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **R1: Performance degradation queries** | Medium | Medium | Indices ottimizzati, pagination obbligatoria, query monitoring |
| **R2: Cache invalidation bugs** | Low | Medium | Feature flag rollback, extensive testing, logging dettagliato |
| **R3: Storage cost overrun** | Low | Low | Alert >25MB usage, retention policy 1 anno, soft delete default |
| **R4: Data loss during migration** | Low | High | Zero migration (new feature), backup automatico Supabase |
| **R5: Feature flag technical debt** | Medium | Low | Removal pianificato 2 settimane post-rollout, documented process |

### Rollback Strategy

**Immediate Rollback**:
1. Set `ENABLE_PERSISTENT_MEMORY=false` in env vars
2. Restart API service (zero downtime deployment)
3. Sistema torna a in-memory only mode
4. Nessuna perdita dati: DB rimane popolato per retry successivo

**Rollback Triggers**:
- Error rate >1%
- DB write latency >500ms p95 sustained 10min
- Cache hit rate <80%
- Critical bug impacting core chat functionality

---

## Dependencies & Prerequisites

### Required Completed Stories

- [x] **Story 7.1**: Academic Conversational RAG (memoria SHORT-TERM) ✅
- [x] **Epic 2**: Core Knowledge Pipeline (DB schema `chat_messages`) ✅
- [x] **Epic 4**: Admin Dashboard infrastructure (per analytics integration) ✅

### External Dependencies

- [x] Supabase PostgreSQL database operational ✅
- [x] `asyncpg` library available (già in uso) ✅
- [x] React Query library available (già in uso) ✅
- [x] Feature flag infrastructure ready ✅

**Status**: All dependencies satisfied, Epic 9 ready for implementation.

---

## Cost Analysis

### Development Cost

| Phase | Hours | Cost (€50/h) |
|-------|-------|--------------|
| Story 9.1 | 12-15h | €600-750 |
| Story 9.2 | 4-6h | €200-300 |
| Story 9.3 | 6-8h | €300-400 |
| Story 9.4 | 4-5h | €200-250 |
| Story 9.5 | 5-7h | €250-350 |
| **TOTAL** | **31-41h** | **€1,550-2,050** |

### Operational Cost

**Annual Infrastructure** (Supabase Free Tier):
- Database storage: 60MB/anno → **€0** (Free Tier: 500MB)
- Database queries: Unlimited → **€0** (Free Tier)
- Bandwidth: Negligible → **€0** (Free Tier: 5GB)

**Total Annual Operational Cost**: **€0** (within Free Tier 1-2 anni)

**Cost Increase vs Current**: **0%**

---

## Acceptance Criteria (Epic Level)

Epic 9 is considered **COMPLETE** when:

- [x] All 5 stories (9.1-9.5) marked as "Done"
- [x] Feature deployed to production with flag enabled 100% users
- [x] Success metrics met for 30 giorni consecutivi:
  - Cache hit rate >95%
  - Feature usage >30% active users
  - Error rate <0.1%
  - Zero critical bugs
- [x] Documentation updated:
  - Architecture addendum created
  - API spec includes new endpoints
  - Frontend spec includes Flow 5
  - User guide updated with history features
- [x] Feature flag removed from codebase
- [x] Retrospective completed with lessons learned documented

---

## Related Documentation

**Architecture References**:
- `docs/architecture/addendum-conversational-memory-patterns.md` — Current SHORT-TERM implementation
- `docs/architecture/addendum-persistent-conversational-memory.md` — Epic 9 architecture spec (TO BE CREATED)
- `docs/architecture/sezione-4-modelli-di-dati.md` — Database schema `chat_messages`

**Requirements References**:
- `docs/prd/sezione-2-requirements.md` — FR9 requirement
- `docs/prd/sezione-epic-4-dettagli-post-mvp-enhancements.md` — Story 4.2 analytics context

**Implementation References**:
- `docs/stories/7.1-academic-conversational-rag.md` — Original SHORT-TERM memory implementation
- `docs/SPRINT_CHANGE_PROPOSAL_EPIC_9.md` — Change analysis and approval documentation

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-06 | 1.0 | Epic 9 initial specification | John (PM) |
| 2025-01-17 | 1.1 | Story 9.3 requisiti modificati: sostituita UI timeline/search con session management UI (sidebar + CRUD operations). Story originale 9.3 spostata a 9.6 come enhancement opzionale. Motivazione: requisiti utente per gestione foundational sessioni prioritaria rispetto analytics/search avanzate. | Bob (SM) |

---

**Epic 9 Status**: 🚧 **IN PROGRESS** — Story 9.1-9.2 Done, Story 9.3 Ready for Development

