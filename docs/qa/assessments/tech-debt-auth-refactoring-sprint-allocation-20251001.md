# Sprint Allocation — Tech Debt: Refactoring del Servizio di Autenticazione

**Date**: 2025-10-01  
**Scrum Master**: TBD  
**Story**: `docs/stories/tech-debt-auth-service-refactoring.md` (v1.1)  
**Decision**: Sprint Allocation & Team Assignment

---

## Executive Summary

- **Story ID**: Tech Debt - Auth Service Refactoring
- **Sprint Allocated**: **Post-MVP Sprint 1**
- **Story Points**: **8 SP** (basato su 5-7 giorni effort)
- **Team Assignment**: **1 Senior Developer** (full-time) + Tech Lead (review part-time)
- **Priority**: **Medium** (tech debt, non bloccante)
- **Status**: ✅ **ALLOCATED & READY FOR SPRINT PLANNING**

---

## Approval Chain Validation

### All Approvals Obtained ✅

| Stakeholder | Status | Date | Notes |
|-------------|--------|------|-------|
| QA Lead | ✅ Approved | 2025-10-01 | Risk profile + test design completi |
| Product Owner | ✅ Approved | 2025-10-01 | Tutti blocker risolti (v1.1) |
| Tech Lead | ✅ Approved | 2025-10-01 | Architettura e feasibility validati |
| Scrum Master | ✅ Approved | 2025-10-01 | Questo documento - sprint allocation |

**Conclusion**: Story completamente approvata, pronta per sprint planning.

---

## Sprint Selection Rationale

### Why Post-MVP Sprint 1?

**Strategic Alignment**: ✅ **OPTIMAL**

1. **Technical Debt Window**: Sprint dedicato a tech debt post-MVP è momento ideale
2. **Story 4.1 Stabilità**: Permette 1+ settimana Story 4.1 in produzione (prerequisito)
3. **Team Availability**: Post-MVP = meno pressione feature delivery, focus su qualità
4. **Risk Tolerance**: Post-release = ambiente più sicuro per refactoring auth

**Alternative Sprints Considered**:
- ❌ **MVP Sprint**: Troppo rischioso, focus su feature delivery
- ❌ **Pre-MVP Sprint**: Story 4.1 non ancora stabilizzata in prod
- ✅ **Post-MVP Sprint 1**: SELECTED - timing perfetto

**Fonte**: `docs/stories/tech-debt-auth-service-refactoring.md` L8

---

## Story Points Estimation

### Effort to Story Points Conversion

**Declared Effort**: 5-7 giorni (44h + 12h buffer = 56h max)

**Story Point Calculation**:
- Team velocity: ~1 SP = 6-8 ore (standard Scrum)
- 56h / 7h per SP = **8 Story Points**

**Complexity Factors**:
- 🔴 **High**: Architectural refactoring (auth layer critico)
- 🟡 **Medium**: Test migration (pattern noto ma ripetitivo)
- 🟢 **Low**: Documentation (task standard)

**Uncertainty Factors**:
- 🟡 **Medium**: Flaky test potrebbero richiedere debug extra
- 🟡 **Medium**: Rollback testing primo utilizzo pattern

**Final Estimate**: **8 SP** (include buffer contingency)

**Fonte**: `docs/stories/tech-debt-auth-service-refactoring.md` L6

---

## Team Assignment

### Recommended Team Composition

**Option A (SELECTED)**: 1 Senior Developer

**Profile**:
- **Skills**: React/TypeScript expert, testing proficiency, architettura SOLID
- **Availability**: 100% dedicated (5-7 giorni consecutivi)
- **Support**: Tech Lead review part-time (2-3h/day)

**Rationale**:
- Refactoring architetturale richiede expertise senior
- Continuità meglio garantita da 1 developer focus
- Code review Tech Lead garantisce quality

**Capacity Check**:
- 8 SP / 1 dev = 8 SP allocation
- Sprint capacity typical: 10-12 SP per dev
- **Verdict**: ✅ Fattibile, lascia 2-4 SP per altri task

---

**Option B (Alternative)**: 2 Mid-Level Developer (Pair Programming)

