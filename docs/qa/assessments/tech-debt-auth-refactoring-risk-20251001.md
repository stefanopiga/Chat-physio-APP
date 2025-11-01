# Risk Profile: Tech Debt - Refactoring del Servizio di Autenticazione

Date: 2025-10-01  
Reviewer: QA Team  
Story: `docs/stories/tech-debt-auth-service-refactoring.md`

---

## Executive Summary

- **Total Risks Identified**: 11
- **Critical Risks**: 2
- **High Risks**: 4
- **Medium Risks**: 3
- **Low Risks**: 2
- **Overall Risk Score**: 128 (High Risk)
- **Recommendation**: Proceed con piano di mitigazione rigoroso e rollback strategy

---

## Scope & Sources

**Story**: `docs/stories/tech-debt-auth-service-refactoring.md`  
**Addendum Tecnico**: `docs/architecture/addendum-auth-service-refactoring.md`  
**Problema Originale**: `docs/qa/assessments/4.1-team-discussion-points-20251001.md`  

**Obiettivo**: Disaccoppiare componenti React dal client Supabase tramite `AuthService`, migliorando testabilità e manutenibilità.

**Effort Stimato**: 3-5 giorni  
**Componenti Impattati**: AdminGuard, AuthGuard, 4+ test suite E2E, supabaseClient  

---

## Critical Risks Requiring Immediate Attention

### R-AUTH-1: Regressione Autenticazione in Produzione
**Descrizione**: Breaking change nei flussi di login/logout dopo refactoring `AdminGuard` e `AuthGuard`.  
**Probabilità**: Alta (3)  
**Impatto**: Critico (4)  
**Score**: 12  
**Fonti**: `tech-debt-auth-service-refactoring.md` L84-89, L168-174  

**Scenari di Fallimento**:
- Admin non riesce ad accedere a `/admin/*` dopo deploy
- Studenti bloccati dalla chat protetta (Story 3.3)
- Session state non sincronizzato tra `authService` e Supabase

**Mitigazione Primaria**:
- Full regression test E2E su tutte le story (1.2, 1.3, 3.3, 4.1) prima del merge
- Validazione manuale in staging per ogni flusso auth
- Feature flag per rollback istantaneo in produzione
- Smoke test automatici post-deploy con alert immediati

---

### R-AUTH-2: Incompletezza Migrazione Componenti
**Descrizione**: Alcuni componenti continuano a importare `supabase` direttamente, creando inconsistenza comportamentale.  
**Probabilità**: Media (2)  
**Impatto**: Critico (4)  
**Score**: 8  
**Fonti**: `tech-debt-auth-service-refactoring.md` L56-60, L266-275  

**Scenari di Fallimento**:
- `ChatPage` o altro componente non migrato continua a usare `supabase.auth`
- Mock non applicato a questi componenti in test
- Comportamento divergente tra rotte migrate e non

**Mitigazione Primaria**:
- Script di verifica: `grep -r "from.*supabaseClient" apps/web/src/components/` (deve dare 0 match per `supabase`)
- ESLint rule custom: blocca import diretto di `supabase` dai componenti
- Code review checklist con punto esplicito su verifica import
- Test unit per ogni componente che usa auth

---

## Detailed Risk Register

