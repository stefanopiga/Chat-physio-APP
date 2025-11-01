# Next Actions — Tech Debt: Auth Service Refactoring

**Date**: 2025-10-01  
**Current Status**: Sprint Planning Complete ✅  
**Story Status**: Committed, Ready for Execution ⏳  

---

## 🎯 Current Situation

### Completed ✅
- [x] Story v1.1 approvata (tutti blocker risolti)
- [x] Risk profile completato (11 rischi, score 128)
- [x] Test design definito (68 test cases)
- [x] PO validation passed
- [x] Tech Lead review approved
- [x] Sprint allocation Post-MVP Sprint 1
- [x] Sprint Planning completato (8 SP committed)

### Pending ⏳
- [ ] **CRITICAL**: Validare prerequisito Story 4.1 in produzione >= 1 settimana
- [ ] Setup tecnico (Jira, branch, baseline)
- [ ] Inizio sviluppo Fase 1

---

## 🚨 IMMEDIATE ACTION REQUIRED

### Action #1: Validate Prerequisito Story 4.1 (BLOCKER)

**Owner**: DevOps / Tech Lead  
**Deadline**: Fine giornata (oggi)  
**Priority**: 🔴 CRITICAL BLOCKER

**Task**:
```bash
# Verificare stato Story 4.1 in produzione
# Domande da rispondere:
1. Story 4.1 è deployata in produzione? (SI/NO)
2. Se SI, da quanto tempo? (>= 7 giorni richiesti)
3. Ci sono stati issue/rollback? (stabilità validata?)
4. Pattern doppia navigazione causa flaky test in prod? (SI/NO)
```

**Decision Tree**:

**IF Story 4.1 in prod >= 1 settimana**:
→ ✅ Prerequisito SODDISFATTO
→ Procedi con Action #2 (Setup Tecnico)

**IF Story 4.1 in prod < 1 settimana**:
→ ⚠️ ATTENDERE fino a 1 settimana completata
→ Comunicare delay a team
→ Allocare story backup temporanea

**IF Story 4.1 NON in produzione**:
→ 🚨 POSTPONE story a Sprint 2
→ Rimuovere da sprint corrente
→ Allocare story alternativa (es. "UI Component Library Upgrade")

---

## 📋 Action #2: Setup Tecnico (IF prerequisito OK)

### Task 2.1: Jira Setup
**Owner**: Scrum Master  
**Deadline**: Oggi  
**Effort**: 30 minuti

**Checklist**:
- [ ] Creare Epic in Jira: "Tech Debt / Post-MVP Enhancements"
- [ ] Creare Story: "Tech Debt - Auth Service Refactoring" (8 SP)
- [ ] Creare 6 Sub-tasks (Fase 1-6):
  ```
  TASK-001: Fase 1 - Creazione AuthService (8h)
  TASK-002: Fase 2 - Migrazione Componenti (4h)
  TASK-003: Fase 3 - Test E2E Migration (12h)
  TASK-004: Fase 4 - Unit Test Componenti (8h)
  TASK-005: Fase 5 - Cleanup & Doc (8h)
  TASK-006: Fase 6 - Validazione Finale (8h)
  ```
- [ ] Collegare story a documenti:
  - Link: `docs/stories/tech-debt-auth-service-refactoring.md`
  - Link: `docs/architecture/addendum-auth-service-refactoring.md`
  - Link: `docs/qa/assessments/tech-debt-auth-refactoring-risk-20251001.md`
- [ ] Configurare DoD checklist (12 items) in Jira
- [ ] Assegnare a Senior Dev A

---

### Task 2.2: Git Setup
**Owner**: Senior Dev A  
**Deadline**: Domani mattina (sprint start)  
**Effort**: 15 minuti

**Commands**:
```bash
# 1. Update master branch
git checkout master
git pull origin master

# 2. Create feature branch
git checkout -b feature/auth-service-refactoring

# 3. Verify clean state
git status

# 4. Push branch (per tracking)
git push -u origin feature/auth-service-refactoring
```

---

### Task 2.3: Baseline Performance Measurement
**Owner**: Senior Dev A  
**Deadline**: Domani mattina  
**Effort**: 30 minuti

**Commands**:
```bash
cd apps/web

# Eseguire suite E2E completa con timing
pnpm run test:e2e --reporter=html

# Annotare metriche baseline:
# - Tempo totale suite: _____ min
# - Story 4.1 test: _____ sec
# - Story 3.3 test: _____ sec  
# - Story 1.3 test: _____ sec
# - Flaky test count: _____
```

**Output**: Salvare report in `docs/metrics/baseline-e2e-performance-20251001.json`

---

### Task 2.4: PR Template Setup
**Owner**: Tech Lead  
**Deadline**: Domani mattina  
**Effort**: 20 minuti

**Create**: `.github/pull_request_template.md`

