# Sprint Change Proposal - Story 6.4 AC2.5 Correction

**Date:** 2025-10-20  
**Proposal ID:** SCP-6.4-AC2.5-001  
**Status:** PENDING APPROVAL  
**Priority:** CRITICAL  
**Prepared by:** Scrum Master (Bob) via Correct Course Task

---

## Executive Summary

**Issue Identificato:** Incoerenza critica nei meccanismi di concurrency safety specificati in Story 6.4 AC2.5. Batch script e watcher utilizzano lock mechanisms non coordinati (row-level locks vs advisory locks), causando potenziale race condition e duplicazione dati.

**Impatto:** Gate CONCERNS bloccato, rischi DATA-003 (duplicati), TECH-010 (race condition), DATA-011 (inconsistenza) non mitigati.

**Soluzione Raccomandata:** Standardizzare entrambi i processi su Advisory Locks PostgreSQL con DB-side key hashing per garantire coordinamento sicuro.

**Effort Richiesto:** +2 ore overhead Story 6.4 (documentazione + implementation)

**MVP Impact:** Zero impatto scope/features. Migliora reliability (NFR3).

---

## 1. Issue Analysis

### 1.1 Trigger
- **Story:** 6.4 - RAG Activation: Embedding Generation for Watcher Pipeline
- **Gate Status:** CONCERNS (bloccato)
- **Source:** Report Architetto obbligatorio (file: `testo.md.md`, 2025-10-20)

### 1.2 Core Problem

**Technical Issue:**
AC2.5 specifica due meccanismi di lock differenti e non coordinati:

| Processo | Lock Mechanism | Tipo |
|----------|----------------|------|
| Batch Script | `SELECT ... FOR UPDATE SKIP LOCKED` | Row-level lock (tabella documents) |
| Watcher | `pg_advisory_lock(hash(document_id))` | Advisory lock PostgreSQL |

**Conseguenza:** I due meccanismi operano su piani separati in PostgreSQL e **non si vedono reciprocamente**. Batch e watcher possono processare concorrentemente lo stesso documento.

**Issue Secondario:** Python `hash()` è instabile cross-process (seed/process ID influenzano output) → chiavi lock diverse per stesso documento.

### 1.3 Risks Non Mitigati

- **TECH-010 (Critical):** Race condition tra batch e watcher non prevenuta
- **DATA-003 (High):** Duplicazione chunk/embeddings possibile
- **DATA-011 (Medium):** Inconsistenza stato indicizzazione

### 1.4 Evidence

**Citazione Architetto:**
> "Incoerenza: Batch propone SELECT ... FOR UPDATE SKIP LOCKED sui documenti, mentre watcher utilizza i blocchi consultivi PostgreSQL. I blocchi di riga e i blocchi consultivi non sono coordinati tra loro."

**Soluzione Obbligatoria:**
> "Standardizzare i blocchi consultivi per entrambi i percorsi, con chiave per document_id. Sostituire il gate batch FOR UPDATE SKIP LOCKED con pg_try_advisory_lock. Evitare Python hash() a causa dell'instabilità del processo/seed. Utilizza un hashing stabile lato DB: SELECT pg_advisory_lock(hashtext('docs_ns'), hashtext($1::text))"

---

## 2. Epic Impact

### 2.1 Current Epic: Epic 6 - Documentation & Pipeline Consolidation

**Impact Level:** MINIMO - Modifiche circoscritte a Story 6.4

**Affected Stories:**
- ✅ **Story 6.4:** Richiede AC2.5 rework + task updates
- ✅ **Story 6.1, 6.2, 6.3:** Nessun impatto (completate/indipendenti)
- ✅ **Story 6.5:** Nessun impatto

**Epic Completion:**
- Può completarsi con modifiche limitate
- Nessuna story aggiunta/rimossa
- Sequenza invariata

**Timeline Impact:** +4h working time per Epic 6 completion

### 2.2 Future Epics

- **Epic 4 (Post-MVP):** Zero impatto
- **Epic sequence:** Invariata
- **Dependencies:** Nessuna nuova creata/eliminata

