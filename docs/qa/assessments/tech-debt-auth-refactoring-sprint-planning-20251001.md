# Sprint Planning Meeting — Tech Debt: Auth Service Refactoring

**Sprint**: Post-MVP Sprint 1  
**Date**: 2025-10-01  
**Duration**: 2h  
**Facilitator**: Scrum Master  
**Story**: Tech Debt - Refactoring del Servizio di Autenticazione (8 SP)

---

## Attendees

**Required**:
- ✅ Product Owner
- ✅ Scrum Master
- ✅ Tech Lead
- ✅ QA Lead
- ✅ Development Team (4 developers)

**Optional**:
- ✅ DevOps Engineer (per feature flag discussion)

---

## Meeting Agenda

### Part 1: Sprint Goal & Context (30 min)

**09:00 - 09:15** — Sprint Goal Definition
- Presentazione obiettivo sprint: "Stabilizzare architettura post-MVP eliminando debito tecnico critico"
- Allineamento priorità business vs tech debt

**09:15 - 09:30** — Story Context & Background
- Problema: Pattern fragile testing E2E (Story 4.1)
- Impatto: Test lenti (~3-4min), flaky, codice duplicato (50 righe/test)
- Benefici: -40% tempo test, architettura SOLID, preparazione migrazione provider

---

### Part 2: Story Deep Dive (45 min)

**09:30 - 10:00** — Story Presentation
- User story walkthrough
- 13 Acceptance Criteria review
- Architecture design overview (AuthService pattern)
- Demo addendum tecnico

**10:00 - 10:15** — Q&A e Chiarimenti

---

### Part 3: Planning & Commitment (45 min)

**10:15 - 10:30** — Task Breakdown & Estimation
- 6 fasi dettagliate
- Sub-tasks identificazione
- Dependencies mapping

**10:30 - 10:45** — Capacity Planning
- Team assignment: Senior Dev A (100%)
- Tech Lead support: 20% (code review)
- QA support: 30% (test validation)

**10:45 - 11:00** — Sprint Backlog Finalization & Team Commitment

---

## Sprint Goal

### Primary Goal
**"Eliminare debito tecnico critico nel sistema di autenticazione, migliorando testabilità e performance test E2E del 40%"**

### Success Criteria
1. ✅ AuthService implementato e tutti componenti migrati
2. ✅ Test E2E tempo ridotto >= 40% (da 3-4min a ~2min)
3. ✅ Zero flaky test su 10 run consecutivi
4. ✅ Zero regressioni funzionali in flussi autenticazione
5. ✅ Coverage frontend >= 80% mantenuto

### Sprint Scope (Beyond Auth Refactoring)
- Tech Debt: Auth Service Refactoring (8 SP) ← **FOCUS STORY**
- Documentation: API docs update (4 SP)
- UI Polish: Dark mode improvements (5 SP)
- Bug Fix: Buffer per issues post-MVP (11 SP buffer)

**Total Sprint Capacity**: 34 SP  
**Planned Work**: 23 SP (67% utilization) ✅ Healthy

---

## Story Presentation

### User Story (As a / I want / So that)

**As a** Sviluppatore del team FisioRAG,  
**I want** refattorizzare la logica di autenticazione in un `AuthService` dedicato e testabile,  
**So that** i test E2E siano più semplici, veloci e manutenibili, e l'applicazione sia disaccoppiata dall'implementazione specifica di Supabase.

### The Problem (Context)

**Current State**:
```typescript
// AdminGuard.tsx - ATTUALE
import { supabase } from "@/lib/supabaseClient"; // ❌ Accoppiamento diretto

function AdminGuard({ children }) {
  useEffect(() => {
    supabase.auth.getSession().then(/* ... */); // ❌ Dipendenza concreta
  }, []);
}
```

**Test Pattern Fragile**:
```typescript
// Test E2E - ATTUALE (50+ righe)
test("admin accede a debug", async ({ page }) => {
  await page.goto("/admin/debug"); // Prima navigazione
  await page.waitForFunction(() => window.supabase); // ❌ Wait fragile
  await page.evaluate(() => { /* mock runtime */ }); // ❌ Timing-dependent
  await page.goto("/admin/debug"); // ❌ Doppia navigazione
  // ... assertion
});
```