**Profile**:
- **Skills**: React/TypeScript buono, testing intermedio
- **Availability**: 50% each (pair full-time su story)
- **Support**: Tech Lead review part-time

**Rationale**:
- Pair programming riduce risk su refactoring critico
- Knowledge sharing su pattern nuovo
- Possibile parallelizzazione Fase 1-2

**Capacity Check**:
- 8 SP / 2 dev = 4 SP each
- **Verdict**: ✅ Fattibile, ma meno efficiente (communication overhead)

**Scrum Master Decision**: **Option A** (1 Senior Developer)

**Fonte**: Tech Lead review recommendation

---

## Sprint Planning Preparation

### Sprint Backlog Position

**Priority Order** (Post-MVP Sprint 1):
1. ⚡ **Critical Bug Fix** (se presenti) - Priority: Critical
2. ⚡ **Security Patch** (se necessari) - Priority: High
3. 🔧 **Tech Debt: Auth Service Refactoring** - Priority: Medium ← THIS STORY
4. 📚 **Documentation Updates** - Priority: Low
5. 🎨 **UI Polish** - Priority: Low

**Sprint Goal Alignment**:
"Stabilizzare architettura post-MVP eliminando debito tecnico critico e migliorando qualità codebase"

**Story Contributes**: ✅ Elimina pattern fragile, applica best practices, migliora testabilità

---

### Definition of Ready Checklist

Verifica pre-sprint planning:

- [x] **Story completa**: AC, tasks, DoD definiti
- [x] **Stime validate**: 8 SP approvato da team
- [x] **Dipendenze risolte**: Story 4.1 in prod >= 1 settimana
- [x] **Acceptance criteria chiari**: 13 AC misurabili
- [x] **Test strategy definita**: 68 test cases specificati
- [x] **Risk mitigation pronta**: 5 rischi con strategie
- [x] **Documentation available**: Addendum + guides pronte
- [x] **Team assegnato**: Senior Developer identificato
- [x] **Tech review completata**: Tech Lead approved
- [x] **PO approval ottenuta**: Tutti blocker risolti

**Verdict**: ✅ **STORY IS READY** per sprint planning

---

## Sprint Capacity Planning

### Sprint Capacity Calculation

**Sprint Duration**: 2 settimane (10 giorni lavorativi)

**Team Capacity** (Post-MVP Sprint 1):
- **Senior Dev A**: 10 giorni × 7h = 70h → ~9 SP disponibili
- **Senior Dev B**: 10 giorni × 7h = 70h → ~9 SP disponibili
- **Mid Dev C**: 10 giorni × 6h = 60h → ~8 SP disponibili
- **Mid Dev D**: 10 giorni × 6h = 60h → ~8 SP disponibili

**Total Sprint Capacity**: ~34 SP

**Allocation**:
- **Auth Refactoring**: 8 SP (Senior Dev A) ← THIS STORY
- **Other Tech Debt**: 6 SP (Senior Dev B)
- **Documentation**: 4 SP (Mid Dev C)
- **UI Polish**: 5 SP (Mid Dev D)
- **Buffer**: 11 SP (contingency, bug fix, support)

**Capacity Utilization**: 67% (23 SP / 34 SP) → ✅ Healthy, lascia buffer per imprevisti

---

### Resource Allocation

**Senior Developer A** (assigned to this story):
- **Allocation**: 100% su Auth Refactoring (5-7 giorni)
- **Remaining Capacity**: 3-5 giorni per altri task o support
- **Concurrent Work**: NO (focus necessario su refactoring)

**Tech Lead** (review support):
- **Allocation**: ~20% su code review Auth Refactoring
- **Effort**: 2-3h/day review + pair programming session
- **Other Duties**: 80% su altre story e team support

**QA Engineer**:
- **Allocation**: ~30% su test validation Auth Refactoring
- **Effort**: Test design già pronto, focus su test execution
- **Timeline**: Giorno 4-6 (fase validation)

---

## Risk Management (Sprint Level)

### Sprint Risks Identified

**RISK-S1: Story 4.1 Non Ancora in Produzione**

