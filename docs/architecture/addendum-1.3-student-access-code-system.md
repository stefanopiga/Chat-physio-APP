# Addendum Architettura — Story 1.3: Student Access Code System

Data: 2025-09-12
Fonti: `docs/qa/assessments/1.3-test-design-20250912.md`, `docs/qa/assessments/1.3-student-access-code-system-trace-20250912.md`, `docs/qa/gates/1.3-student-access-code-system.yml`, `docs/stories/1.3.student-access-code-system.md`, specifiche fornite (Supabase Docs: JWTs, JWT fields; FastAPI Tutorial OAuth2+JWT; Supabase RLS)

## 1) Modelli Dati Coinvolti
- `AccessCode` (già definito): `id`, `code`, `is_active`, `expires_at`, `usage_count`, `last_used_at`, `created_by_id`, `created_at`, `updated_at`. (Fonte: story/trace)

## 2) Flusso di Generazione e Validazione (Overview)
1. Admin genera `AccessCode` (interfaccia admin, endpoint protetto). (Fonti: story, trace)
2. Utente inserisce codice in UI pubblica, richiesta di validazione. (Fonti: story, test-design)
3. Se valido/attivo/non scaduto, sistema restituisce un “token temporaneo” (JWT). (Fonti: story, trace)

Endpoint pubblico previsto: `POST /api/v1/auth/exchange-code` (vedi sezione 4). (Fonte: specifiche fornite)

### Best Pattern (JWT/RLS & flussi)
- Verifica JWT e RLS avvengono lato Supabase tramite i claim del token e le policy. Token esterni sono accettati se validati e coerenti con i claim. [Supabase: JWTs](https://supabase.com/docs/guides/auth/jwts)
- Pattern a confronto:
  - Frontend → FastAPI → Supabase DB: FastAPI emette/valida token e media l’accesso; Supabase applica RLS sui claim. [Supabase: JWTs](https://supabase.com/docs/guides/auth/jwts)
  - Frontend → Supabase Edge Function: le Edge Functions verificano JWT e invocano DB con RLS. [Supabase: Edge Functions](https://supabase.com/docs/guides/functions)
- Scelta: mantenere `service_role_key` solo nel backend; non esporla nel frontend; usare RLS per enforcement. [Supabase: Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

## 3) Token temporaneo (JWT)
- Issuer (`iss`): `https://<project-ref>.supabase.co/auth/v1` (pattern Supabase). [Supabase: JWTs](https://supabase.com/docs/guides/auth/jwts)
- Audience (`aud`): tipicamente `"authenticated"` (oppure `"anon"`). [Supabase: JWT fields](https://supabase.com/docs/guides/auth/jwt-fields)
- Claims minimi: `iss`, `aud`, `sub`, `role`, `session_id`, `iat`, `exp`. [Supabase: JWT fields](https://supabase.com/docs/guides/auth/jwt-fields)
- Algoritmo (esempio tutorial FastAPI): `HS256`. [FastAPI: OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- Durata esempio: 15 minuti. [FastAPI: OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

Esempio generazione JWT (FastAPI + PyJWT) — estratto conforme al tutorial FastAPI:
```python
from datetime import datetime, timedelta, timezone
import jwt

SECRET_KEY = "sostituisci_con_chiave_sicura"
ALGORITHM = "HS256"

def generate_temp_jwt(subject: str, session_id: str, issuer: str, audience: str, minutes: int = 15) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "role": "authenticated",
        "session_id": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```
(Fonti: specifiche fornite)

## 4) API — Exchange Code
- Metodo/Path: `POST /api/v1/auth/exchange-code` (pubblico)
- Request (JSON):
```json
{
  "access_code": "string"
}
```
- Response 200 (JSON):
```json
{
  "token": "jwt-string",
  "token_type": "bearer",
  "expires_in": 900
}
```
- Errori (etichette esemplificative; testi esatti non in fonte): 400 `invalid_request`, 401 `invalid_code`, 410 `expired_code`, 409 `code_already_used`, 429 `rate_limited`
- Riferimenti: [FastAPI: OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
(Fonti: specifiche fornite)

## 5) Sicurezza & RLS (Supabase)
- Service Role: la `service_role_key` bypassa RLS e va usata solo lato server (mai nel frontend). [Supabase: RLS](https://supabase.com/docs/guides/auth/row-level-security)
- Default deny: con RLS attivo l’accesso è negato finché non esistono policy. [Supabase: RLS](https://supabase.com/docs/guides/auth/row-level-security)
- Policy di esempio (admin via `app_metadata.role = 'admin'`):
```sql
alter table public.access_code enable row level security;

create policy "access_code_select_admin"
on public.access_code
for select
to authenticated
using (
  (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
);

create policy "access_code_insert_admin"
on public.access_code
for insert
to authenticated
with check (
  (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
);

create policy "access_code_update_admin"
on public.access_code
for update
to authenticated
using (
  (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
)
with check (
  (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
);

create policy "access_code_delete_admin"
on public.access_code
for delete
to authenticated
using (
  (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
);
```
(Note: struttura di `app_metadata` e ruoli dipendono dalla configurazione del progetto — valori esatti non presenti nella fonte)

## 6) Testing & Qualità (riepilogo)
- P0 su contract/security per generazione/validazione e redirect E2E. (Fonte: test-design)
- Gap residui: messaggi di errore specifici non definiti nelle fonti. (Fonti: specifiche fornite)

## 7) Prossimi Passi
- Allineare la story 1.3 con i dettagli di questa sezione (issuer/audience/claims/durata, endpoint API, note RLS).
- Aggiornare test design con asserzioni sul token (durata/claims) e sugli esiti di errore.
- Rieseguire review QA e aggiornare il gate.