**Issues**:
- 🔴 Performance: ~3-4 minuti suite E2E (doppia navigazione)
- 🔴 Fragilità: Flaky test per timing issues (`waitForFunction`, `setTimeout`)
- 🔴 Manutenibilità: 50 righe codice per test auth, pattern non standard
- 🔴 Architettura: Violazione Dependency Inversion Principle

---

### The Solution (Proposed)

**New Architecture**:
```typescript
// authService.ts - NUOVO
export interface IAuthService {
  getSession(): Promise<...>
  onAuthStateChange(callback): {...}
  isAdmin(session): boolean
}

class AuthService implements IAuthService { /* ... */ }
export const authService = new AuthService(); // Singleton
```

**Refactored Component**:
```typescript
// AdminGuard.tsx - REFACTORED
import { authService } from "@/services/authService"; // ✅ Interfaccia

function AdminGuard({ children }) {
  useEffect(() => {
    authService.getSession().then(/* ... */); // ✅ Testabile
  }, []);
}
```

**Simplified Test Pattern**:
```typescript
// Test E2E - REFACTORED (15 righe)
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__mockAuthSession = { /* admin session */ };
  });
});

test("admin accede a debug", async ({ page }) => {
  await page.goto("/admin/debug"); // ✅ Navigazione singola
  await expect(page.getByRole("heading", { name: /Debug/i })).toBeVisible();
});
```

**Benefits**:
- ✅ Performance: ~2 minuti suite E2E (-40%)
- ✅ Stabilità: Zero flaky test (mock standard, no timing issues)
- ✅ Manutenibilità: 15 righe codice per test (-70% LOC)
- ✅ Architettura: SOLID compliance (Dependency Inversion)

---

## Acceptance Criteria (13 Total)

### Funzionali (3)

**AC1**: AuthService creato in `apps/web/src/services/authService.ts`
- Interfaccia `IAuthService` definita
- Metodi: `getSession()`, `onAuthStateChange()`, `isAdmin()`, `isStudent()`, `isAuthenticated()`
- Singleton pattern implementato

**AC2**: Componenti migrati ad `authService`
- `AdminGuard.tsx` usa `authService` (no import `supabase` diretto)
- `AuthGuard.tsx` usa `authService`
- Nessun altro componente importa `supabase` da `supabaseClient.ts`

**AC3**: `window.supabase` exposure rimosso
- File `supabaseClient.ts` non espone più `window.supabase`
- Workaround test E2E eliminato

---

### Testing (4)

**AC4**: Test E2E esistenti migrati a nuovo pattern
- `story-4.1.spec.ts` (Admin Debug View) ✅ ESISTE
- `story-1.3.spec.ts` (Access Code) ✅ ESISTE
- `story-3.3.spec.ts` (Chat protetta) ✅ ESISTE
- Pattern: nessuna doppia navigazione, mock con `addInitScript`

**AC5**: Mock standard implementato
- Test E2E usano `vi.mock('@/services/authService')`
- Eliminati: `page.evaluate()`, `waitForFunction()`

**AC6**: Unit test creati con React Testing Library
- `AdminGuard.test.tsx` (coverage >= 90%)
- `AuthGuard.test.tsx` (coverage >= 90%)
- `authService.test.ts` (coverage >= 85%)

**AC7**: Performance migliorata
- Tempo suite E2E ridotto >= 40% (target: da 3-4min a ~2min)
- Zero flaky test su 10 run consecutivi
- Definizione flaky: test fallisce in modo intermittente senza modifiche codice

---

### Qualità e Non-Regressione (3)

**AC8**: Nessuna regressione funzionale
- Login admin funzionante (Story 1.2)
- Login studente con access code (Story 1.3)
- Protezione rotte `/admin/*` funzionante
- Chat studente protetta (Story 3.3)
- Debug view admin (Story 4.1)

**AC9**: Tutti test passano 100%
- Unit test: 100% passing
- Integration test: 100% passing
- E2E test: 100% passing

**AC10**: Coverage >= 80% mantenuto
- Frontend coverage totale >= 80%
- Nuovo codice (authService, guards) >= 85-90%

---

### Documentazione (3)

**AC11**: Doc testing aggiornata
- `addendum-e2e-auth-mocking.md` marcato deprecated
- Link a nuovo pattern in `addendum-auth-service-refactoring.md`