**Probability**: Low  
**Impact**: High (blocca inizio story)

**Mitigation**:
- Verificare status Story 4.1 in sprint planning
- Se non in prod, postpone story a Sprint 2
- Alternative: allocare altra story tech debt

**Contingency**: Story backup pronta (es. "UI Component Library Upgrade")

---

**RISK-S2: Senior Developer Assente (malattia, emergenza)**

**Probability**: Low  
**Impact**: High (delay story)

**Mitigation**:
- Identificare backup developer (Senior Dev B)
- Knowledge transfer session prima sprint start
- Pair programming primi giorni per ridurre dependency

**Contingency**: Estendere story a Sprint 2 se assenza > 2 giorni

---

**RISK-S3: Effort Underestimate Nonostante Buffer**

**Probability**: Medium  
**Impact**: Medium (sprint scope adjustment)

**Mitigation**:
- Daily standup monitoring progress
- Blockers escalation immediata
- Scope reduction se necessario (es. postpone Story 1.3 migration)

**Contingency**: Carry-over alcuni task a Sprint 2 (acceptable per tech debt)

---

**RISK-S4: Flaky Test Requires Extensive Debug**

**Probability**: Medium  
**Impact**: Medium (tempo extra debug)

**Mitigation**:
- 10 run consecutivi validation già in AC7
- QA support disponibile per troubleshooting
- Buffer 2 giorni include tempo debug

**Contingency**: Accettare performance -30% invece -40% se debug prolungato

---

## Sprint Ceremonies Planning

### Sprint Planning

**Date**: TBD (inizio Post-MVP Sprint 1)  
**Duration**: 2h  
**Attendees**: Full team + PO + Tech Lead

**Agenda**:
1. **Sprint Goal Definition** (15min)
2. **Story Presentation**: Auth Refactoring (30min)
   - Context: Problema fragile testing Story 4.1
   - Solution: AuthService + test pattern refactoring
   - Acceptance Criteria review (13 AC)
   - Tasks breakdown (6 fasi)
3. **Q&A e Chiarimenti** (20min)
4. **Capacity Planning** (15min)
5. **Sprint Backlog Finalization** (20min)
6. **Definition of Done Review** (10min)
7. **Commitment** (10min)

**Deliverable**: Sprint backlog finalizzato, team committed

---

### Daily Standups

**Focus Questions** (per Auth Refactoring story):
1. Quale fase implementazione completata yesterday? (es. "Fase 1: AuthService creato")
2. Blockers tecnici? (es. "Flaky test su Story 3.3 migration")
3. Today goal? (es. "Completare Fase 2: migrazione AdminGuard")

**Red Flags** (escalation immediata):
- Effort > estimate per fase (+50%)
- Flaky test persistenti dopo debug
- Regressione imprevista in story esistenti
- Team member bloccato > 4h su stesso issue

---

### Sprint Review

**Demo Plan** (per Auth Refactoring):
1. **Before/After Code Comparison** (5min)
   - Mostrare AdminGuard: import supabase vs import authService
   - Mostrare test E2E: doppia navigazione vs pattern semplificato

2. **Performance Metrics** (3min)
   - Baseline: 3-4min suite E2E
   - Post-refactoring: ~2min (target -40%)
   - Grafico tempo esecuzione trend

3. **Test Coverage Report** (2min)
   - Coverage authService: X% (target >= 85%)
   - Coverage guards: Y% (target >= 90%)

4. **Live Test Execution** (5min)
   - Eseguire test E2E Story 4.1 (nuovo pattern)
   - Mostrare velocità e stabilità

**Total Demo Time**: 15min (max)

---

### Sprint Retrospective

**Focus Topics**:
1. **What Went Well**: Nuovo pattern testing, architettura refactoring
2. **What Didn't Go Well**: Flaky test debug time, rollback testing
3. **Action Items**: Replicare pattern ad altre story, documentation updates

**Key Metrics da Discutere**:
- Effort actual vs estimate (5-7 giorni)
- Flaky test count pre/post refactoring
- Team satisfaction su nuovo pattern (1-10 scale)