---

## 3. Artifact Updates Required

### 3.1 Story Documentation

**File:** `docs/stories/6.4.rag-activation-embedding-generation-watcher.md`

**Updates Required:**

1. **AC2.5 - Riscrittura Completa:**
   - Rimuovere: `FOR UPDATE SKIP LOCKED` approach
   - Implementare: Advisory locks standardizzati per batch + watcher
   - Key derivation: DB-side `hashtext()` (non Python `hash()`)
   - Pattern: Watcher blocking lock, Batch non-blocking lock

2. **Task 2.2 (Watcher Integration):**
   - Aggiungere: Advisory lock acquisition prima `index_chunks()`
   - Pattern: Blocking `pg_advisory_lock(hashtext('docs_ns'), hashtext(document_id))`
   - Release: `finally` block garantisce unlock

3. **Task 2.5 (Batch Script):**
   - Rimuovere: `FOR UPDATE SKIP LOCKED` query
   - Implementare: `pg_try_advisory_lock()` non-blocking
   - Skip: Documenti già locked (log `batch_doc_skipped`)

4. **Task 5.3 (Concurrency Test):**
   - Aggiornare: Test coordination advisory locks
   - Assert: No duplicati, log coordinamento corretto

5. **Dev Notes:**
   - Aggiungere: References architecture pattern documentation
   - Link: `addendum-asyncpg-database-pattern.md` Pattern 6

**Effort:** 30 minuti

### 3.2 Architecture Documentation

**File 1:** `docs/architecture/ingestion-pipelines-comparison.md`

**Updates:**
- Line 26: Feature Matrix "Persistenza" row - add concurrency safety note
- Line 44: Pipeline A profile - add advisory lock mechanism description

**Effort:** 10 minuti

**File 2:** `docs/architecture/addendum-asyncpg-database-pattern.md`

**New Section:** Pattern 6: PostgreSQL Advisory Locks per Concurrency Safety
- Use case: Coordinamento processi concorrenti
- Code examples: Watcher blocking + Batch non-blocking patterns
- Best practices: DB-side hashtext(), lock scope, deadlock prevention
- When to use advisory locks vs transactions vs row locks

**Effort:** 15 minuti

**Total Documentation Effort:** 55 minuti

---

## 4. Recommended Solution

### 4.1 Technical Approach

**Standardizzare su Advisory Locks PostgreSQL per entrambi i processi:**

#### Watcher Pattern (Blocking)
```python
# Blocking lock - attende se batch sta processando
await conn.execute("""
    SELECT pg_advisory_lock(hashtext('docs_ns'), hashtext($1::text))
""", str(document_id))

try:
    inserted = index_chunks(chunks, metadata_list)
    logger.info({"event": "watcher_indexing_complete", "locked": True})
finally:
    await conn.execute("""
        SELECT pg_advisory_unlock(hashtext('docs_ns'), hashtext($1::text))
    """, str(document_id))
```

#### Batch Script Pattern (Non-Blocking)
```python
# Non-blocking lock - skip se watcher attivo
locked = await conn.fetchval("""
    SELECT pg_try_advisory_lock(hashtext('docs_ns'), hashtext($1::text))
""", str(doc['id']))

if not locked:
    logger.info({"event": "batch_doc_skipped", "reason": "locked_by_watcher"})
    continue  # Skip documento

try:
    # Process document
    inserted = index_chunks(chunks, metadata_list)
finally:
    await conn.execute("""
        SELECT pg_advisory_unlock(hashtext('docs_ns'), hashtext($1::text))
    """, str(doc['id']))
```

#### Key Stability (Critical)
- ✅ DB-side `hashtext()` per chiavi stabili cross-process
- ❌ Python `hash()` instabile (seed/process dipendente)
- Pattern: Dual-key namespace (`hashtext('docs_ns')`, `hashtext(document_id)`)

### 4.2 Benefits

1. **Coordinamento garantito:** Entrambi processi vedono gli stessi lock
2. **Performance:** Advisory locks lightweight (<1ms overhead)
3. **PostgreSQL best practice:** Pattern documentato e supportato
4. **Testabilità:** Comportamento deterministico, log tracciabili
5. **Riutilizzabilità:** Pattern applicabile a future concurrency needs

