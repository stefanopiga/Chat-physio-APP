# Sezione 10: Sicurezza e Performance

*   **Sicurezza**:
    *   **Autenticazione e Autorizzazione**: Delegate a `Supabase Auth` e `Row-Level Security (RLS)`. Il backend utilizzerà esclusivamente la `service_role_key` per operazioni amministrative (es. ingestione) che richiedono di bypassare le policy RLS, mentre il frontend opererà con la `anon_key` pubblica, soggetta alle restrizioni di sicurezza.
    *   **Sicurezza dell'Infrastruttura**: L'accesso al VPS deve essere configurato in modo sicuro, consentendo esclusivamente l'autenticazione tramite chiave SSH e disabilitando il login diretto dell'utente `root`.
    *   **Sicurezza Web**: Implementazione di CSP, CORS restrittivi, e input validation.
    *   **Variabili d'Ambiente (Auth/JWT)**:
        - `SUPABASE_URL`: base URL del progetto (necessaria per PostgREST).
        - `SUPABASE_ANON_KEY`: chiave pubblica per chiamate dal frontend e test cURL.
        - `SUPABASE_JWT_SECRET`: chiave server-side per firma/validazione del token temporaneo.
        - `SUPABASE_JWT_ISSUER` (opzionale): di default `https://<ref>.supabase.co/auth/v1`.
        - `TEMP_JWT_EXPIRES_MINUTES` (opz.): durata token temporaneo (default 15).
        - `USER_ACCESS_TOKEN` (test): token utente per verifiche RLS sui test PostgREST.
    *   **Target di Sicurezza (Story 2.1)**:
        - Nessun secret hardcoded nel repository; tutte le chiavi via variabili d'ambiente.
        - Rate limiting abilitato sugli endpoint di autenticazione/sensitive (es. `exchange-code`).
        - Ingestion service non esposto pubblicamente; esecuzione solo server-side.
*   **Rate Limiting per Endpoint Admin (Story 2.4) e Chat (Story 3.1)**:
        - **Obiettivo**: Proteggere gli endpoint amministrativi che avviano processi intensivi (es. indicizzazione conoscenza) da abusi e burst traffic.
        - **Strategia**: Token Bucket con soglia per IP/cliente.
        - **Parametri iniziali**: 30 richieste/minuto con burst massimo 10 (valori indicativi, da calibrare in base al carico reale). Per `/chat/query` limite applicativo 60/min.
        - **Ambito**: Applicato a `POST /admin/knowledge-base/sync-jobs`, `GET /admin/knowledge-base/sync-jobs/{jobId}` e `POST /chat/query`. Testato con scenario negativo 429 su `/api/v1/chat/query`. [Fonti: `apps/api/tests/test_chat_query.py`]
        - **Note di implementazione**: Enforcement lato API Gateway/Reverse Proxy (es. NGINX `limit_req`) e/o middleware applicativo. Loggare eventi di throttling per monitoraggio.
        - **Riferimento**: Necessità emersa nell'NFR Assessment della Story 2.4 (`docs/qa/assessments/2.4-nfr-20250923.md`).
*   **Performance**:
    *   **Frontend**: Implementazione di una strategia di ottimizzazione completa che include: **code splitting** per route, **lazy loading** per componenti non critici, **virtualizzazione** per la lista dei messaggi della chat e **compressione delle immagini** (se applicabile).
    *   **Backend**: Query del database ottimizzate con indici vettoriali, esecuzione asincrona. Per `/chat/query`, target p95 < 500ms (vedi Story 3.1 NFR).
    *   **Osservabilità Chat AG (Story 3.2)**: l'endpoint `POST /api/v1/chat/sessions/{sessionId}/messages` emette log `ag_metrics` con `latency_ms`, `p95_ms` e `samples` basati su finestra scorrevole in‑process. Obiettivo: monitorare regressioni e rispettare target p95 < 500ms.
    *   **Target di Performance (Story 2.1)**:
        - Ingestion: estrazione testo `.txt/.pdf/.docx` completata senza errori su documenti standard; logging strutturato per tempi di elaborazione.
        - Obiettivo: misurare tempo di elaborazione per file ed evidenziare regressioni nelle pipeline successive.

---