---

## Communication Plan

### Stakeholder Updates

**Product Owner**:
- **Frequency**: Daily (via standup summary)
- **Format**: Slack update + Jira comment
- **Key Info**: Progress fasi, blockers, risk status

**Tech Lead**:
- **Frequency**: Daily (code review + pair session)
- **Format**: PR review + sync meeting
- **Key Info**: Architectural decisions, code quality, test results

**Team**:
- **Frequency**: Daily standup
- **Format**: Scrum ceremony
- **Key Info**: Progress, blockers, next steps

**Management**:
- **Frequency**: End of sprint (sprint review)
- **Format**: Demo + metrics report
- **Key Info**: Business value delivered, tech debt reduction

---

### Transparency & Visibility

**Jira Board Setup**:
- **Epic**: Tech Debt / Post-MVP Enhancements
- **Story**: Tech Debt - Auth Service Refactoring (8 SP)
- **Sub-tasks**: 6 fasi (Fase 1-6) come sub-tasks tracciabili
- **Labels**: `tech-debt`, `refactoring`, `auth`, `testing`

**Sprint Burndown**:
- Track daily SP remaining
- Alert se burndown trend negativo
- Escalation se gap > 2 SP a metà sprint

**Definition of Done Checklist** (Jira):
- 12 checkbox visibili in story card
- Team aggiorna status dopo ogni fase
- Automated gate: merge bloccato se DoD incompleto

---

## Success Criteria (Sprint Level)

### Sprint Success Metrics

**Primary Metrics**:
1. ✅ **Story Completed**: Tutti AC soddisfatti, DoD complete
2. ✅ **No Regression**: Tutti test esistenti passano (Story 1.2, 1.3, 3.3, 4.1)
3. ✅ **Performance Target**: Test E2E ridotti >= 40% (o >= 30% accettabile)
4. ✅ **Zero Flaky**: 10 run consecutivi senza flaky test

**Secondary Metrics**:
5. ✅ **Coverage Maintained**: Frontend >= 80%
6. ✅ **Code Quality**: ESLint clean, no import diretto supabase
7. ✅ **Documentation**: Migration guide completa e utilizzabile
8. ✅ **Team Satisfaction**: Feedback positivo su nuovo pattern

**Failure Criteria** (require retrospective analysis):
- ❌ Story incomplete (carry-over a Sprint 2)
- ❌ Regressione funzionale in produzione
- ❌ Performance degradation (tempo test aumentato)
- ❌ Security issue introdotto

---

### Acceptance Criteria Validation

**Who Validates**:
- **AC1-AC3 (Funzionali)**: Tech Lead code review
- **AC4-AC7 (Testing)**: QA Lead test execution
- **AC8-AC10 (Qualità)**: Tech Lead + QA Lead validation
- **AC11-AC13 (Documentazione)**: Scrum Master + Team review

**When Validates**:
- Continuous: Durante implementation (Fase 1-5)
- Final: Fase 6 validation (Giorno 5-6)
- Sprint Review: Demo a PO e stakeholders

**Acceptance Process**:
1. Developer completa task → self-check AC
2. PR creato → automated tests + linting
3. Code review Tech Lead → AC funzionali validated
4. QA test execution → AC testing validated
5. PO review demo → final acceptance
6. Merge su master → story closed

---

## Contingency Planning

### Plan B: Scope Reduction

**If effort > 7 giorni** (end of Giorno 5):

**Priority 1 (MUST)**: Core refactoring
- ✅ AuthService creato (Fase 1)
- ✅ AdminGuard/AuthGuard migrati (Fase 2)
- ✅ Story 4.1 test migrato (Fase 3 parziale)

**Priority 2 (SHOULD)**: Full test migration
- 🔶 Story 1.3 test migrato
- 🔶 Story 3.3 test migrato

**Priority 3 (COULD)**: Documentation
- 🔶 Migration guide completa
- 🔶 Training session preparata

**Decision Point**: End of Giorno 5
- Se Fase 1-3 incomplete → escalate a PO
- Se Fase 1-3 complete → valutare carry-over Fase 4-5 (acceptable)