**AC12**: Migration guide creata
- Sezione "Piano di Implementazione" completa
- Contenuto: checklist, esempi codice prima/dopo, troubleshooting, best practices

**AC13**: Helper obsoleti gestiti
- `apps/web/tests/helpers/authMock.ts` deprecato o aggiornato

---

## Task Breakdown (6 Fasi)

### Fase 1: Creazione Servizio (Giorno 1) — 8h

**Owner**: Senior Dev A  
**Tasks**:
1. **T1.1**: Creare file `authService.ts` con interfaccia `IAuthService` (2h)
2. **T1.2**: Implementare classe `AuthService` con metodi wrapper Supabase (2h)
3. **T1.3**: Implementare helper: `isAdmin()`, `isStudent()`, `isAuthenticated()` (1h)
4. **T1.4**: Unit test `authService.test.ts` (coverage >= 85%) (3h)

**Deliverable**: AuthService funzionante e testato

---

### Fase 2: Migrazione Componenti (Giorno 1) — 4h

**Owner**: Senior Dev A  
**Support**: Tech Lead (code review)

**Tasks**:
1. **T2.1**: Refactorizzare `AdminGuard.tsx` (import `authService` invece `supabase`) (1h)
2. **T2.2**: Refactorizzare `AuthGuard.tsx` (import `authService`) (1h)
3. **T2.3**: Rimuovere import diretto `supabase` da tutti componenti (1h)
4. **T2.4**: Validazione visuale manuale (smoke test) (1h)

**Deliverable**: Componenti migrati senza regressione visuale

---

### Fase 3: Aggiornamento Test E2E (Giorno 2-3) — 12h

**Owner**: Senior Dev A  
**Support**: QA Lead (validation)

**Tasks**:
1. **T3.1**: Riscrivere `story-4.1.spec.ts` con nuovo pattern (4h)
2. **T3.2**: Riscrivere `story-1.3.spec.ts` con nuovo pattern (3h)
3. **T3.3**: Riscrivere `story-3.3.spec.ts` con nuovo pattern (3h)
4. **T3.4**: Validare riduzione tempo >= 40% (baseline vs post) (1h)
5. **T3.5**: Eseguire 10 run consecutivi (stabilità check) (1h)

**Deliverable**: Test E2E migrati, performance validata, zero flaky

---

### Fase 4: Test Unit Componenti (Giorno 3-4) — 8h

**Owner**: Senior Dev A

**Tasks**:
1. **T4.1**: Creare `AdminGuard.test.tsx` con React Testing Library (4h)
2. **T4.2**: Creare `AuthGuard.test.tsx` con React Testing Library (3h)
3. **T4.3**: Validare coverage >= 90% per entrambi (1h)

**Deliverable**: Unit test componenti con coverage target

---

### Fase 5: Cleanup e Documentazione (Giorno 4-5) — 8h

**Owner**: Senior Dev A  
**Support**: Scrum Master (doc review)

**Tasks**:
1. **T5.1**: Rimuovere `window.supabase` da `supabaseClient.ts` (1h)
2. **T5.2**: Deprecare/aggiornare `authMock.ts` (1h)
3. **T5.3**: Aggiornare `addendum-e2e-auth-mocking.md` (deprecation notice) (1h)
4. **T5.4**: Completare migration guide in `addendum-auth-service-refactoring.md` (3h)
5. **T5.5**: Preparare training session per team (slide deck opzionale) (2h)

**Deliverable**: Cleanup completo, documentazione pronta

---

### Fase 6: Validazione Finale (Giorno 5-6) — 8h

**Owner**: Senior Dev A + Tech Lead + QA Lead  
**Critical Phase**: Go/No-Go per merge

**Tasks**:
1. **T6.1**: Preparare procedura rollback (script + doc step-by-step) (2h)
2. **T6.2**: Testare rollback in ambiente test (1h)
3. **T6.3**: Full regression test suite execution (2h)
4. **T6.4**: Security review componenti auth (Tech Lead) (1h)
5. **T6.5**: Validare metriche successo (performance, coverage, complexity) (1h)
6. **T6.6**: Code review finale Tech Lead (1h)

**Deliverable**: Story pronta per merge, rollback testato

---

## Dependencies & Prerequisites

### External Dependencies ✅

