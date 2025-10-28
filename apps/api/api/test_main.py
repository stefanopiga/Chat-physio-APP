from datetime import datetime, timedelta, timezone
import os

import jwt
import pytest
from fastapi.testclient import TestClient

from .main import app
from .routers.auth import access_codes_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_access_code_store():
    access_codes_store.clear()
    yield
    access_codes_store.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_exchange_code_invalid_request():
    r = client.post("/api/v1/auth/exchange-code", json={"access_code": ""})
    assert r.status_code == 400


def test_exchange_code_invalid_code():
    r = client.post("/api/v1/auth/exchange-code", json={"access_code": "NOTEXIST"})
    assert r.status_code == 401


def test_exchange_code_happy_path_monouse():
    # Arrange: inserisci codice in store (simula generazione admin)
    code_value = "TESTCODE1"
    access_codes_store[code_value] = {
        "id": "code-1",
        "code": code_value,
        "is_active": True,
        "expires_at": None,
        "usage_count": 0,
        "last_used_at": None,
        "created_by_id": "admin-1",
        "created_at": None,
        "updated_at": None,
    }

    r = client.post("/api/v1/auth/exchange-code", json={"access_code": code_value})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data and data["token_type"] == "bearer"
    assert isinstance(data["expires_in"], int) and data["expires_in"] > 0

    # Secondo uso deve fallire
    r2 = client.post("/api/v1/auth/exchange-code", json={"access_code": code_value})
    assert r2.status_code == 409


def test_exchange_code_expired_code():
    code_value = "EXPIRED01"
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    access_codes_store[code_value] = {
        "id": "code-exp",
        "code": code_value,
        "is_active": True,
        "expires_at": past,
        "usage_count": 0,
        "last_used_at": None,
        "created_by_id": "admin-1",
        "created_at": None,
        "updated_at": None,
    }

    r = client.post("/api/v1/auth/exchange-code", json={"access_code": code_value})
    assert r.status_code == 410


def test_exchange_code_jwt_claims():
    # Prepara un codice valido
    code_value = "CLAIMS01"
    access_codes_store[code_value] = {
        "id": "code-claims",
        "code": code_value,
        "is_active": True,
        "expires_at": None,
        "usage_count": 0,
        "last_used_at": None,
        "created_by_id": "admin-1",
        "created_at": None,
        "updated_at": None,
    }

    r = client.post("/api/v1/auth/exchange-code", json={"access_code": code_value})
    assert r.status_code == 200
    data = r.json()
    token = data["token"]

    secret = os.environ.get("SUPABASE_JWT_SECRET", "devsecret")
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    assert payload.get("iss") == "https://example.supabase.co/auth/v1"
    assert payload.get("aud") == "authenticated"
    assert payload.get("sub", "").startswith("student:")
    assert isinstance(payload.get("exp"), int)


# -------------------------------
# Admin: generate access code
# -------------------------------

def _make_jwt(sub: str, role: str = "admin") -> str:
    secret = os.environ.get("SUPABASE_JWT_SECRET", "devsecret")
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "https://example.supabase.co/auth/v1",
        "aud": "authenticated",
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=60)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_admin_generate_code_requires_auth():
    r = client.post("/api/v1/auth/admin/access-codes/generate", json={})
    assert r.status_code == 401


def test_admin_generate_code_forbidden_if_not_admin():
    token = _make_jwt(sub="user-1", role="authenticated")
    r = client.post(
        "/api/v1/auth/admin/access-codes/generate",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_admin_generate_code_success_and_persist():
    # Clear store for deterministic assertion
    access_codes_store.clear()

    token = _make_jwt(sub="admin-1", role="admin")
    r = client.post(
        "/api/v1/auth/admin/access-codes/generate",
        json={"expires_in_minutes": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert set(["id", "code"]).issubset(data.keys())

    # Verify persistence in store with expected defaults
    code_value = data["code"]
    rec = access_codes_store.get(code_value)
    assert rec is not None
    assert rec["id"] == data["id"]
    assert rec["is_active"] is True
    assert rec.get("usage_count", 0) == 0
    assert rec.get("created_by_id") == "admin-1"
    # expires_at set approximately 5 minutes in the future
    assert rec["expires_at"] is not None
