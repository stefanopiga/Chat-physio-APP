# Sezione 11: Strategia di Testing

*   **Piramide dei Test**:
    *   **Unit Tests**: `Vitest` (FE) e `Pytest` (BE).
    *   **Integration Tests**: `React Testing Library` (FE) e `Pytest`+`HTTPX` (BE).
    *   **E2E Tests**: `Playwright` per i flussi critici.
*   **LLM Evals**:
    *   **Strategia**: Uso di un "golden dataset" e di un framework come `Ragas` per misurare la qualità (Faithfulness, Relevancy) delle risposte del sistema RAG e prevenire regressioni. Questo processo sarà potenziato da strumenti di tracciamento e debugging come `LangSmith` (dall'ecosistema LangChain) per analizzare nel dettaglio ogni passaggio della catena RAG.
*   **Mocking dei Servizi Esterni**: Tutte le chiamate a servizi esterni (LLM, Embedding API) saranno mockate durante i test per garantire esecuzioni deterministiche, veloci e indipendenti dalla disponibilità della rete. Questo approccio abilita anche uno sviluppo offline efficace.

## Pratiche di Testing Dettagliate (dal Knowledge Base)

### Backend (Pytest + HTTPX)
- Usare test async con `@pytest.mark.anyio` e `httpx.AsyncClient(app=app, base_url="http://test")`.
- Gestire correttamente startup/shutdown con `asgi_lifespan.LifespanManager(app)`.
- Definire fixture client riutilizzabile con scope `module` per ridurre overhead.
- Validare il contratto `POST /api/v1/auth/exchange-code` (happy/negative) e i claim JWT minimi (`iss`, `aud`, `exp`).
- Per PostgREST e RLS: inviare `Authorization: Bearer ${USER_ACCESS_TOKEN}` nei test di policy.
- Per dipendenze esterne, usare `monkeypatch` su funzioni wrapper (es. verifica JWT), evitando chiamate reali.
 - Esecuzione: preferire `poetry run pytest` per garantire allineamento delle dipendenze; evitare `python -m pytest` su interprete di sistema non isolato.
 - Endpoint Chat: aggiungere test per `POST /api/v1/chat/query` con mocking di embeddings e vector store; validare parametri `match_count` e risposta con top N. Aggiungere test negativi: 401 (token mancante/invalid) e 429 (rate limited). [Fonti: `apps/api/tests/test_chat_query.py`]

### Frontend (Vitest + React Testing Library)
- Testare validazione del campo codice: submit bloccato se vuoto, messaggio di errore specifico.
- Mockare la risposta API e verificare redirect a `/chat` su codice valido.

### End-to-End (Playwright)
- Scenario felice: inserimento codice valido → redirect `/chat`.
- Scenari negativi: codice invalido/scaduto/disattivato → messaggio di errore specifico.

#### Linee guida pratiche FE E2E (AuthGuard/AdminGuard)
- Rotte protette (`AuthGuard`): impostare credenziali fittizie prima di `goto`.
```ts
await page.addInitScript(() => {
  localStorage.setItem("chat.sessionId", "e2e-session-id");
  sessionStorage.setItem("temp_jwt", "e2e-temp-token");
});
await page.goto("/chat");
```
- Attendere sblocco di `AuthGuard` prima di interagire.
```ts
await expect(page.getByText("Verifica autenticazione...")).not.toBeVisible({ timeout: 10000 });
```
- Selettori resilienti e attese su elementi lenti.
```ts
const input = page.getByPlaceholder("Inserisci la tua domanda...");
await expect(input).toBeVisible({ timeout: 10000 });
```
- Submit reattivo: attendere il bottone abilitato.
```ts
const submit = page.getByRole("button", { name: "Invia" });
await expect(submit).toBeEnabled();
```
- Post-condizione: loader spento.
```ts
await expect(page.getByText("Caricamento...")).not.toBeVisible({ timeout: 10000 });
```
- Rotte admin (`AdminGuard`): verificare redirect asincrono.
```ts
await page.goto("/admin/dashboard");
await page.waitForURL("/", { timeout: 10000 });
await expect(page.getByRole("heading", { name: /Accesso Studente/i })).toBeVisible();
```

---

## Metriche di Qualità del Codice

- **Code Coverage (Policy Ufficiale)**: Target minimo dell'80% per tutto il nuovo codice (FE e BE).
- **Enforcement CI/CD**: La pipeline misurerà automaticamente il coverage; il mancato rispetto del target bloccherà la merge.
- **Ambito**: Il requisito si applica a PR che introducono nuove funzionalità o modifiche sostanziali; eccezioni devono essere motivate e approvate nel contesto della review tecnica.

### Piani specifici: Story 1.3 — Exchange Code

- Backend (Pytest + HTTPX): usare test async con `httpx.AsyncClient` e `asgi_lifespan.LifespanManager(app)`; validare contratto `POST /api/v1/auth/exchange-code` (happy/negative) e claims minimi `iss`, `aud`, `exp`; fixture client riutilizzabile (scope `module`); mock dipendenze esterne con `monkeypatch`; per test RLS via PostgREST usare header `Authorization: Bearer ${USER_ACCESS_TOKEN}`.
[Fonti: `docs/qa/assessments/po-master-check-20250913.md` L121–L128]
- Frontend (Vitest + RTL): validazione campo vuoto con messaggio specifico; redirect a `/chat` su codice valido (mock risposta API).
[Fonti: `docs/qa/assessments/po-master-check-20250913.md` L129–L132]
- E2E (Playwright): scenario felice (codice valido → redirect `/chat`); scenari negativi (codice invalido/scaduto/disattivato → messaggio errore specifico).
[Fonti: `docs/qa/assessments/po-master-check-20250913.md` L134–L135]