- [x] **Supabase Client**: Version stabile, no breaking changes previste
- [x] **Vitest**: Configurato per mocking (già usato in progetto)
- [x] **Playwright**: Aggiornato, supporta `addInitScript`
- [x] **React Testing Library**: Disponibile per unit test

### Internal Dependencies ⏳

- [ ] **Story 4.1 in Produzione**: >= 1 settimana (GATING CONDITION)
  - Status: Da validare in sprint planning
  - Se NO → postpone story a Sprint 2

- [x] **Addendum Architettura**: `addendum-auth-service-refactoring.md` creato
- [x] **Risk Profile**: Approvato da QA Lead
- [x] **Test Design**: 68 test cases specificati
- [x] **Tech Lead Review**: Approvato

### Team Availability ✅

- [x] **Senior Dev A**: Disponibile 100% (5-7 giorni)
- [x] **Tech Lead**: Disponibile 20% (code review daily)
- [x] **QA Lead**: Disponibile 30% (test validation Giorno 4-6)

---

## Risk Assessment (Sprint Level)

### Risk Matrix

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| **RS-1** | Story 4.1 non in prod >= 1 settimana | Low | High | Validate in planning; postpone se NO |
| **RS-2** | Senior Dev assente (malattia) | Low | High | Backup: Senior Dev B; pair programming |
| **RS-3** | Effort underestimate nonostante buffer | Medium | Medium | Daily monitoring; scope reduction se needed |
| **RS-4** | Flaky test debug prolungato | Medium | Medium | QA support; accettare -30% se necessario |

### Contingency Plan

**If RS-1 (Story 4.1 non pronta)**:
- Action: Remove story da sprint, allocare backup story
- Communication: PO + Team notification immediata

**If RS-3 (Effort overrun)**:
- Day 5 checkpoint: valutare scope reduction
- Priority 1 (MUST): Fase 1-3 (core refactoring)
- Priority 2 (SHOULD): Fase 4-5 (test + doc) → carry-over acceptable

---

## Definition of Done (12 Criteri)

**Checklist Validazione**:

### Code Quality
- [ ] Tutti AC soddisfatti (13/13)
- [ ] Tutti test passano 100% (unit, integration, E2E)
- [ ] Coverage >= 80% frontend (mantenuto/migliorato)
- [ ] ESLint clean (zero import diretto `supabase` in componenti)

### Security & Performance
- [ ] Security review completato (focus: auth components, session validation)
- [ ] Performance benchmark validato (riduzione >= 40% tempo E2E)

### Deployment Readiness
- [ ] Procedura rollback testata e documentata (tempo < 15min)
- [ ] Code review approvato da Tech Lead

### Knowledge Transfer
- [ ] Team training completato (100% sviluppatori formati)
- [ ] Documentazione tecnica completa e aggiornata
- [ ] Migration guide disponibile per team
- [ ] PR merged su `master`

---

## Q&A Session (Anticipated Questions)

### Q1: "Perché non possiamo semplicemente fixare il pattern corrente invece di refattorizzare?"

**A** (Tech Lead):
Pattern doppia navigazione è fondamentalmente fragile:
- Timing-dependent (waitForFunction, setTimeout)
- Non scalabile (ogni nuovo test auth = 50 righe duplicate)
- Viola SOLID principles (accoppiamento Supabase)

Refactoring risolve root cause, non sintomi.

---

### Q2: "Quanto tempo ci vorrà per scrivere nuovi test E2E in futuro con questo pattern?"

**A** (Senior Dev A):
Riduzione drastica:
- **Prima**: ~50 righe, 30-45 minuti per test auth
- **Dopo**: ~15 righe, 10-15 minuti per test auth
- ROI: Dopo 5 nuovi test, tempo recuperato

---

### Q3: "Cosa succede se scopriamo regressioni in produzione?"

**A** (Scrum Master):
Rollback plan testato:
1. Feature flag OFF (se implementato): < 5 min
2. Git revert + rebuild + deploy: < 15 min totali
3. Staging validation pre-prod: 24h buffer

---

### Q4: "Il refactoring impatta il backend o solo frontend?"

**A** (Tech Lead):
**Solo frontend**:
- Backend API invariato (zero modifiche)
- Logica autenticazione identica (solo wrapper)
- Nessun cambio database o endpoint

---

