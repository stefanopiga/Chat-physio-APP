# Test Fix Report: Story 4.4

**Data**: 2025-10-05  
**Status**: Fixing E2E Test Failures

---

## Test Results Summary

### Backend Tests ✅
**Status**: 6/6 PASSED (100%)

| Test | Status | Notes |
|------|--------|-------|
| test_get_documents_success | ✅ PASSED | |
| test_get_documents_forbidden_non_admin | ✅ PASSED | |
| test_get_document_chunks_success | ✅ PASSED | |
| test_get_document_chunks_filter_strategy | ✅ PASSED | |
| test_get_document_chunks_sort_by_size | ✅ PASSED | |
| test_get_document_chunks_pagination | ✅ PASSED | |

**Coverage**: 57% (accettabile per endpoint isolati)

---

## E2E Tests ⚠️
**Status**: 3/6 PASSED (50%)

### Passed Tests ✅
1. Scenario 2: Click documento → chunks page
2. Scenario 3: Dialog contenuto completo
3. Scenario 4: Filter per strategy

### Failed Tests ❌

#### 1. Scenario 1: Strict Mode Violation
**Error**: `getByText('Documento')` resolved to 2 elements

**Root Cause**: 
- Text "Documento" appare in 2 posti:
  1. Descrizione: "Visualizza e analizza chunk generati per ogni **doc**umento"
  2. Header tabella: `<th>Documento</th>`

**Fix**:
```typescript
// Prima (ambiguo)
await expect(page.getByText("Documento")).toBeVisible();

// Dopo (specifico)
await expect(page.getByRole("columnheader", { name: "Documento" })).toBeVisible();
```

#### 2. Scenario 6: AdminGuard Non Blocca
**Error**: Expected `/login`, received `/admin/documents`

**Root Cause**:
- `addInitScript()` con `localStorage.removeItem()` non funziona per pagine già caricate
- Token rimane in localStorage della pagina esistente

**Fix**:
```typescript
// Prima (non funziona)
await page.addInitScript(() => {
  localStorage.removeItem("authToken");
});
await page.goto("/admin/documents");

// Dopo (crea nuova pagina senza token)
const newPage = await page.context().newPage();
await newPage.goto("/admin/documents");
await expect(newPage).toHaveURL(/\/login/);
```

#### 3. Scenario 5: Timeout Combobox
**Error**: `getByRole('combobox').nth(1)` timeout

**Root Cause**:
- Select components caricano async
- Test non aspetta rendering completo

**Fix**:
```typescript
// Prima (assume caricamento immediato)
await page.getByRole("combobox").nth(1).click();

// Dopo (aspetta caricamento)
await page.waitForSelector('[role="combobox"]', { timeout: 5000 });
const comboboxes = page.getByRole("combobox");
await expect(comboboxes).toHaveCount(2);
await comboboxes.nth(1).click();
```

---

## Fixes Applied

### File: `apps/web/tests/story-4.4.spec.ts`

**Changes**:
1. Scenario 1: Cambiato `getByText()` → `getByRole("columnheader")`
2. Scenario 6: Usato `newPage()` context invece di `addInitScript()`
3. Scenario 5: Aggiunto `waitForSelector()` prima di interagire con combobox

---

## Next Action

**Re-run E2E Tests**:
```bash
cd apps/web
pnpm test:e2e tests/story-4.4.spec.ts
```

**Expected**: 6/6 PASSED
