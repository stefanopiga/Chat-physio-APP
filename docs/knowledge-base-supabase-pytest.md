## Supabase Knowledge Base

### Autenticazione JWT
Riassunto: Supabase Auth usa JWT per autenticare gli utenti; i token di accesso hanno scadenza configurabile, i refresh token non scadono ma sono monouso. Le sessioni si gestiscono via `supabase.auth` (create/sign-in, get/refresh session, sign-out). Integrare con RLS tramite `auth.uid()`.

Snippet (Python: sign-in, session, refresh):
```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Email/password sign-in
auth_res = supabase.auth.sign_in_with_password({"email": "user@example.com", "password": "secret"})
session = auth_res.session  # access_token, refresh_token, user

# Get current session
current = supabase.auth.get_session()

# Refresh session (when access token expired)
refreshed = supabase.auth.refresh_session()
new_access = refreshed.session.access_token

# Sign out
supabase.auth.sign_out()
```

Note utili:
- Configura la scadenza degli access token nelle impostazioni Auth del progetto. Un refresh token è riutilizzabile una sola volta.
- Eventi di sessione disponibili nei client (platform specific) per reagire a SIGNED_IN/SIGNED_OUT.
- Riferimenti: `supabase.com/docs/guides/auth`, `.../guides/auth/jwts`, `.../reference/python/introduction` (sezione Auth).
### API PostgREST: Select e Insert
Riassunto: Il client espone PostgREST per CRUD su tabelle e viste. Usa `select()` per leggere con filtri, ordinamenti e paginazione; `insert()` per creare righe. I filtri seguono la sintassi PostgREST.

Snippet (Python: select con filtri, order, range):
```python
# Fetch specific columns with filters and ordering
resp = supabase.table("profiles").select("id,email,created_at")\
    .eq("role", "student")\
    .like("email", "%@domain.com")\
    .order("created_at", desc=True)\
    .range(0, 9)\
    .execute()
rows = resp.data
```

Snippet (Python: insert con returning):
```python
# Insert and return created rows
resp = supabase.table("access_codes").insert(
    [{"code": "ABC123", "expires_at": "2025-12-31T23:59:59Z"}],
    count="exact"
).select("*").execute()
created = resp.data
```

Note utili:
- `.filter(column, operator, value)` accetta operatori PostgREST quando i metodi dedicati non bastano.
- Paginazione con `.range(start, end)`.
- In REST puro: invia `Prefer: return=representation` per far restituire i record inseriti.

Snippet (cURL: select e insert):
```bash
# SELECT with filters and ordering
curl -s "${SUPABASE_URL}/rest/v1/profiles?role=eq.student&select=id,email,created_at&order=created_at.desc&limit=10" \
  -H "apikey: ${SUPABASE_ANON_KEY}" -H "Authorization: Bearer ${SUPABASE_ANON_KEY}"

# INSERT and return rows
curl -s "${SUPABASE_URL}/rest/v1/access_codes" \
  -H "apikey: ${SUPABASE_ANON_KEY}" -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" -H "Prefer: return=representation" \
  -d '[{"code":"ABC123","expires_at":"2025-12-31T23:59:59Z"}]'
```

Riferimenti: `supabase.com/docs/reference/python/select`, `.../insert`, PostgREST syntax nei client reference.
### Row-Level Security (RLS)
Riassunto: Abilita RLS sulla tabella e definisci policy per CRUD basate su `auth.uid()` o altri predicati. Usa clausole USING e WITH CHECK. Testa le policy con richieste autenticate.

SQL: abilitazione e policy CRUD tipica per owner:
```sql
alter table access_codes enable row level security;

-- Solo proprietario può SELECT
create policy "select_own" on access_codes
  for select using (user_id = auth.uid());

-- Solo proprietario può INSERT (assegnato in WITH CHECK)
create policy "insert_own" on access_codes
  for insert with check (user_id = auth.uid());

-- Solo proprietario può UPDATE
create policy "update_own" on access_codes
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Solo proprietario può DELETE
create policy "delete_own" on access_codes
  for delete using (user_id = auth.uid());
```

Test rapido con cURL (Bearer = access token dell’utente):
```bash
curl -s "${SUPABASE_URL}/rest/v1/access_codes?select=*" \
  -H "apikey: ${SUPABASE_ANON_KEY}" -H "Authorization: Bearer ${USER_ACCESS_TOKEN}"
```

Riferimenti: `supabase.com/docs/guides/auth` (integrazione con RLS), `.../guides/database` e policy guide; PostgREST policy evaluation.
## Pytest Knowledge Base

### Test di Integrazione con HTTP/ASGI
Riassunto: Per app ASGI (FastAPI), usa `TestClient` (sync) o esegui test async con `pytest.mark.anyio`. Se usi HTTPX, integra un client async e fixture per event loop.

Snippet (FastAPI TestClient sync):
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_healthcheck():
    r = client.get("/health")
    assert r.status_code == 200
```

Snippet (async test con anyio + httpx.AsyncClient):
```python
import pytest, httpx
from api.main import app
from asgi_lifespan import LifespanManager

@pytest.mark.anyio
async def test_create_code():
    async with LifespanManager(app):
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post("/access-codes", json={"code":"ABC123"})
            assert resp.status_code == 201
```

Note utili:
- Per test async, marca con `@pytest.mark.anyio`. Gestisci startup/shutdown dell’app.
- Usa fixture per creare il client una volta per modulo/sessione.

Riferimenti: `fastapi.tiangolo.com/advanced/async-tests/`, `.../reference/testclient/`.
### Fixture Pytest
Riassunto: Le fixture gestiscono setup/teardown, scopi multipli, dipendenze tra fixture, parametrizzazione.

Snippet (fixture client riutilizzabile):
```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_get_codes(client):
    r = client.get("/access-codes")
    assert r.status_code == 200
```

Riferimenti: `docs.pytest.org/.../how-to/fixtures.html`, `.../reference/fixtures.html`.
### Monkeypatch e Mocking Dipendenze Esterne
Riassunto: Usa `monkeypatch.setattr`/`delenv`/`setenv` per sostituire funzioni, variabili d’ambiente o attributi; tutto è ripristinato a fine test. Per HTTP esterni, monkeypatch su funzioni wrapper o usa librerie specializzate (se consentite).

Snippet (mock funzione HTTP):
```python
import pytest
import app.services as services

def fake_verify_jwt(token: str):
    return {"sub": "user-123"}

def test_auth_guard(monkeypatch):
    monkeypatch.setattr(services, "verify_jwt", fake_verify_jwt)
    claims = services.verify_jwt("any")
    assert claims["sub"] == "user-123"
```

Snippet (env vars):
```python
def test_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://localhost")
    monkeypatch.delenv("UNUSED_VAR", raising=False)
```

Riferimenti: `docs.pytest.org/.../how-to/monkeypatch.html`.
### Dati Temporanei e FS
Riassunto: Usa `tmp_path`/`tmp_path_factory` per filesystem isolato nei test di integrazione.

Snippet:
```python
def test_write_tmp(tmp_path):
    p = tmp_path / "out.json"
    p.write_text('{"ok": true}')
    assert p.read_text().startswith("{")
```

Riferimenti: `docs.pytest.org/.../how-to/tmp_path.html`.
