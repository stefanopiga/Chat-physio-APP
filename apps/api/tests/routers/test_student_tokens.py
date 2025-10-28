"""
Test suite per Student Tokens Router (Story 1.3.1).

Coverage:
- POST /api/v1/admin/student-tokens (create)
- GET /api/v1/admin/student-tokens (list)
- DELETE /api/v1/admin/student-tokens/{id} (soft delete)
- Authorization checks (admin only)
- Cascade revoke refresh tokens
"""
import os
import secrets
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from pydantic import ValidationError
from supabase import create_client


# =============================================================================
# Unit Tests: Token Generation & Validation
# =============================================================================

def test_generate_student_token_uniqueness():
    """Test: student token generation produces unique 32-char tokens."""
    tokens = set()
    
    for _ in range(1000):
        token = secrets.token_urlsafe(32)
        tokens.add(token)
    
    assert len(tokens) == 1000
    
    for token in tokens:
        assert len(token) >= 32


def test_generate_refresh_token_uniqueness():
    """Test: refresh token generation produces unique 64-char tokens."""
    tokens = set()
    
    for _ in range(1000):
        token = secrets.token_urlsafe(64)
        tokens.add(token)
    
    assert len(tokens) == 1000
    
    for token in tokens:
        assert len(token) >= 64


def test_create_student_token_request_validation():
    """Test: Pydantic validation CreateStudentTokenRequest."""
    from api.schemas.student_tokens import CreateStudentTokenRequest
    
    # Test: first_name vuoto
    with pytest.raises(ValidationError) as exc_info:
        CreateStudentTokenRequest(first_name="", last_name="Rossi")
    
    assert "first_name" in str(exc_info.value)
    
    # Test: last_name vuoto
    with pytest.raises(ValidationError) as exc_info:
        CreateStudentTokenRequest(first_name="Mario", last_name="")
    
    assert "last_name" in str(exc_info.value)
    
    # Test: first_name troppo lungo
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
    """Test: POST /api/v1/admin/student-tokens crea token (201).
    
    Story 5.4.3 Fix: usa admin_token_in_db con UUID valido invece di admin_token
    per evitare errori 422 su validazione created_by_id.
    """
    response = test_client.post(
        "/api/v1/admin/student-tokens",
        json={"first_name": "Mario", "last_name": "Rossi"},
        headers={"Authorization": f"Bearer {admin_token_in_db['token']}"}
    )
    
    assert response.status_code == 201
    
    data = response.json()
    assert "id" in data
    assert "token" in data
    assert data["first_name"] == "Mario"
    assert data["last_name"] == "Rossi"
    assert "expires_at" in data
    
    # Verifica DB: created_by_id corretto (Story 5.4.3)
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
    
    assert response.status_code == 401


def test_create_student_token_forbidden_non_admin(test_client):
    """Test: POST /api/v1/admin/student-tokens con JWT non-admin → 403."""
    import jwt
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not jwt_secret:
        pytest.skip("SUPABASE_JWT_SECRET non configurato")
    
    payload = {
        "sub": "test-user-id",
        "role": "authenticated",
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
    
    assert response.status_code == 403


def test_list_student_tokens_filtered(test_client, admin_token, student_token_in_db, supabase_test_client):
    """Test: GET /api/v1/admin/student-tokens filtra per is_active."""
    response = test_client.get(
        "/api/v1/admin/student-tokens?is_active=true",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Verifica token presente
    active_ids = [token["id"] for token in data]
    assert student_token_in_db["id"] in active_ids
    
    # Soft delete
    supabase_test_client.table("student_tokens").update({
        "is_active": False
    }).eq("id", student_token_in_db["id"]).execute()
    
    # Test lista dopo revoca
    response = test_client.get(
        "/api/v1/admin/student-tokens?is_active=true",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    data = response.json()
    active_ids_after_revoke = [token["id"] for token in data]
    assert student_token_in_db["id"] not in active_ids_after_revoke


def test_delete_student_token_soft_delete(test_client, admin_token, student_token_in_db, supabase_test_client):
    """Test: DELETE /api/v1/admin/student-tokens/{id} soft delete + cascade revoke."""
    # Crea refresh token associato
    refresh_token = secrets.token_urlsafe(64)
    supabase_test_client.table("refresh_tokens").insert({
        "student_token_id": student_token_in_db["id"],
        "token": refresh_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "is_revoked": False,
    }).execute()
    
    # DELETE
    response = test_client.delete(
        f"/api/v1/admin/student-tokens/{student_token_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 204
    
    # Verifica soft delete
    db_result = supabase_test_client.table("student_tokens").select("*").eq("id", student_token_in_db["id"]).execute()
    assert db_result.data[0]["is_active"] is False
    
    # Verifica cascade revoke
    refresh_result = supabase_test_client.table("refresh_tokens").select("*").eq(
        "student_token_id", student_token_in_db["id"]
    ).execute()
    for refresh in refresh_result.data:
        assert refresh["is_revoked"] is True


def test_delete_student_token_not_found(test_client, admin_token):
    """Test: DELETE /api/v1/admin/student-tokens/{id} con id inesistente → 404."""
    fake_uuid = "00000000-0000-0000-0000-999999999999"
    
    response = test_client.delete(
        f"/api/v1/admin/student-tokens/{fake_uuid}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404


def test_refresh_token_after_student_token_revoked(
    test_client, admin_token, student_token_in_db, refresh_token_in_db, supabase_test_client
):
    """Test: Admin revoca student token → refresh token fails (cascade)."""
    # Pre-condition
    test_client.cookies.set("refresh_token", refresh_token_in_db["token"])
    response = test_client.post("/api/v1/auth/refresh-token")
    assert response.status_code == 200
    
    # Revoca student token
    response = test_client.delete(
        f"/api/v1/admin/student-tokens/{student_token_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204
    
    # Verifica refresh fails
    response = test_client.post("/api/v1/auth/refresh-token")
    assert response.status_code == 401
    
    test_client.cookies.clear()