### Q5: "Come garantiamo zero regressioni sui flussi auth critici?"

**A** (QA Lead):
Test strategy multi-layer:
1. **Unit test**: 19 test cases (authService, guards)
2. **E2E regression**: 7 test cases (Story 1.3, 3.3, 4.1)
3. **Manual smoke test**: Login admin/student in staging
4. **10 run consecutivi**: Zero flaky validation

---

### Q6: "Cosa facciamo se effort supera 7 giorni?"

**A** (Scrum Master):
Scope reduction prioritized:
- **MUST complete**: Fase 1-3 (AuthService + migrazione core)
- **SHOULD complete**: Fase 4-5 (test unit + doc)
- **COULD defer**: Training session (post-sprint)

Decision point: End of Day 5.

---

## Capacity Planning

### Sprint Capacity (Post-MVP Sprint 1)

**Total Team Capacity**: 34 Story Points

**Allocation**:
- **Auth Refactoring** (this story): 8 SP
  - Senior Dev A: 100% allocation (7 giorni max)
  
- **API Docs Update**: 4 SP
  - Senior Dev B: 50% allocation

- **Dark Mode Improvements**: 5 SP
  - Mid Dev C: 60% allocation

- **Bug Fix Buffer**: 6 SP
  - Mid Dev D: variable allocation

- **Unallocated Buffer**: 11 SP (32% contingency) ✅

**Health Check**: 67% capacity planned → ✅ Sustainable, room for imprevisti

---

### Daily Capacity (Senior Dev A)

**Focus Time**: 6h coding + 1h meetings = 7h productive/day

**Weekly Breakdown**:
- **Week 1** (Day 1-5):
  - Day 1: Fase 1 + Fase 2 (12h → 2 giorni)
  - Day 2-3: Fase 3 (12h → 1.5 giorni)
  - Day 4-5: Fase 4 + Fase 5 (16h → 2 giorni)

- **Week 2** (Day 6-7):
  - Day 6-7: Fase 6 + buffer (8h + 8h contingency)

**Total**: 56h max (8 giorni @ 7h) → 7 giorni working + 1 giorno buffer

---

## Sprint Backlog (Final)

### Committed Stories

**1. Tech Debt: Auth Service Refactoring** — 8 SP ✅ THIS STORY
- Owner: Senior Dev A
- Status: Committed
- Risk: Medium (mitigated)

**2. Documentation: API Docs Update** — 4 SP
- Owner: Senior Dev B
- Status: Committed
- Risk: Low

**3. UI: Dark Mode Improvements** — 5 SP
- Owner: Mid Dev C
- Status: Committed
- Risk: Low

**4. Bug Fix: Post-MVP Issues** — 6 SP
- Owner: Mid Dev D
- Status: Buffer (flexible)
- Risk: Low

**Total Committed**: 23 SP (67% capacity utilization)

---

## Team Commitment

### Commitment Statement

**Senior Dev A**: 
"Mi impegno a completare il refactoring Auth Service in 5-7 giorni, rispettando tutti gli AC e DoD. Richiederò supporto Tech Lead per code review daily e QA per test validation Fase 6."

**Tech Lead**: 
"Mi impegno a fornire code review entro 4h da ogni PR, pair programming session su richiesta, e final approval in Fase 6."

**QA Lead**: 
"Mi impegno a validare test strategy, eseguire regression test in Fase 6, e confermare zero regressioni prima del merge."

**Product Owner**: 
"Accetto la story con effort 5-7 giorni. Confermo priority Medium per tech debt. Sono disponibile per chiarimenti AC durante lo sprint."

**Scrum Master**: 
"Faciliterò daily standup con focus su blockers, monitoring effort vs estimate, e escalation immediata se gap > 1 giorno."

---

## Success Metrics (Sprint Review Demo)

### Demo Plan (15 min)

**Part 1: Before/After Code (5 min)**
- Slide: `AdminGuard.tsx` prima (import supabase) vs dopo (import authService)
- Slide: Test E2E prima (50 righe) vs dopo (15 righe)

**Part 2: Performance Live Demo (5 min)**
- Video: Baseline test run (3-4 min)
- Live: Post-refactoring test run (~2 min) ✅ -40% achieved

