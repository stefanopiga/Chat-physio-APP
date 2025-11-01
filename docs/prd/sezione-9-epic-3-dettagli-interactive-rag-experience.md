# Sezione 9: Epic 3 Dettagli - Interactive RAG Experience

**Goal dell'Epic**: Abilitare l'interfaccia di chat per gli studenti, collegandola alla pipeline di conoscenza per fornire risposte, visualizzare le fonti e raccogliere feedback, completando il flusso di valore end-to-end.

#### **Story 3.1: Semantic Search Endpoint**
*   **As a** Sviluppatore Backend, **I want** un endpoint per eseguire una ricerca di similarità, **so that** possiamo recuperare i chunk pertinenti.
**Acceptance Criteria:** 1. Endpoint `/api/v1/chat/query` protetto. 2. La domanda viene convertita in embedding. 3. Esegue query di similarità su Supabase. 4. Restituisce i top N chunk.

#### **Story 3.2: Augmented Generation Endpoint**
*   **As a** Sviluppatore Backend, **I want** un endpoint che usi un LLM per generare una risposta contestualizzata, **so that** l'utente riceva una risposta utile basata sulle fonti.
**Acceptance Criteria:** 1. Prompt ingegnerizzato per rispondere solo dal contesto e citare fonti. 2. L'endpoint riceve domanda e chunk. 3. Invoca l'LLM. 4. Restituisce la risposta con citazioni. 5. Gestisce la memoria a breve termine.

#### **Story 3.3: Frontend Chat Integration**
*   **As a** Sviluppatore Frontend, **I want** collegare la UI della chat agli endpoint, **so that** gli studenti possano avere una conversazione fluida.
**Acceptance Criteria:** 1. La UI chiama l'endpoint `/api/v1/chat/query`. 2. Mostra un indicatore di caricamento. 3. Visualizza la risposta. 4. Mantiene la cronologia della sessione con `sessionId` persistito lato client (es. `localStorage`, chiave `chat.sessionId`).

**E2E Prerequisiti & Linee guida**
- Per rotte protette (`AuthGuard`), impostare credenziali fittizie prima di `goto`:
```ts
await page.addInitScript(() => {
  localStorage.setItem("chat.sessionId", "e2e-session-id");
  sessionStorage.setItem("temp_jwt", "e2e-temp-token");
});
await page.goto("/chat");
```
- Attendere sblocco di `AuthGuard`:
```ts
await expect(page.getByText("Verifica autenticazione...")).not.toBeVisible({ timeout: 10000 });
```
- Attendere visibilità input e abilitazione submit, poi validare loader off:
```ts
const input = page.getByPlaceholder("Inserisci la tua domanda...");
await expect(input).toBeVisible({ timeout: 10000 });
const submit = page.getByRole("button", { name: "Invia" });
await expect(submit).toBeEnabled();
await submit.click();
await expect(page.getByText("Caricamento...")).not.toBeVisible({ timeout: 10000 });
```

#### **Story 3.4: Source Visualization & Feedback**
*   **As a** Sviluppatore Frontend, **I want** implementare la visualizzazione delle fonti e il feedback, **so that** gli studenti possano verificare le info e noi possiamo misurare la qualità.
**Acceptance Criteria:** 1. Le citazioni sono interattive. 2. Al click/hover mostrano un popover con la fonte. 3. Pulsanti 👍/👎 presenti. 4. Il feedback viene inviato e registrato.

#### **Story 3.5: In-App User Guide**
*   **As a** Studente, **I want** accedere a una semplice guida all'interno dell'applicazione, **so that** posso capire rapidamente come usare la chat, interpretare le fonti e fornire feedback.
*   **Acceptance Criteria:** 1. Un'icona "Aiuto" (?) è visibile e accessibile nell'interfaccia della chat. 2. Cliccando sull'icona si apre una finestra modale con la guida. 3. La guida spiega in modo conciso: a) come porre domande, b) come funzionano le citazioni interattive delle fonti, c) lo scopo dei pulsanti di feedback. 4. La guida è scritta in un linguaggio chiaro e semplice.

---