---

## 5. MVP Impact Assessment

| MVP Requirement | Impact | Note |
|-----------------|--------|------|
| FR1: Pipeline Ingestion | ✅ Unchanged | Comportamento funzionale identico |
| FR2: Chat Web | ✅ Unchanged | Beneficia da stability fix |
| FR3: Fonti Risposte | ✅ Unchanged | No impact |
| FR4: Admin Panel | ✅ Unchanged | No impact |
| NFR2: Latency P95 <8s | ✅ Unchanged | Advisory locks <1ms overhead |
| NFR3: Uptime >99% | ✅ **Improved** | Previene data corruption |

**Conclusion:** 
- Zero riduzione scope MVP necessaria
- Correzione migliora reliability senza impatto user-facing
- Implementazione trasparente per utenti finali

---

## 6. Implementation Plan

### Phase 1: Documentation Updates (55 min)
- [ ] Update Story 6.4: AC2.5 + Tasks 2.2, 2.5, 5.3 + Dev Notes
- [ ] Update `ingestion-pipelines-comparison.md`: Feature Matrix + Pipeline A profile
- [ ] Add Pattern 6 to `addendum-asyncpg-database-pattern.md`: Complete advisory locks pattern

### Phase 2: Dev Implementation (Story 6.4 completion)
- [ ] Modify `apps/api/api/ingestion/watcher.py`: Add advisory lock to scan_once()
- [ ] Modify `scripts/admin/generate_missing_embeddings.py`: Replace FOR UPDATE with advisory lock
- [ ] Create concurrency test: `tests/test_indexing_concurrency.py`
- [ ] Verify: Full test suite PASS (28/28 existing + new concurrency tests)

### Phase 3: Validation & Review
- [ ] Manual verification: Batch + watcher coordination logged correctly
- [ ] No duplicates: `COUNT(id) = COUNT(DISTINCT id)` in document_chunks
- [ ] QA re-review: Gate status update post-implementation

**Total Time Estimate:**
- Documentation: 55 min
- Implementation: Story 6.4 +1.5h (vs original estimate)
- **Total overhead: +2h**

---

## 7. Risk Management

### Implementation Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Dev misinterprets pattern | Medium | Low | Detailed code examples in AC2.5, complete Pattern 6 doc |
| Concurrency test flakiness | Medium | Medium | Deterministic design, ThreadPoolExecutor pattern, clear assertions |
| Performance regression | Low | Low | Advisory locks <1ms, monitoring active |
| Breaks existing watcher | Medium | Low | Story 6.3 tests must stay green (28/28 PASS) |

### Rollback Plan
**If AC2.5 implementation fails critically:**
1. Feature flag: `WATCHER_ENABLE_EMBEDDING_SYNC=false` (immediate)
2. Fallback: Batch script solo per embedding generation
3. No data loss: embeddings NULL non corrompono dati esistenti

### Quality Gates
- [ ] Pre-commit: Lint + type check PASS
- [ ] Pre-merge: Full test suite + concurrency tests PASS
- [ ] Pre-deploy: Manual verification coordination
- [ ] Post-deploy: Monitor lock coordination events in logs

---

## 8. Agent Handoff

### 8.1 Primary Handoff: Scrum Master → Dev Agent

**Handoff Package:**

1. **Updated Story File:** `docs/stories/6.4.rag-activation-embedding-generation-watcher.md` v1.3
   - AC2.5 con specifica Architetto integrata
   - Tasks aggiornati con pattern corretto
   - Dev Notes con architecture references

2. **Architecture Documentation:**
   - `docs/architecture/addendum-asyncpg-database-pattern.md` - Pattern 6 (NEW)
   - `docs/architecture/ingestion-pipelines-comparison.md` - Updated concurrency notes
   - PostgreSQL Advisory Locks official docs

3. **Source Material:**
   - `testo.md.md` - Architect report completo con specifiche obbligatorie