```markdown
## Story: Tech Debt - Auth Service Refactoring

### Fase Completata
- [ ] Fase 1: Creazione AuthService
- [ ] Fase 2: Migrazione Componenti
- [ ] Fase 3: Test E2E Migration
- [ ] Fase 4: Unit Test Componenti
- [ ] Fase 5: Cleanup & Documentazione
- [ ] Fase 6: Validazione Finale

### Acceptance Criteria (13)
- [ ] AC1: AuthService creato
- [ ] AC2: Componenti migrati
- [ ] AC3: window.supabase rimosso
- [ ] AC4: Test E2E migrati
- [ ] AC5: Mock standard
- [ ] AC6: Unit test creati
- [ ] AC7: Performance -40%
- [ ] AC8: Zero regressioni
- [ ] AC9: Test 100% passing
- [ ] AC10: Coverage >= 80%
- [ ] AC11: Doc testing updated
- [ ] AC12: Migration guide
- [ ] AC13: Helper gestiti

### Definition of Done (12)
- [ ] Tutti AC soddisfatti
- [ ] Test 100% passing
- [ ] Coverage >= 80%
- [ ] Security review
- [ ] Performance benchmark
- [ ] Rollback testato
- [ ] Team training
- [ ] Code review Tech Lead
- [ ] Doc completa
- [ ] Zero regressioni staging
- [ ] Migration guide
- [ ] Ready for merge

### Checklist Pre-Merge
- [ ] Linter clean (ESLint)
- [ ] No import diretto `supabase` in componenti
- [ ] 10 run E2E consecutivi passed
- [ ] Rollback procedure documentata e testata
```

---

## 🚀 Action #3: Kick-off Sviluppo (Day 1)

### Task 3.1: Kick-off Meeting
**Owner**: Scrum Master  
**When**: Domani mattina (9:00 AM)  
**Duration**: 30 min  
**Attendees**: Senior Dev A, Tech Lead, QA Lead

**Agenda**:
1. Recap sprint goal (5min)
2. Review Fase 1 tasks (10min)
3. Setup pair programming session (opzionale) (5min)
4. Q&A e chiarimenti (10min)

---

### Task 3.2: Start Fase 1 — Creazione AuthService
**Owner**: Senior Dev A  
**When**: Domani mattina (post kick-off)  
**Duration**: Giorno 1 (8h)

**Sub-tasks Fase 1**:

**T1.1**: Creare `apps/web/src/services/authService.ts` (2h)
```typescript
// File: apps/web/src/services/authService.ts
import { supabase } from '@/lib/supabaseClient';
import type { Session } from '@supabase/supabase-js';

export interface IAuthService {
  getSession(): Promise<{ data: { session: Session | null }, error: any }>;
  onAuthStateChange(callback): { data: { subscription: { unsubscribe: () => void } } };
  isAdmin(session: Session | null): boolean;
  isStudent(session: Session | null): boolean;
  isAuthenticated(session: Session | null): boolean;
}

class AuthService implements IAuthService {
  private client = supabase;
  
  async getSession() {
    return this.client.auth.getSession();
  }
  
  onAuthStateChange(callback) {
    return this.client.auth.onAuthStateChange(callback);
  }
  
  isAdmin(session: Session | null): boolean {
    const role = session?.user?.user_metadata?.role as string | undefined;
    return role === 'admin';
  }
  
  isStudent(session: Session | null): boolean {
    const role = session?.user?.user_metadata?.role as string | undefined;
    return role === 'student';
  }
  
  isAuthenticated(session: Session | null): boolean {
    return session !== null;
  }
}

export const authService = new AuthService();
```

**T1.2**: Unit test `authService.test.ts` (3h)
```typescript
// File: apps/web/src/services/__tests__/authService.test.ts
import { describe, it, expect, vi } from 'vitest';
import { authService } from '../authService';

describe('AuthService', () => {
  it('getSession returns session from Supabase', async () => {
    // Test implementation
  });
  
  it('isAdmin returns true for admin role', () => {
    const session = { user: { user_metadata: { role: 'admin' } } };
    expect(authService.isAdmin(session)).toBe(true);
  });
  
  // ... more tests
});
```

**T1.3**: Commit & PR (1h)
```bash
git add apps/web/src/services/authService.ts
git add apps/web/src/services/__tests__/authService.test.ts
git commit -m "feat: add AuthService with interface and unit tests (Fase 1)"
git push origin feature/auth-service-refactoring

# Create Draft PR
gh pr create --draft --title "Tech Debt: Auth Service Refactoring" --body "WIP - Fase 1 complete"
```

---

## 📊 Daily Standup Template

**For Senior Dev A** (to use in daily standup):

```
Yesterday:
- Completed: [Fase X, Task Y]
- Blockers: [None / Describe blocker]

Today:
- Plan: [Fase X, Task Y]
- Need help: [None / Tech Lead review / QA support]

Risks:
- [None / Effort tracking: X% complete vs Y% time elapsed]
```

---

## 📈 Progress Tracking Dashboard

### Daily Check-in (End of Day)

**Day 1** (Fase 1):
- [ ] AuthService.ts created with IAuthService interface
- [ ] Unit tests written (coverage >= 85%)
- [ ] Draft PR created
- [ ] Tech Lead review requested

**Day 2** (Fase 2):
- [ ] AdminGuard.tsx migrated to authService
- [ ] AuthGuard.tsx migrated to authService
- [ ] No direct supabase imports in components
- [ ] Visual smoke test passed

