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


def test_start_sync_job_with_mocked_dependencies(client, monkeypatch):
    # Mock auth to always allow admin (Story 5.4.1 Phase 3: migrated to dependencies)
    def fake_verify_jwt_token(_):
        return {"role": "admin", "app_metadata": {"role": "admin"}}

    from api import dependencies
    monkeypatch.setattr(dependencies, "verify_jwt_token", lambda: fake_verify_jwt_token(None))

    # Mock router to return 2 chunks
    class FakeChunks:
        chunks = ["a", "b"]
        strategy_name = "test_strategy"
        parameters = {}

    def fake_route(content, classification):
        return FakeChunks()

    monkeypatch.setattr(
        "api.routers.knowledge_base.ChunkRouter",
        lambda: type("R", (), {"route": staticmethod(fake_route)})()
    )

    monkeypatch.setattr("api.routers.knowledge_base.CELERY_ENABLED", False)

    # Mock indexer to count inputs
    calls = {"n": 0}

    def fake_index(chunks, metadata_list):
        calls["n"] = len(chunks)
        return len(chunks)

    monkeypatch.setattr("api.routers.knowledge_base.index_chunks", fake_index)

    fake_doc_id = uuid.uuid4()

    async def fake_save_document_to_db(*args, **kwargs):
        return fake_doc_id

    async def fake_update_document_status(*args, **kwargs):
        return None

    monkeypatch.setattr("api.routers.knowledge_base.save_document_to_db", fake_save_document_to_db)
    monkeypatch.setattr("api.routers.knowledge_base.update_document_status", fake_update_document_status)

    resp = client.post(
        "/api/v1/admin/knowledge-base/sync-jobs",
        headers={"Authorization": "Bearer x"},
        json={"document_text": "x", "metadata": {"document_name": "test"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2
    assert data["job_id"] == str(fake_doc_id)
    assert data["document_id"] == str(fake_doc_id)
    assert calls["n"] == 2
