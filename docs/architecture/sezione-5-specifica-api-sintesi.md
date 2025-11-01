# Sezione 5: Specifica API (Sintesi)

L'architettura sfrutta un approccio ibrido:
1.  **API di Supabase (PostgREST)**: Il frontend interagirà direttamente con le API auto-generate di Supabase per tutte le operazioni di **Autenticazione** e **CRUD sugli `AccessCode`**. La sicurezza è garantita da `Supabase Auth` e dalle policy di `Row-Level Security`.
2.  **API Custom (FastAPI)**: Un'API custom, più piccola e focalizzata, gestirà la logica di business complessa che non può essere auto-generata. Questa API è definita dal file `docs/api/openapi.yml`.

### Riepilogo `openapi.yml` (API Custom)
*   **Host**: `/api/v1`
*   **Sicurezza**: JWT Bearer Token (forniti da Supabase Auth)
*   **Endpoint Principali**:
*   `POST /chat/sessions/{sessionId}/messages`: Invia un messaggio e ottiene una risposta RAG. Stato attuale: implementato con catena LCEL (ChatPromptTemplate | ChatOpenAI | PydanticOutputParser). Output include `citations` arricchite per popover (`chunk_id`, `document_id`, `excerpt`, `position`). [Story 3.4]
    *   `POST /chat/messages/{messageId}/feedback`: Invia un feedback su un messaggio. Body `{ sessionId: string, vote: 'up'|'down' }`, risposta `{ ok: boolean }`. [Story 3.4]
    *   `POST /admin/knowledge-base/sync-jobs`: Avvia un processo di sincronizzazione.
    *   `GET /admin/knowledge-base/sync-jobs/{jobId}`: Controlla lo stato di un processo.
    *   `GET /health`: Endpoint pubblico per il monitoraggio dell'uptime.
    *   `POST /api/v1/auth/exchange-code`: Valida `access_code` e rilascia JWT temporaneo.
    *   `POST /chat/query`: Ricerca semantica (protetto, rate limited 60/min) — vedi Story 3.1.

> Nota stato: la rotta `POST /api/v1/chat/sessions/{sessionId}/messages` è implementata in `apps/api/api/main.py` con modelli `ChatMessageCreateRequest/Response`, auth runtime, rate limiting `60/min` e logging eventi `ag_message_request`, `ag_fallback` e `ag_metrics`. La logica RAG usa LCEL e restituisce risposta con citazioni arricchite per la visualizzazione (Story 3.4). Il modello dati LLM è definito in `apps/api/api/models/answer_with_citations.py`.

> Modello di generazione AG: `gpt-5-nano` (LangChain `ChatOpenAI`, temperature=0) come LLM post-embedding per produrre la risposta con citazioni. Metriche di performance: log `ag_metrics` con `latency_ms` e `p95_ms`. Riferimenti: `docs/stories/3.2.augmented-generation-endpoint.md` (LLM) e `docs/architecture/sezione-10-sicurezza-e-performance.md` (osservabilità).

### Esempi PostgREST (Access Codes)
```bash
# SELECT con filtri e ordine (prime 10 righe)
curl -s "$SUPABASE_URL/rest/v1/access_codes?is_active=eq.true&select=id,code,expires_at,usage_count&order=created_at.desc&limit=10" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY"

# INSERT con ritorno della riga creata
curl -s "$SUPABASE_URL/rest/v1/access_codes" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" -H "Prefer: return=representation" \
  -d '[{"code":"ABC123","expires_at":"2025-12-31T23:59:59Z"}]'
```

### Note RLS e Test
- Abilitare RLS su `access_codes` e definire policy per owner/admin secondo necessità.
- Per testare le policy via PostgREST, utilizzare `Authorization: Bearer ${USER_ACCESS_TOKEN}` nei test.
*   **Standard**: L'API segue un approccio "schema-first", con componenti riutilizzabili e risposte di errore standardizzate.

---


### Note su Sicurezza e Logging (Exchange Code)

- `POST /api/v1/auth/exchange-code`:
  - Rate limiting applicativo per-IP con parametri configurabili via env.
  - Log strutturati JSON per tentativi/esiti e richieste HTTP.
[Fonti: `docs/qa/assessments/po-master-check-20250913.md` L110–L112; `docs/qa/assessments/po-master-check-20250924.md` L55–L57]
