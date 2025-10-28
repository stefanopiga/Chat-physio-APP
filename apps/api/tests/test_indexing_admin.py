from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db_connection
from unittest.mock import AsyncMock, patch
import pytest
import uuid


@pytest.fixture
def client():
    # Mock get_db_connection per evitare RuntimeError DB pool
    async def mock_get_db_connection():
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=uuid.uuid4())
        mock_conn.execute = AsyncMock(return_value=None)
        yield mock_conn
    
    # Mock init_db_pool e close_db_pool per evitare connessione DB reale durante lifespan
    async def mock_init_db_pool():
        pass
    
    async def mock_close_db_pool():
        pass
    
    app.dependency_overrides[get_db_connection] = mock_get_db_connection
    
    with patch('api.database.init_db_pool', side_effect=mock_init_db_pool), \
         patch('api.database.close_db_pool', side_effect=mock_close_db_pool):
        with TestClient(app) as test_client:
            yield test_client
    
    app.dependency_overrides.clear()


def _fake_admin_token_headers():
    # Bypass verify_jwt_token by monkeypatching in tests is preferred; here we expect env var SUPABASE_JWT_SECRET set
    # For integration tests, the app requires a valid token; unit tests should monkeypatch dependencies.
    return {"Authorization": "Bearer test"}


def test_start_sync_job_requires_auth(client):
    resp = client.post("/api/v1/admin/knowledge-base/sync-jobs", json={"document_text": "ciao"})
    assert resp.status_code in (401, 403)


def test_sync_job_status_flow(client, monkeypatch):
    # Mock auth: always admin (Story 5.4.1 Phase 3: migrated to dependencies)
    def fake_verify_jwt_token(_=None):
        return {"role": "admin", "app_metadata": {"role": "admin"}}

    from api import dependencies
    monkeypatch.setattr(dependencies, "verify_jwt_token", lambda: fake_verify_jwt_token(None))

    # Mock pipeline: router returns single chunk, indexer returns 1
    class FakeChunks:
        chunks = ["uno"]
        strategy_name = "test_strategy"
        parameters = {}

    def fake_route(content, classification):
        return FakeChunks()

    monkeypatch.setattr(
        "api.routers.knowledge_base.ChunkRouter",
        lambda: type("R", (), {"route": staticmethod(fake_route)})()
    )

    monkeypatch.setattr("api.routers.knowledge_base.CELERY_ENABLED", False)

    inserted_calls = {"count": 0}

    def fake_index(chunks, metadata_list):
        inserted_calls["count"] = len(chunks)
        return len(chunks)

    monkeypatch.setattr("api.routers.knowledge_base.index_chunks", fake_index)

    fake_doc_id = uuid.uuid4()

    async def fake_save_document_to_db(*args, **kwargs):
        return fake_doc_id

    async def fake_update_document_status(*args, **kwargs):
        return None

    monkeypatch.setattr("api.routers.knowledge_base.save_document_to_db", fake_save_document_to_db)
    monkeypatch.setattr("api.routers.knowledge_base.update_document_status", fake_update_document_status)

    # Start job
    resp = client.post(
        "/api/v1/admin/knowledge-base/sync-jobs",
        headers={"Authorization": "Bearer x"},
        json={"document_text": "abc", "metadata": {"document_name": "test"}},
    )
    assert resp.status_code == 200
    job = resp.json()
    assert job["job_id"] == str(fake_doc_id)
    assert job["document_id"] == str(fake_doc_id)
    assert inserted_calls["count"] == 1

    from api.stores import sync_jobs_store
    assert sync_jobs_store[job["job_id"]]["inserted"] == 1
    assert job["inserted"] == 1

    # Get status
    status_resp = client.get(
        f"/api/v1/admin/knowledge-base/sync-jobs/{job['job_id']}",
        headers={"Authorization": "Bearer x"},
    )
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["job_id"] == job["job_id"]
    assert data["status"] in ("completed", "running")
    assert data.get("error") is None
    assert data.get("document_id") == job["job_id"]
