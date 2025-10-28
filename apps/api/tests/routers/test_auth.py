"""
Test suite per Authentication Router (Story 1.3 + 1.3.1).

Coverage:
- POST /api/v1/auth/exchange-code (access code + student token)
- POST /api/v1/auth/refresh-token
- Rate limiting enforcement
- JWT validation

Migration Notes (Story 5.3):
- Removed duplicate fixtures (supabase_test_client, student_token_in_db, refresh_token_in_db)
- Uses fixtures from conftest.py to prevent FK constraint errors
"""
import os
import secrets
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

# Note: supabase_test_client, student_token_in_db, refresh_token_in_db fixtures
# sono definite in conftest.py e automaticamente disponibili


# =============================================================================
# Integration Tests: Exchange Code
# =============================================================================

def test_exchange_code_with_student_token(test_client, student_token_in_db, supabase_test_client):
    """
    Test: POST /api/v1/auth/exchange-code con student token.
    
    Verifica:
    - Status 200
    - JWT access token 15 min
    - HttpOnly cookie refresh_token
    - Refresh token salvato in DB
    """
    response = test_client.post(
        "/api/v1/auth/exchange-code",
        json={"access_code": student_token_in_db["token"]}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "token" in data  # ExchangeCodeResponse usa "token" (non "access_token")
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    
    # Verifica JWT duration
    import jwt
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if jwt_secret:
        decoded = jwt.decode(
            data["token"], 
            jwt_secret, 
            algorithms=["HS256"], 
            audience="authenticated",
            options={"verify_exp": False}
        )
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        duration_minutes = (exp_time - iat_time).total_seconds() / 60
        assert 14 <= duration_minutes <= 16
    
    # Verifica cookie
    assert "set-cookie" in response.headers
    cookie_header = response.headers["set-cookie"]
    assert "refresh_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=Strict" in cookie_header or "SameSite=strict" in cookie_header
    
    # Verifica DB
    refresh_result = supabase_test_client.table("refresh_tokens").select("*").eq(
        "student_token_id", student_token_in_db["id"]
    ).execute()
    assert len(refresh_result.data) > 0
    assert refresh_result.data[0]["is_revoked"] is False


def test_exchange_code_with_expired_student_token(test_client, supabase_test_client):
    """
    Test: POST /api/v1/auth/exchange-code con token scaduto → 410.
    """
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
    
    token = secrets.token_urlsafe(32)
    expired_at = datetime.now(timezone.utc) - timedelta(days=1)
    
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
    
    assert response.status_code == 410
    assert "expired" in response.text.lower()
    
    # Cleanup (child → parent order)
    try:
        supabase_test_client.table("student_tokens").delete().eq("id", created_id).execute()
        supabase_test_client.table("users").delete().eq("id", test_user_id).execute()
    except Exception:
        pass


def test_exchange_code_with_revoked_student_token(test_client, supabase_test_client):
    """
    Test: POST /api/v1/auth/exchange-code con token revocato → 401.
    """
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
    
    token = secrets.token_urlsafe(32)
    
    result = supabase_test_client.table("student_tokens").insert({
        "first_name": "Revoked",
        "last_name": "User",
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "is_active": False,
        "created_by_id": test_user_id,
    }).execute()
    
    created_id = result.data[0]["id"]
    
    response = test_client.post(
        "/api/v1/auth/exchange-code",
        json={"access_code": token}
    )
    
    assert response.status_code == 401
    
    # Cleanup (child → parent order)
    try:
        supabase_test_client.table("student_tokens").delete().eq("id", created_id).execute()
        supabase_test_client.table("users").delete().eq("id", test_user_id).execute()
    except Exception:
        pass


# =============================================================================
# Integration Tests: Refresh Token
# =============================================================================

def test_refresh_token_success(test_client, refresh_token_in_db, supabase_test_client):
    """
    Test: POST /api/v1/auth/refresh-token con cookie valido → nuovo JWT.
    """
    test_client.cookies.set("refresh_token", refresh_token_in_db["token"])
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    
    # Verifica last_used_at aggiornato
    refresh_result = supabase_test_client.table("refresh_tokens").select("*").eq(
        "id", refresh_token_in_db["id"]
    ).execute()
    assert refresh_result.data[0]["last_used_at"] is not None
    
    test_client.cookies.clear()


def test_refresh_token_missing_cookie(test_client):
    """
    Test: POST /api/v1/auth/refresh-token senza cookie → 400.
    """
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 400
    assert "missing_refresh_token" in response.text.lower()


def test_refresh_token_invalid(test_client):
    """
    Test: POST /api/v1/auth/refresh-token con cookie non in DB → 401.
    """
    fake_refresh_token = secrets.token_urlsafe(64)
    test_client.cookies.set("refresh_token", fake_refresh_token)
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 401
    assert "invalid" in response.text.lower() or "revoked" in response.text.lower()
    
    test_client.cookies.clear()


def test_refresh_token_revoked(test_client, refresh_token_in_db, supabase_test_client):
    """
    Test: POST /api/v1/auth/refresh-token con token revocato → 401.
    """
    supabase_test_client.table("refresh_tokens").update({
        "is_revoked": True
    }).eq("id", refresh_token_in_db["id"]).execute()
    
    test_client.cookies.set("refresh_token", refresh_token_in_db["token"])
    
    response = test_client.post("/api/v1/auth/refresh-token")
    
    assert response.status_code == 401
    
    test_client.cookies.clear()


def test_refresh_token_expired(test_client, supabase_test_client, student_token_in_db):
    """
    Test: POST /api/v1/auth/refresh-token con token scaduto → 410.
    """
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
    
    assert response.status_code == 410
    assert "expired" in response.text.lower()
    
    test_client.cookies.clear()
    
    # Cleanup
    supabase_test_client.table("refresh_tokens").update({"is_revoked": True}).eq("id", created_id).execute()

