"""Test suite Story 1.3.1: Student Token Management System with Refresh Token Pattern.

Test coverage:
- Unit tests: token generation uniqueness
- Integration tests CRUD: create/list/delete student tokens
- Integration tests Refresh Token Pattern: exchange-code, refresh-token endpoint

Setup:
- Requires test database con migration 20251008000000_create_student_tokens_and_refresh.sql applicata
- Requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET in .env.test.local

Run:
    cd apps/api
    poetry run pytest tests/test_student_tokens.py -v
"""
import os
import secrets
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from supabase import create_client


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def supabase_test_client():
    """Supabase client per test database operations."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        pytest.skip("Supabase test environment not configured")
    
    return create_client(supabase_url, supabase_service_key)


# Story 5.4 Task 3.2: Removed duplicate student_token_in_db fixture
# Use fixture from conftest.py instead (with proper upsert for FK constraint)


@pytest.fixture
def refresh_token_in_db(supabase_test_client, student_token_in_db):
    """Crea refresh token di test in DB (setup + teardown)."""
    refresh_token = secrets.token_urlsafe(64)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=365)
    
    result = supabase_test_client.table("refresh_tokens").insert({
        "student_token_id": student_token_in_db["id"],
        "token": refresh_token,
        "expires_at": expires_at.isoformat(),
        "is_revoked": False,
    }).execute()
    
    created_refresh = result.data[0]
    
    yield created_refresh
    
    # Cleanup: revoke
    supabase_test_client.table("refresh_tokens").update({
        "is_revoked": True
    }).eq("id", created_refresh["id"]).execute()


# =============================================================================
# Unit Tests: Token Generation
# =============================================================================

def test_generate_student_token_uniqueness():
    """Test: student token generation produces unique 32-char tokens (256-bit entropy)."""
    tokens = set()
    
    for _ in range(1000):
        token = secrets.token_urlsafe(32)
        tokens.add(token)
    
    # Verifica: 1000 token generati, 1000 unici
    assert len(tokens) == 1000, "Student token generation non produce token unici"
    
    # Verifica: lunghezza token consistente (URL-safe base64 encoding)
    for token in tokens:
        assert len(token) >= 32, f"Token troppo corto: {len(token)} < 32"


def test_generate_refresh_token_uniqueness():
    """Test: refresh token generation produces unique 64-char tokens (512-bit entropy)."""
    tokens = set()
    
    for _ in range(1000):
        token = secrets.token_urlsafe(64)
        tokens.add(token)
    
    # Verifica: 1000 token generati, 1000 unici
    assert len(tokens) == 1000, "Refresh token generation non produce token unici"
    
    # Verifica: lunghezza token >= 64 (512-bit entropy)
    for token in tokens:
        assert len(token) >= 64, f"Refresh token troppo corto: {len(token)} < 64"


def test_create_student_token_request_validation():
    """Test: Pydantic validation CreateStudentTokenRequest (empty first_name, max_length)."""
    from pydantic import ValidationError
    from api.schemas.student_tokens import CreateStudentTokenRequest  # Story 5.4 Task 4.4
    
    # Test: first_name vuoto
    with pytest.raises(ValidationError) as exc_info:
        CreateStudentTokenRequest(first_name="", last_name="Rossi")
    
    assert "first_name" in str(exc_info.value), "Validation error deve menzionare first_name"
    
    # Test: last_name vuoto
    with pytest.raises(ValidationError) as exc_info:
        CreateStudentTokenRequest(first_name="Mario", last_name="")
    
    assert "last_name" in str(exc_info.value), "Validation error deve menzionare last_name"
    
    # Test: first_name troppo lungo (max_length 100)
    with pytest.raises(ValidationError):
        CreateStudentTokenRequest(first_name="A" * 101, last_name="Rossi")
    
    # Test: input valido
    valid_request = CreateStudentTokenRequest(first_name="Mario", last_name="Rossi")
    assert valid_request.first_name == "Mario"
    assert valid_request.last_name == "Rossi"


# =============================================================================
# Integration Tests: CRUD Endpoints
# =============================================================================

def test_create_student_token_success(test_client, admin_token_in_db, supabase_test_client):
    """Test: POST /api/v1/admin/student-tokens crea token con successo (201).
    
    Story 5.4.3 Fix: usa admin_token_in_db con UUID valido invece di admin_token
    per evitare errori 422 su validazione created_by_id.
    """
    response = test_client.post(
        "/api/v1/admin/student-tokens",
        json={"first_name": "Mario", "last_name": "Rossi"},
        headers={"Authorization": f"Bearer {admin_token_in_db['token']}"}
    )
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "id" in data
    assert "token" in data
    assert data["first_name"] == "Mario"
    assert data["last_name"] == "Rossi"
    assert "expires_at" in data
    
    # Verifica: token salvato in DB con created_by_id corretto (Story 5.4.3)
    db_result = supabase_test_client.table("student_tokens").select("*").eq("id", data["id"]).execute()
    assert len(db_result.data) == 1
    assert db_result.data[0]["token"] == data["token"]
    assert db_result.data[0]["is_active"] is True
    assert db_result.data[0]["created_by_id"] == admin_token_in_db["user_id"], "created_by_id deve essere admin UUID valido"
    
    # Cleanup: not needed, admin_token_in_db fixture cleanup will cascade delete


def test_create_student_token_unauthorized(test_client):
    """Test: POST /api/v1/admin/student-tokens senza JWT → 401."""
    response = test_client.post(
        "/api/v1/admin/student-tokens",
        json={"first_name": "Mario", "last_name": "Rossi"}
    )
    
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


def test_create_student_token_forbidden_non_admin(test_client):
    """Test: POST /api/v1/admin/student-tokens con JWT non-admin → 403."""
    # Generate JWT con role="authenticated" (non admin)
    import jwt
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not jwt_secret:
        pytest.skip("SUPABASE_JWT_SECRET non configurato")
    
    payload = {
        "sub": "test-user-id",
        "role": "authenticated",  # NO app_metadata.role = "admin"
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "iss": os.getenv("SUPABASE_JWT_ISSUER", "test"),
    }
    
    non_admin_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    
    response = test_client.post(
        "/api/v1/admin/student-tokens",
        json={"first_name": "Mario", "last_name": "Rossi"},
        headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"


def test_list_student_tokens_filtered(test_client, admin_token, student_token_in_db, supabase_test_client):
    """Test: GET /api/v1/admin/student-tokens filtra per is_active."""
    # Test: lista token attivi
    response = test_client.get(
        "/api/v1/admin/student-tokens?is_active=true",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Verifica: student_token_in_db presente (is_active=true)
    active_ids = [token["id"] for token in data]
    assert student_token_in_db["id"] in active_ids
    
    # Soft delete token
    supabase_test_client.table("student_tokens").update({
        "is_active": False
    }).eq("id", student_token_in_db["id"]).execute()
    
    # Test: lista token attivi (non deve includere token revocato)
    response = test_client.get(
        "/api/v1/admin/student-tokens?is_active=true",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    data = response.json()
    active_ids_after_revoke = [token["id"] for token in data]
    assert student_token_in_db["id"] not in active_ids_after_revoke


def test_delete_student_token_soft_delete(test_client, admin_token, student_token_in_db, supabase_test_client):
    """Test: DELETE /api/v1/admin/student-tokens/{id} soft delete + cascade revoke refresh tokens."""
    # Crea refresh token associato
    refresh_token = secrets.token_urlsafe(64)
    supabase_test_client.table("refresh_tokens").insert({
        "student_token_id": student_token_in_db["id"],
        "token": refresh_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "is_revoked": False,
    }).execute()
    
    # DELETE endpoint
    response = test_client.delete(
        f"/api/v1/admin/student-tokens/{student_token_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"
    
    # Verifica: student token soft deleted (is_active=false)
    db_result = supabase_test_client.table("student_tokens").select("*").eq("id", student_token_in_db["id"]).execute()
    assert db_result.data[0]["is_active"] is False
    
    # Verifica: refresh tokens revocati (is_revoked=true)
    refresh_result = supabase_test_client.table("refresh_tokens").select("*").eq("student_token_id", student_token_in_db["id"]).execute()
    for refresh in refresh_result.data:
        assert refresh["is_revoked"] is True, "Refresh tokens non revocati dopo soft delete student token"


def test_delete_student_token_not_found(test_client, admin_token):
    """Test: DELETE /api/v1/admin/student-tokens/{id} con id inesistente → 404."""
    fake_uuid = "00000000-0000-0000-0000-999999999999"
    
    response = test_client.delete(
        f"/api/v1/admin/student-tokens/{fake_uuid}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"


# =============================================================================
# Integration Tests: Refresh Token Pattern
# =============================================================================

def test_exchange_code_with_student_token(test_client, student_token_in_db, supabase_test_client):
    """Test: POST /api/v1/auth/exchange-code con student token → access token JWT 15 min + cookie refresh_token."""
    response = test_client.post(
        "/api/v1/auth/exchange-code",
        json={"access_code": student_token_in_db["token"]}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "token" in data  # ExchangeCodeResponse usa "token" (non "access_token")
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900  # 15 minuti
    
    # Verifica: JWT access token con exp 15 minuti
    import jwt
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if jwt_secret:
        decoded = jwt.decode(data["token"], jwt_secret, algorithms=["HS256"], audience="authenticated", options={"verify_exp": False})
        assert "exp" in decoded
        assert "iat" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        duration_minutes = (exp_time - iat_time).total_seconds() / 60
        assert 14 <= duration_minutes <= 16, f"JWT duration {duration_minutes} min, expected ~15 min"
    
    # Verifica: cookie refresh_token impostato
    assert "set-cookie" in response.headers, "Cookie refresh_token non impostato"
    cookie_header = response.headers["set-cookie"]
    assert "refresh_token=" in cookie_header, "Cookie refresh_token assente"
    assert "HttpOnly" in cookie_header, "Cookie HttpOnly attribute mancante"
    assert "SameSite=Strict" in cookie_header or "SameSite=strict" in cookie_header, "Cookie SameSite attribute mancante"
    
    # Verifica: refresh token salvato in DB
    refresh_result = supabase_test_client.table("refresh_tokens").select("*").eq("student_token_id", student_token_in_db["id"]).execute()
    assert len(refresh_result.data) > 0, "Refresh token non salvato in DB"
    assert refresh_result.data[0]["is_revoked"] is False


def test_exchange_code_with_access_code(test_client):
    """Test: POST /api/v1/auth/exchange-code con access code (Story 1.3) → JWT 15 min, NO refresh token."""
    # Questo test verifica comportamento invariato Story 1.3 (access code temporanei)
    # Richiede setup access code in-memory store (fuori scope test student token)
    # Placeholder: test skipped se access code non disponibile in fixture
    pytest.skip("Access code test richiede fixture access_code_store (Story 1.3)")


def test_exchange_code_with_expired_student_token(test_client, supabase_test_client):
    """Test: POST /api/v1/auth/exchange-code con student token scaduto → 410."""
    import uuid
    
    # Crea user di test per FK constraint con unique ID (Story 5.4.2)
    test_user_id = str(uuid.uuid4())
    user_result = supabase_test_client.table("users").insert({
        "id": test_user_id,
        "email": f"test-expired-{test_user_id[:8]}@fisiorag.test",
        "role": "admin",
    }).execute()
    
    # Verify user created
    assert user_result.data, "User creation failed"
    
    # Crea student token scaduto
    token = secrets.token_urlsafe(32)
    expired_at = datetime.now(timezone.utc) - timedelta(days=1)  # Scaduto 1 giorno fa
    
    result = supabase_test_client.table("student_tokens").insert({
        "first_name": "Expired",
        "last_name": "User",
        "token": token,
        "expires_at": expired_at.isoformat(),
        "is_active": True,
        "created_by_id": test_user_id,
    }).execute()
    
    created_id = result.data[0]["id"]
    
    response = test_client.post(
        "/api/v1/auth/exchange-code",
        json={"access_code": token}
    )
    
    assert response.status_code == 410, f"Expected 410, got {response.status_code}"
    assert "expired" in response.text.lower()
    
    # Cleanup (child → parent order)
    try:
        supabase_test_client.table("student_tokens").delete().eq("id", created_id).execute()
        supabase_test_client.table("users").delete().eq("id", test_user_id).execute()
    except Exception:
        pass


def test_exchange_code_with_revoked_student_token(test_client, supabase_test_client):
    """Test: POST /api/v1/auth/exchange-code con student token revocato (is_active=false) → 401."""
    import uuid
    
    # Crea user di test per FK constraint con unique ID (Story 5.4.2)
    test_user_id = str(uuid.uuid4())
    user_result = supabase_test_client.table("users").insert({
        "id": test_user_id,
        "email": f"test-revoked-{test_user_id[:8]}@fisiorag.test",
        "role": "admin",
    }).execute()
    
    # Verify user created
    assert user_result.data, "User creation failed"
    
    # Crea student token revocato
    token = secrets.token_urlsafe(32)
    
    result = supabase_test_client.table("student_tokens").insert({
        "first_name": "Revoked",
        "last_name": "User",
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "is_active": False,  # REVOCATO
        "created_by_id": test_user_id,
    }).execute()
    
    created_id = result.data[0]["id"]
    
    response = test_client.post(
        "/api/v1/auth/exchange-code",
        json={"access_code": token}
    )
    
    # NOTA: Query Supabase con .eq("is_active", True) non ritorna token revocato
    # Exchange-code fallisce con 401 invalid_code (nessun match)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    # Cleanup (child → parent order)
    try:
        supabase_test_client.table("student_tokens").delete().eq("id", created_id).execute()
        supabase_test_client.table("users").delete().eq("id", test_user_id).execute()
    except Exception:
        pass


def test_refresh_token_success(test_client, refresh_token_in_db, supabase_test_client):
    """Test: POST /api/v1/auth/refresh-token con cookie valido → nuovo access token + last_used_at aggiornato."""
    # Imposta cookie refresh_token nella richiesta
    test_client.cookies.set("refresh_token", refresh_token_in_db["token"])
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    
    # Verifica: last_used_at aggiornato in DB
    refresh_result = supabase_test_client.table("refresh_tokens").select("*").eq("id", refresh_token_in_db["id"]).execute()
    assert refresh_result.data[0]["last_used_at"] is not None, "last_used_at non aggiornato"
    
    # Clear cookie per altri test
    test_client.cookies.clear()


def test_refresh_token_missing_cookie(test_client):
    """Test: POST /api/v1/auth/refresh-token senza cookie → 400 missing_refresh_token."""
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert "missing_refresh_token" in response.text.lower()


def test_refresh_token_invalid(test_client):
    """Test: POST /api/v1/auth/refresh-token con cookie non in DB → 401 invalid_refresh_token."""
    fake_refresh_token = secrets.token_urlsafe(64)
    test_client.cookies.set("refresh_token", fake_refresh_token)
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert "invalid" in response.text.lower() or "revoked" in response.text.lower()
    
    test_client.cookies.clear()


def test_refresh_token_revoked(test_client, refresh_token_in_db, supabase_test_client):
    """Test: POST /api/v1/auth/refresh-token con cookie revocato (is_revoked=true) → 401."""
    # Revoca refresh token
    supabase_test_client.table("refresh_tokens").update({
        "is_revoked": True
    }).eq("id", refresh_token_in_db["id"]).execute()
    
    test_client.cookies.set("refresh_token", refresh_token_in_db["token"])
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    test_client.cookies.clear()


def test_refresh_token_expired(test_client, supabase_test_client, student_token_in_db):
    """Test: POST /api/v1/auth/refresh-token con cookie scaduto (expires_at < now) → 410."""
    # Crea refresh token scaduto
    expired_refresh_token = secrets.token_urlsafe(64)
    expired_at = datetime.now(timezone.utc) - timedelta(days=1)
    
    result = supabase_test_client.table("refresh_tokens").insert({
        "student_token_id": student_token_in_db["id"],
        "token": expired_refresh_token,
        "expires_at": expired_at.isoformat(),
        "is_revoked": False,
    }).execute()
    
    created_id = result.data[0]["id"]
    
    test_client.cookies.set("refresh_token", expired_refresh_token)
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 410, f"Expected 410, got {response.status_code}"
    assert "expired" in response.text.lower()
    
    test_client.cookies.clear()
    
    # Cleanup
    supabase_test_client.table("refresh_tokens").update({"is_revoked": True}).eq("id", created_id).execute()


def test_refresh_token_after_student_token_revoked(test_client, admin_token, student_token_in_db, refresh_token_in_db, supabase_test_client):
    """Test: Admin revoca student token → refresh token fails 401 (cascade revoke)."""
    # Step 1: Verifica refresh token funziona pre-revoca
    test_client.cookies.set("refresh_token", refresh_token_in_db["token"])
    response = test_client.post("/api/v1/auth/refresh-token")
    assert response.status_code == 200, "Pre-condition failed: refresh token dovrebbe funzionare"
    
    # Step 2: Admin revoca student token (cascade revoke refresh tokens)
    response = test_client.delete(
        f"/api/v1/admin/student-tokens/{student_token_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204
    
    # Step 3: Verifica refresh token fails post-revoca
    response = test_client.post("/api/v1/auth/refresh-token")
    assert response.status_code == 401, f"Expected 401 after revoke, got {response.status_code}"
    
    test_client.cookies.clear()