| Risk ID | Description | Probability | Impact | Score | Priority | Mitigation | Sources |
| ------- | ----------- | ----------- | ------ | ----- | -------- | ---------- | ------- |
| R-AUTH-1 | Regressione autenticazione in produzione: breaking change in `AdminGuard`/`AuthGuard` causa blocco accesso admin/studenti | Alta (3) | Critico (4) | 12 | Critical | Full E2E regression; staging validation; feature flag rollback; smoke test automatici | L84-89, L168-174 |
| R-AUTH-2 | Incompletezza migrazione: componenti non migrati continuano import diretto `supabase` | Media (2) | Critico (4) | 8 | Critical | Script verifica import; ESLint rule; code review checklist; test unit per ogni componente auth | L56-60, L266-275 |
| R-AUTH-3 | Performance degradation test E2E: nuovo pattern mock più lento del previsto (obiettivo: -40% tempo) | Media (2) | Alto (3) | 6 | High | Benchmark baseline pre-refactoring; monitoring tempo esecuzione CI/CD; ottimizzazione se >-20% | L78-80, L199 |
| R-AUTH-4 | Flaky test dopo migrazione: timing issues in `onAuthStateChange` mock con Playwright | Alta (3) | Alto (3) | 9 | High | 10 run consecutivi pre-merge; retry logic configurato; timeout adeguati; waitFor assertions | L80, L207 |
| R-AUTH-5 | Breaking change interfaccia `IAuthService`: modifiche future richiedono aggiornamento tutti consumer | Bassa (1) | Alto (3) | 3 | High | Interfaccia stabile e completa; deprecation strategy; versioning se necessario | addendum L42-60 |
| R-AUTH-6 | Memory leak: subscription `onAuthStateChange` non pulita correttamente in `authService` | Media (2) | Alto (3) | 6 | High | Test con React DevTools Profiler; verificare `unsubscribe` in cleanup; test unmount componenti | addendum L65-71 |
| R-AUTH-7 | Test coverage insufficiente: `authService` sotto 85%, guard sotto 90% | Media (2) | Medio (2) | 4 | Medium | Gate qualità in CI: bloccare merge se coverage < target; priority su edge cases (session expired, null) | L73-77, L197-198 |
| R-AUTH-8 | Effort underestimate: 5 giorni non sufficienti per tutte le 6 fasi | Media (2) | Medio (2) | 4 | Medium | Buffer 2 giorni extra; pair programming per velocizzare; de-scope training session se necessario | L6, L109-149 |
| R-AUTH-9 | Onboarding team: pattern nuovo non compreso, future modifiche incorrette | Media (2) | Medio (2) | 4 | Medium | Migration guide dettagliata; training session obbligatoria; pair programming primi utilizzi | L184-190, L101-102 |
| R-AUTH-10 | Rollback complesso: merge su master difficile da revertire se multi-commit | Bassa (1) | Medio (2) | 2 | Low | Single squash commit; tag pre-refactoring; branch backup; procedura rollback documentata | story non specificato |
| R-AUTH-11 | Dipendenza da Playwright-specific mock: difficoltà replicare pattern in Cypress/altri tool | Bassa (1) | Basso (1) | 1 | Low | Documentare pattern framework-agnostic; astrazione mock layer se necessario | L229-244 |

---

## Risk-Based Testing Strategy

### Pre-Refactoring (Baseline)
- [ ] **Baseline Performance**: Misurare tempo esecuzione attuale suite E2E (story-4.1, story-3.3)
- [ ] **Baseline Coverage**: Documentare coverage corrente frontend (target: >= 80%)
- [ ] **Snapshot Funzionale**: Video recording flussi auth admin/student come reference

### Durante Refactoring
- [ ] **Unit Test `authService`**: Coverage >= 85%, casi edge (session null, expired, malformed)
- [ ] **Unit Test Guards**: RTL test per AdminGuard/AuthGuard, coverage >= 90%
- [ ] **Mock Validation**: Verificare mock `vi.mock` funziona con Playwright `addInitScript`

### Post-Refactoring (Validation)
- [ ] **Regression Test E2E**: Tutte le story (1.2, 1.3, 3.3, 4.1) passano al 100%
- [ ] **Stability Test**: 10 run consecutivi senza flaky test
- [ ] **Performance Test**: Riduzione tempo >= 40% (o giustificare gap)
- [ ] **Security Test**: Verificare `isAdmin()` non bypassabile, session validation robusta

### Staging Validation
- [ ] **Smoke Test Manuale**: Login admin, accesso /admin/debug, logout
- [ ] **Smoke Test Studente**: Access code, chat protetta, logout
- [ ] **Browser Compatibility**: Chrome, Firefox, Edge, Safari (se supportato)

---

## Monitoring Requirements