*   **Rate Limiting e Logging per Endpoint Pubblico (Story 1.3)**:
    *   **Endpoint**: `POST /api/v1/auth/exchange-code`.
    *   **Strategia RL**: per-IP, finestra e soglia configurabili via variabili d'ambiente.
    *   **Logging**: log strutturati JSON per tentativi/esiti dello scambio codice e richieste HTTP.
    *   **Riferimenti**: `docs/qa/assessments/po-master-check-20250913.md` L110–L112; `docs/qa/assessments/po-master-check-20250924.md` L55–L57.

---

## Security Standards Compliance

*   **JWT Security (RFC 8725, RFC 7519, RFC 9068)**:
    *   **Whitelist Algoritmi**: Backend supporta esclusivamente `HS256` (RFC 8725 Sezione 3.1). Vietato accettare `alg: none` senza validazione esplicita. PyJWT configuration: `algorithms=["HS256"]` parametro obbligatorio in `jwt.decode()`.
    *   **Claims Temporali**: Validazione obbligatoria `exp` (expiration) e `iat` (issued at) tramite `options={"require": ["exp", "iat"]}`. RFC 7519: "The current time MUST be before the time represented by the 'exp' claim".
    *   **Clock Skew Tolerance**: Tolleranza ±2 minuti (120 secondi) su validazione `exp`/`nbf` per gestire desincronizzazioni NTP (RFC 7519: "usually no more than a few minutes"). PyJWT: `options={"leeway": 120}`.
    *   **OAuth 2.0 Error Codes**: Conformità RFC 6749 Sezione 5.2: `invalid_grant` per refresh token invalid/expired/revoked, `invalid_request` per parametri malformati.
    *   **Environment Variables**: `CLOCK_SKEW_LEEWAY_SECONDS` (default: 120), `SUPABASE_JWT_SECRET`, `SUPABASE_JWT_ISSUER`, `TEMP_JWT_EXPIRES_MINUTES` (default: 15).

*   **Cookie Security (RFC 6265, RFC 6265bis, OWASP)**:
    *   **HttpOnly Attribute** (RFC 6265 Sezione 4.1.2.6): Protegge confidenzialità refresh token, previene lettura via `document.cookie`. **Limitazione critica**: XSS può inviare richieste autenticate on-the-fly con cookie auto-incluso dal browser (fetch + credentials: 'include'). Mitigazione primaria XSS: output encoding context-aware (OWASP XSS Prevention).
    *   **Secure Attribute** (RFC 6265 Sezione 4.1.2.5): Forza trasmissione cookie solo su HTTPS, previene MITM su reti non sicure. Prerequisito: deployment con HTTPS obbligatorio (Traefik + Let's Encrypt).
    *   **SameSite=Strict** (RFC 6265bis, OWASP CSRF Prevention): Previene CSRF attacks, browser blocca cookie in richieste cross-site. **Limitazione**: browser legacy (<5% utenti) non supportano; XSS bypassa (richieste same-origin). Defense in depth: CSRF token pianificato Phase 2.
    *   **Path Attribute** (RFC 6265 Sezione 4.1.2.4): Scope restrictivo per ridurre cookie leakage. Esempio: refresh token `path="/api/v1/auth/refresh-token"`.
    *   **Implementation**: `response.set_cookie(httponly=True, secure=True, samesite="strict", path="/api/v1/auth/refresh-token", max_age=31536000)`.

*   **Rate Limiting Standards (OWASP Authentication Cheat Sheet)**:
    *   **Sliding Window Algorithm**: Algoritmo raccomandato produzione, più accurato di fixed window, previene burst al confine delle finestre temporali (Redis implementation).
    *   **Account-Based Limiting**: OWASP raccomandazione: "associate the counter of failed login with the account itself, rather than the source IP address" per prevenire attacchi da IP multipli. Pianificato Phase 2.
    *   **Configuration**: Lockout threshold (es. 10 richieste), observation window (es. 60 sec), lockout duration (es. 300 sec), exponential backoff per endpoint critici.
    *   **Endpoint-Specific Limits**: exchange-code (10 req/60 sec), refresh-token (60 req/1 ora), admin-create-token (10 req/1 ora), chat-query (60 req/1 min).

*   **Compliance Documentation**: Materiale dettagliato e checklist audit in `docs/architecture/addendum-security-standards-compliance.md`. Pattern riutilizzabili per implementazioni authentication/authorization progetto.