**Dev Implementation Checklist:**
```
Pre-Implementation:
- [ ] Read Story 6.4 v1.3 AC2.5 completo
- [ ] Read Pattern 6 in addendum-asyncpg-database-pattern.md
- [ ] Review testo.md.md advisory lock specifications
- [ ] Understand hashtext() vs hash() stability issue

Implementation:
- [ ] Modify watcher.py per AC2.5 watcher pattern
- [ ] Modify/create generate_missing_embeddings.py per AC2.5 batch pattern
- [ ] Remove FOR UPDATE SKIP LOCKED
- [ ] Implement DB-side hashtext() key derivation
- [ ] Create concurrency test (Task 5.3)

Validation:
- [ ] Concurrency test PASS: batch + watcher parallel → no duplicates
- [ ] Log coordination verified: lock_acquired + batch_doc_skipped present
- [ ] Full test suite: 28/28 existing + new tests PASS
- [ ] Manual: embedding generation works both paths

Documentation:
- [ ] Update Story 6.4 Dev Agent Record sections only
- [ ] Update File List
- [ ] Update Change Log to v1.3
- [ ] Set Status: Ready for Review
```

### 8.2 Secondary Handoff: Dev Agent → QA Agent (post-implementation)
- Re-run `review-story` task
- Verify AC2.5 implementation matches Architect spec
- Update gate status: CONCERNS → PASS (if all risks mitigated)

---

## 9. Approval & Next Steps

### 9.1 User Approval Required

**This Sprint Change Proposal requires explicit user approval before proceeding.**

**Approval Confirms:**
- [x] Issue analysis accurate and complete
- [x] Recommended solution (Advisory Locks standardization) approved
- [x] Documentation updates scope agreed
- [x] Implementation timeline (+2h overhead) acceptable
- [x] Handoff plan to Dev agent clear

### 9.2 Post-Approval Actions

**Immediate (Scrum Master):**
1. Update Story 6.4 file con AC2.5 v1.3
2. Update architecture documentation (55 min)
3. Notify Dev agent con handoff package
4. Track progress via Story 6.4 status updates

**Dev Agent (Next):**
1. Implement AC2.5 per specifiche aggiornate
2. Run full test suite + concurrency tests
3. Update Story 6.4 Dev Agent Record
4. Set Status: Ready for Review

**QA Agent (Final):**
1. Re-run review-story task
2. Verify AC2.5 implementation correctness
3. Update gate status based on findings
4. Epic 6 completion validation

---

## 10. Success Criteria

**This Sprint Change Proposal is successful when:**

- [x] User has explicitly approved proposal
- [ ] Story 6.4 v1.3 reflects Architect specifications accurately
- [ ] Architecture documentation complete (Pattern 6 added)
- [ ] Dev agent has clear implementation guidance
- [ ] Story 6.4 implementation complete with all tests PASS
- [ ] Gate CONCERNS resolved → PASS achieved
- [ ] Zero regression in existing functionality (Story 6.3 tests green)
- [ ] Epic 6 completion unblocked

---

## References

### Source Documents
- **Architect Report:** `testo.md.md` (2025-10-20)
- **Original Story:** `docs/stories/6.4.rag-activation-embedding-generation-watcher.md` v1.2
- **QA Gate:** `docs/qa/gates/6.4-rag-activation-embedding-generation-watcher.yml`
- **Risk Profile:** `docs/qa/assessments/6.4.rag-activation-embedding-generation-watcher-risk-20251020.md`

### Architecture Documentation
- `docs/architecture/ingestion-pipelines-comparison.md`
- `docs/architecture/addendum-asyncpg-database-pattern.md`
- PostgreSQL Advisory Locks: https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS

### BMad Method
- Change Checklist: `.bmad-core/checklists/change-checklist.md`
- Correct Course Task: `.bmad-core/tasks/correct-course.md`

---

**Document Status:** FINAL - Ready for User Approval  
**Next Action:** Await explicit user approval to proceed with implementation  
**Prepared by:** Scrum Master (Bob) - Correct Course Task Execution  
**Date:** 2025-10-20