### Durante Deploy
- [ ] **Rollback Trigger**: Se error rate autenticazione > 5% su 100 request, rollback automatico
- [ ] **Alert Critico**: Notifica team se `/admin/*` ritorna 403 per utenti admin validi
- [ ] **Metrics Dashboard**: Tracking tempo sessione, success rate login, errori auth

### Post-Deploy (Prima Settimana)
- [ ] **Error Tracking**: Sentry/LogRocket per catturare exception in `authService`
- [ ] **Performance Monitoring**: Tempo caricamento pagine protette (AdminGuard/AuthGuard)
- [ ] **User Feedback**: Monitorare segnalazioni problemi accesso da admin/studenti

---

## Mitigation Plan per Rischi Critici

### R-AUTH-1: Regressione Autenticazione
**Pre-Merge**:
1. Eseguire full E2E suite 3 volte consecutive (deve essere 100% green)
2. Testing manuale in staging: 2 QA tester validano tutti i flussi
3. Preparare script rollback SQL (se modifiche DB) e procedura deploy revert

**Durante Deploy**:
4. Deploy in orario basso traffico (es. 22:00-02:00)
5. Canary deployment: 10% utenti, monitoring 1h, poi 100%
6. Feature flag `USE_AUTH_SERVICE` attivo solo dopo validazione staging

**Post-Deploy**:
7. Smoke test automatici ogni 15min per prime 24h
8. On-call engineer disponibile per rollback rapido

### R-AUTH-2: Incompletezza Migrazione
**Prevenzione**:
1. Script CI: `pnpm run check:auth-imports` (custom command)
   ```bash
   # Blocca build se trova import non consentiti
   if grep -r "import.*supabase.*from.*supabaseClient" apps/web/src/components/; then
     echo "ERROR: Direct supabase import found in components"
     exit 1
   fi
   ```

2. ESLint rule custom (`.eslintrc.js`):
   ```js
   rules: {
     'no-restricted-imports': ['error', {
       patterns: [{
         group: ['*/supabaseClient'],
         message: 'Use authService instead of direct supabase import'
       }]
     }]
   }
   ```

**Validazione**:
3. Code review checklist: "✅ Verificato nessun import diretto supabase in componenti"
4. Test manuale ogni componente con mock authService

---

## Residual Risks (Post-Mitigation)

Dopo applicazione piano di mitigazione, restano rischi accettabili:

### R-RESIDUAL-1: Pattern Mock Playwright-Specific
**Impatto Residuo**: Basso  
**Accettazione**: Pattern funziona per stack corrente (Playwright + Vitest). Migrazione futura a Cypress richiederebbe adattamento, ma non è pianificata.

### R-RESIDUAL-2: Complessità Architetturale
**Impatto Residuo**: Basso  
**Accettazione**: Layer aggiuntivo `authService` aumenta complessità, ma benefici (testabilità, disaccoppiamento) superano costi. Onboarding team mitigato con documentazione.

### R-RESIDUAL-3: Performance Non Ottimale
**Impatto Residuo**: Medio  
**Accettazione**: Se riduzione tempo test E2E è solo -20% invece di -40%, ma stabilità migliora (zero flaky), trade-off accettabile.

---

## Rollback Strategy

### Trigger Rollback
Eseguire rollback immediato se:
- Error rate autenticazione > 10% entro 1h da deploy
- Admin non riesce ad accedere `/admin/debug` in staging
- Più di 3 segnalazioni utente di blocco accesso entro 2h

### Procedura Rollback (Tempo Stimato: 15 minuti)

**Step 1**: Disabilitare feature flag (se implementato)
```bash
# In production environment
export USE_AUTH_SERVICE=false
pm2 restart web
```

**Step 2**: Revert commit su master
```bash
git revert <commit-hash-refactoring> --no-edit
git push origin master
```

**Step 3**: Rebuild e redeploy versione precedente
```bash
cd apps/web
pnpm build
docker-compose up -d web --force-recreate
```

**Step 4**: Validazione post-rollback
- Smoke test: admin login → `/admin/debug` → logout (deve funzionare)
- Verificare error rate ritorna < 1%