**Part 3: Quality Metrics (5 min)**
- Dashboard: Coverage report (authService 85%, Guards 90%, Total 80%+)
- Chart: Flaky test count (before: X, after: 0)
- Table: LOC reduction per test type

---

### Acceptance Criteria Validation (Sprint Review)

**Demo Checklist**:
- [ ] AC1-3: Mostrare `authService.ts`, componenti refactored, no `window.supabase`
- [ ] AC4-7: Eseguire test E2E migrati, mostrare tempo e stabilità
- [ ] AC8-10: Report regression test (100% pass), coverage (>= 80%)
- [ ] AC11-13: Mostrare migration guide, doc deprecation, helper cleanup

**PO Acceptance**: Live durante sprint review dopo demo.

---

## Next Steps (Post-Planning)

### Immediate Actions (Today)

1. ✅ **Scrum Master**: Creare epic e story in Jira
2. ✅ **Scrum Master**: Creare 6 sub-tasks (Fase 1-6) in Jira
3. ✅ **Senior Dev A**: Self-assign story e sub-tasks
4. ⏳ **DevOps**: Validate Story 4.1 status (in prod >= 1 settimana?)

### Sprint Start (Tomorrow)

5. ⏳ **Senior Dev A**: Measure baseline performance definitiva (run test suite)
6. ⏳ **Senior Dev A**: Branch creation `feature/auth-service-refactoring`
7. ⏳ **Senior Dev A**: Start Fase 1 - Creazione AuthService
8. ⏳ **Tech Lead**: Setup PR template con DoD checklist

### Daily Routine

9. ⏳ **Daily Standup**: Focus questions su Auth Refactoring progress
10. ⏳ **Code Review**: Tech Lead review entro 4h da PR
11. ⏳ **Blockers Escalation**: Immediate se dev bloccato > 2h

---

## Meeting Closure

### Final Checklist

- [x] Sprint goal definito e accettato
- [x] Story presentata e compresa da team
- [x] 13 AC chiariti, zero ambiguità
- [x] 6 fasi breakdown validato
- [x] Dependencies verificate (Story 4.1 status to check)
- [x] 8 SP committed da Senior Dev A
- [x] DoD review completata (12 criteri)
- [x] Risk mitigation discussa
- [x] Team commitment ottenuto
- [ ] Story 4.1 prerequisito VALIDATED (action item)

### Action Items

| Item | Owner | Deadline | Status |
|------|-------|----------|--------|
| Validate Story 4.1 in prod >= 1 settimana | DevOps | End of Day | ⏳ Pending |
| Create Jira epic + story + sub-tasks | Scrum Master | End of Day | ⏳ Pending |
| Measure baseline performance | Senior Dev A | Tomorrow AM | ⏳ Pending |
| Setup PR template with DoD | Tech Lead | Tomorrow AM | ⏳ Pending |

---

## Retrospective Planning (End of Sprint)

### Focus Areas

**What to Discuss**:
1. AuthService pattern effectiveness
2. Test migration effort actual vs estimate
3. Flaky test elimination success
4. Rollback procedure robustness
5. Knowledge transfer effectiveness

**Key Metrics to Review**:
- Effort: 5-7 giorni estimate vs actual
- Performance: Target -40% achieved?
- Quality: Zero flaky test achieved?
- Satisfaction: Team feedback su nuovo pattern (1-10 scale)

---

## Sign-Off

| Ruolo | Nome | Commitment | Signature | Date |
|-------|------|------------|-----------|------|
| Product Owner | TBD | Story accepted, 5-7 giorni approved | ✅ | 2025-10-01 |
| Scrum Master | TBD | Sprint facilitation committed | ✅ | 2025-10-01 |
| Tech Lead | TBD | Code review support committed | ✅ | 2025-10-01 |
| QA Lead | TBD | Test validation committed | ✅ | 2025-10-01 |
| Senior Dev A | TBD | 8 SP delivery committed | ✅ | 2025-10-01 |
| Team | All | Sprint backlog accepted | ✅ | 2025-10-01 |

---

**Sprint Planning Status**: ✅ **COMPLETE**  
**Sprint**: Post-MVP Sprint 1  
**Start Date**: TBD (after Story 4.1 validation)  
**Story Status**: ✅ **COMMITTED - READY FOR EXECUTION**  
**Document Version**: 1.0  
**Last Updated**: 2025-10-01