**Day 3-4** (Fase 3):
- [ ] story-4.1.spec.ts migrated
- [ ] story-1.3.spec.ts migrated
- [ ] story-3.3.spec.ts migrated
- [ ] Performance validation >= -40%
- [ ] 10 run stability test passed

**Day 5** (Fase 4):
- [ ] AdminGuard.test.tsx created (coverage >= 90%)
- [ ] AuthGuard.test.tsx created (coverage >= 90%)

**Day 6** (Fase 5):
- [ ] window.supabase removed
- [ ] authMock.ts deprecated
- [ ] Documentation updated
- [ ] Migration guide complete

**Day 7** (Fase 6):
- [ ] Rollback procedure tested
- [ ] Full regression suite passed
- [ ] Security review complete
- [ ] All DoD criteria satisfied
- [ ] PR ready for final review

---

## 🚨 Escalation Triggers

**Immediate Escalation to Tech Lead IF**:
- Senior Dev A bloccato > 2h su stesso issue
- Flaky test persistenti dopo debug
- Regressione imprevista scoperta
- Effort > estimate per fase (+50%)

**Escalation to PO IF**:
- Prerequisito Story 4.1 non soddisfatto (postpone sprint)
- Effort supera 7 giorni (scope reduction needed)
- Critical blocker non risolvibile in sprint

**Escalation to Scrum Master IF**:
- Team member assente (malattia, emergenza)
- External dependency blocker (DevOps, infra)
- Sprint goal at risk

---

## ✅ Success Criteria (Final Check)

**Before marking story DONE**:

### Technical Validation
- [ ] Tutti 13 AC verificati e approvati
- [ ] 12 DoD criteria soddisfatti
- [ ] 68 test cases eseguiti e passanti
- [ ] Coverage >= 80% confermato
- [ ] Performance -40% misurato e documentato
- [ ] Zero flaky test su 10 run

### Process Validation
- [ ] Code review Tech Lead approvato
- [ ] Security review completato
- [ ] Rollback procedure testata (< 15min)
- [ ] Migration guide utilizzata da altro dev (validation)
- [ ] Team training session eseguita

### Business Validation
- [ ] PO demo acceptance ottenuta
- [ ] Zero regressioni in staging confermato
- [ ] Deployment plan approvato
- [ ] Post-deploy monitoring setup

---

## 📅 Timeline Summary

**Today (2025-10-01)**:
- ⏳ Action #1: Validate Story 4.1 prerequisito (BLOCKER)
- ⏳ Action #2.1: Jira setup (Scrum Master)

**Tomorrow (Sprint Day 1)**:
- ⏳ Action #2.2: Git branch setup
- ⏳ Action #2.3: Baseline measurement
- ⏳ Action #2.4: PR template
- ⏳ Action #3.1: Kick-off meeting
- ⏳ Action #3.2: Start Fase 1

**Day 2-7**:
- Fase 2-6 execution
- Daily standup monitoring
- Continuous code review
- Final validation & merge

---

## 🎯 Next Immediate Step

### RIGHT NOW (Next 1 Hour):

**Step 1**: Verificare prerequisito Story 4.1
```bash
# Domanda al DevOps/Tech Lead:
"Story 4.1 (Admin Debug View) è in produzione da almeno 1 settimana?"

# Se SI → Procedi
# Se NO → Postpone e comunica
```

**Step 2**: Se prerequisito OK, creare Jira items
- Epic + Story + 6 Sub-tasks
- Assegnare a Senior Dev A
- Linkare documentazione

**Step 3**: Comunicare a team
```
Slack message to #team-fisiorag:

🚀 Sprint Planning Complete!

Story: Tech Debt - Auth Service Refactoring (8 SP)
Sprint: Post-MVP Sprint 1
Owner: @SeniorDevA

✅ Tutti approval ottenuti (PO, Tech Lead, QA)
⏳ BLOCKER: Validare Story 4.1 in prod >= 1 settimana

Action needed:
- @DevOps: Validate Story 4.1 status (TODAY)
- @ScrumMaster: Setup Jira (TODAY)
- @SeniorDevA: Branch + baseline (TOMORROW)

Kick-off meeting: Tomorrow 9:00 AM
```

---

## 📞 Contacts & Support

**For Questions**:
- Technical: @TechLead (architecture, code review)
- Process: @ScrumMaster (blockers, sprint issues)
- Business: @ProductOwner (AC clarification, scope)
- Testing: @QALead (test strategy, validation)

**Documentation**:
- Story: `docs/stories/tech-debt-auth-service-refactoring.md`
- Addendum: `docs/architecture/addendum-auth-service-refactoring.md`
- Test Design: `docs/qa/assessments/tech-debt-auth-refactoring-test-design-20251001.md`
- Sprint Planning: `docs/qa/assessments/tech-debt-auth-refactoring-sprint-planning-20251001.md`

---

**Status**: ⏳ **WAITING FOR ACTION #1 (Story 4.1 Validation)**  
**Next Milestone**: Sprint Day 1 Kick-off  
**Document Owner**: Scrum Master  
**Last Updated**: 2025-10-01

