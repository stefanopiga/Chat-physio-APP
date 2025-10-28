import types

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.database import get_db_connection


@pytest.fixture
def health_test_client(monkeypatch):
    async def fake_init_db_pool():
        return None

    async def fake_close_db_pool():
        return None

    async def fake_db_connection():
        class DummyConnection:
            async def fetchval(self, *_args, **_kwargs):
                return 1

        yield DummyConnection()

    class FakeSupabase:
        def table(self, *_args, **_kwargs):
            return self

        def select(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            return types.SimpleNamespace(data=[])

    monkeypatch.setattr("api.database.init_db_pool", fake_init_db_pool)
    monkeypatch.setattr("api.database.close_db_pool", fake_close_db_pool)
    monkeypatch.setattr("api.knowledge_base.search._get_supabase_client", lambda: FakeSupabase())

    app.dependency_overrides[get_db_connection] = fake_db_connection

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.pop(get_db_connection, None)


def test_health_endpoint_returns_ok(health_test_client):
    resp = health_test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_dependencies_reports_ok(health_test_client):
    resp = health_test_client.get("/health/dependencies")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert {item["name"] for item in payload["checks"]} == {"database", "vector_store"}


def test_health_dependencies_handles_failures(monkeypatch, health_test_client):
    monkeypatch.setattr(
        "api.knowledge_base.search._get_supabase_client",
        lambda: (_ for _ in ()).throw(RuntimeError("supabase unavailable")),
    )

    resp = health_test_client.get("/health/dependencies")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "degraded"
    vector_status = next(item for item in payload["checks"] if item["name"] == "vector_store")
    assert vector_status["status"] == "error"