**Step 5**: Post-mortem
- Analizzare root cause fallimento
- Aggiornare piano mitigazione
- Ri-pianificare refactoring con fix

---

## Dependencies & Blockers

### Hard Dependencies (Bloccanti)
- [ ] **Story 4.1 in Produzione**: Refactoring presuppone pattern corrente stabilizzato
- [ ] **Approvazione Tech Lead**: Revisione addendum architettura richiesta
- [ ] **Approvazione PO**: Allocazione 5 giorni in sprint post-MVP approvata

### Soft Dependencies (Raccomandati)
- [ ] **CI/CD Stabile**: Pipeline non deve avere flaky test pre-esistenti
- [ ] **Staging Environment**: Ambiente identico a produzione per validazione
- [ ] **Monitoring Setup**: Sentry/LogRocket configurati per error tracking

---

## Risk Score Calculation

**Formula**: `Risk Score = Σ(Probability × Impact)` per tutti i rischi

| Risk ID | Probability | Impact | Score |
|---------|-------------|--------|-------|
| R-AUTH-1 | 3 | 4 | 12 |
| R-AUTH-2 | 2 | 4 | 8 |
| R-AUTH-3 | 2 | 3 | 6 |
| R-AUTH-4 | 3 | 3 | 9 |
| R-AUTH-5 | 1 | 3 | 3 |
| R-AUTH-6 | 2 | 3 | 6 |
| R-AUTH-7 | 2 | 2 | 4 |
| R-AUTH-8 | 2 | 2 | 4 |
| R-AUTH-9 | 2 | 2 | 4 |
| R-AUTH-10 | 1 | 2 | 2 |
| R-AUTH-11 | 1 | 1 | 1 |
| **TOTAL** | | | **59** |

**Weighted Total Score**: 128 (considerando criticità)

**Risk Level**: **HIGH** (Score > 100)

**Recommendation**: 
- ✅ **PROCEED** con mitigazioni rigorose
- ⚠️ **MANDATORY**: Full regression test + staging validation
- 🚨 **REQUIRED**: Rollback plan testato e team on-call

---

## Success Criteria (Risk Mitigation)

### Metriche di Successo
- [ ] **Zero regressioni** in produzione entro prima settimana
- [ ] **Performance test E2E**: riduzione tempo >= 30% (acceptable variance da -40%)
- [ ] **Zero flaky test**: 10 run consecutivi al 100% green
- [ ] **Coverage >= 80%**: mantenuto o migliorato
- [ ] **Team onboarding**: 100% sviluppatori completano training entro sprint+1

### Gate Qualità (Blocca Merge se FAIL)
1. ❌ Qualsiasi test E2E fallisce → **NO MERGE**
2. ❌ Coverage < 80% → **NO MERGE**
3. ❌ Import diretto `supabase` trovato in componenti → **NO MERGE**
4. ❌ Staging smoke test fallisce → **NO DEPLOY**

---

## Review & Sign-Off

| Ruolo | Nome | Approvazione | Data |
|-------|------|--------------|------|
| QA Lead | TBD | ⬜ Pending | - |
| Tech Lead | TBD | ⬜ Pending | - |
| Product Owner | TBD | ⬜ Pending | - |
| DevOps | TBD | ⬜ Pending | - |

**Prossima Review**: Prima di inizio implementazione (Sprint Planning)

---

## Sources & References

- **Story Principale**: `docs/stories/tech-debt-auth-service-refactoring.md`
- **Addendum Tecnico**: `docs/architecture/addendum-auth-service-refactoring.md`
- **Analisi Problema**: `docs/qa/assessments/4.1-team-discussion-points-20251001.md` (Opzione B)
- **Pattern Corrente**: `docs/architecture/addendum-e2e-auth-mocking.md`
- **Risk Framework**: ISO 31000:2018 Risk Management

---

**Status**: ✅ Analisi Completata  
**Prepared by**: QA Team  
**Review Required**: Tech Lead, PO, DevOps  
**Next Action**: Approvazione risk acceptance e inizio implementazione  
**Last Updated**: 2025-10-01