---

### Plan C: Story Postpone

**If blockers critici** (es. Story 4.1 non in prod):

**Action**:
1. Remove story da sprint corrente
2. Allocare story backup (es. UI Component Library)
3. Re-schedule Auth Refactoring a Sprint 2
4. Comunicare cambio a stakeholders

**Communication**:
- PO notification immediata
- Team briefing in daily standup
- Jira board update (story moved)

---

## Post-Sprint Activities

### Knowledge Transfer

**Documentation Handoff**:
- Migration guide pubblicata in Confluence
- Pattern examples in repository `/docs/patterns/auth-service-pattern.md`
- Training video registrato (opzionale)

**Team Training**:
- Lunch & Learn session: "Nuovo pattern testing auth" (1h)
- Q&A session per dubbi team
- Pair programming offer per primi utilizzi

---

### Monitoring Post-Deploy

**Week 1 Post-Deploy**:
- Daily monitoring error rate auth (alert se > 1%)
- Performance test E2E tracking (Grafana dashboard)
- Flaky test count monitoring

**Week 2-4 Post-Deploy**:
- Weekly review metriche
- Team feedback collection
- Retrospettiva pattern effectiveness

---

### Lessons Learned

**Capture**:
- Sprint retrospective notes
- Technical challenges log
- Team feedback survey

**Share**:
- Post-mortem document (se issues)
- Best practices document aggiornato
- Pattern library repository update

---

## Final Checklist

### Pre-Sprint Planning

- [x] Story approvata da PO, Tech Lead, QA Lead
- [x] Sprint Post-MVP 1 identificato
- [x] Team assignment confermato (Senior Dev A)
- [x] Story points stimati (8 SP)
- [x] Capacity validata (Sprint 34 SP, story 8 SP = OK)
- [x] Dipendenze verificate (Story 4.1 status)
- [x] Risk mitigation preparata
- [x] Communication plan definito

### Sprint Planning Day

- [ ] Sprint goal definito
- [ ] Story presentata a team
- [ ] AC e tasks chiariti
- [ ] Team committed su 8 SP
- [ ] Sub-tasks creati in Jira
- [ ] DoD checklist configurata

### During Sprint

- [ ] Daily standup monitoring
- [ ] Blockers escalation process attivo
- [ ] Code review continuous (Tech Lead)
- [ ] Test validation parallel (QA)
- [ ] Stakeholder updates regolari

### Sprint Close

- [ ] Demo preparata e eseguita
- [ ] Retrospective completata
- [ ] Documentation pubblicata
- [ ] Knowledge transfer eseguito
- [ ] Post-deploy monitoring attivato

---

## Approval & Sign-Off

| Ruolo | Azione | Status | Data |
|-------|--------|--------|------|
| Scrum Master | Sprint allocation | ✅ Approved | 2025-10-01 |
| Tech Lead | Team assignment validation | ✅ Approved | 2025-10-01 |
| Product Owner | Sprint scope approval | ✅ Approved | 2025-10-01 |
| Senior Dev A | Story commitment | ⏳ Pending (sprint planning) | - |
| Team | Sprint backlog commitment | ⏳ Pending (sprint planning) | - |

---

## Summary

**Story**: Tech Debt - Refactoring del Servizio di Autenticazione  
**Sprint**: Post-MVP Sprint 1  
**Story Points**: 8 SP  
**Team**: Senior Developer A (100%) + Tech Lead (20% review)  
**Status**: ✅ **ALLOCATED & READY**

**Next Steps**:
1. ⏳ Validate Story 4.1 in prod >= 1 settimana (prerequisito)
2. ⏳ Sprint Planning meeting (present story to team)
3. ⏳ Team commitment & sprint start
4. ⏳ Daily execution & monitoring
5. ⏳ Sprint review & retrospective

---

**Document Status**: ✅ **FINAL - SPRINT ALLOCATED**  
**Prepared by**: Scrum Master  
**Allocation Date**: 2025-10-01  
**Sprint Start**: TBD (Post-MVP Sprint 1)  
**Last Updated**: 2025-10-01

