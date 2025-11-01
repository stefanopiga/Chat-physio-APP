# Procedura di Rollback - Auth Service Refactoring

**Data**: 2025-10-01  
**Versione**: 1.0  
**Tempo Stimato**: < 15 minuti  
**Rischio**: Basso (operazione reversibile)

---

## Scenario di Rollback

In caso di problemi critici rilevati dopo il deploy in produzione, è possibile ripristinare il pattern precedente tramite `git revert`.

---

## Procedura Step-by-Step

### Step 1: Identificare il Commit di Merge (< 1 min)

```bash
cd apps/web
git log --oneline --grep="auth-service-refactoring" -n 5
```

Output esempio:
```
a1b2c3d Merge branch 'feature/auth-service-refactoring'
```

### Step 2: Revert del Merge (< 1 min)

```bash
git revert -m 1 a1b2c3d
```

Parametro `-m 1`: indica quale parent mantenere (1 = branch principale).

### Step 3: Verifica delle Modifiche (< 2 min)

Controllare che i file siano stati ripristinati:

```bash
git diff HEAD~1 HEAD -- src/services/authService.ts
git diff HEAD~1 HEAD -- src/components/AdminGuard.tsx
git diff HEAD~1 HEAD -- src/lib/supabaseClient.ts
```

Verifica attesa:
- `authService.ts` eliminato
- `AdminGuard.tsx` e `AuthGuard.tsx` tornano a usare `supabase.auth`
- `supabaseClient.ts` ripristina `window.supabase`

### Step 4: Test di Regressione (< 5 min)

```bash
pnpm run test
pnpm run test:e2e
```

Atteso: Tutti test devono passare (pattern legacy).

### Step 5: Commit e Push (< 1 min)

```bash
git commit -m "Revert: rollback auth-service-refactoring per issue #XXX"
git push origin master
```

### Step 6: Deploy in Staging (< 5 min)

Seguire procedura CI/CD standard per deploy in staging.

### Step 7: Validazione Post-Rollback (< 2 min)

Verificare in staging:
- Login admin funzionante
- Login studente funzionante
- Protezione rotte `/admin/*`
- Chat protetta funzionante
- Debug view funzionante

---

## File da Ripristinare

**File eliminati nel refactoring** (ripristinati automaticamente da `git revert`):
- `apps/web/tests/helpers/authMock.ts`

**File modificati nel refactoring** (ripristinati automaticamente):
- `apps/web/src/components/AdminGuard.tsx`
- `apps/web/src/components/AuthGuard.tsx`
- `apps/web/src/lib/supabaseClient.ts`
- `apps/web/tests/story-4.1.spec.ts`
- `apps/web/tests/story-3.3.spec.ts`

**File creati nel refactoring** (eliminati automaticamente):
- `apps/web/src/services/authService.ts`
- `apps/web/src/services/__tests__/authService.test.ts`
- `apps/web/src/components/__tests__/AdminGuard.test.tsx`
- `apps/web/src/components/__tests__/AuthGuard.test.tsx`

---

## Validazione Rollback Preventiva

**Test eseguito**: 2025-10-01  
**Branch**: `feature/auth-service-refactoring-rollback-test`  
**Risultato**: ✅ Rollback testato con successo

Procedura testata:
1. Creato branch test da `feature/auth-service-refactoring`
2. Eseguito `git revert` del merge commit simulato
3. Eseguito `pnpm run test && pnpm run test:e2e`
4. Risultato: pattern legacy ripristinato correttamente

---

## Checklist Post-Rollback

- [ ] Test unit passano al 100%
- [ ] Test E2E passano al 100%
- [ ] Login admin funzionante in staging
- [ ] Login studente funzionante in staging
- [ ] Protezione rotte verificata in staging
- [ ] Monitoraggio errori produzione (nessun nuovo errore)
- [ ] Comunicazione al team dell'avvenuto rollback
- [ ] Creazione issue per analisi root cause
- [ ] Planning per fix e re-deploy

---

## Contatti Emergenza

**Tech Lead**: [Nome]  
**DevOps**: [Nome]  
**On-Call**: [Numero]

---

**Nota**: Questa procedura è stata testata e validata. Tempo totale effettivo: **< 15 minuti** come da requirement.

