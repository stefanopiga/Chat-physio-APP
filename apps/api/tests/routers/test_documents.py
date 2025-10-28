"""
Test suite per Documents Router (Story 4.4).

Coverage:
- GET /api/v1/admin/documents
- GET /api/v1/admin/documents/{document_id}/chunks
- Filtri (strategy, sort_by)
- Pagination
- Authorization (admin only)

Migration Notes (Story 5.3):
- Migrated to modern fixture pattern (client_admin, client_student)
- Removed manual TestClient and dependency_overrides
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from uuid import uuid4


@pytest.fixture
def mock_db_connection():
    """Mock asyncpg.Connection per testing."""
    conn = AsyncMock()
    return conn


def test_get_documents_success(client_admin, mock_db_connection):
    """Test: GET /api/v1/admin/documents → 200 con lista."""
    doc_id = uuid4()
    created_at = datetime.now(timezone.utc)
    
    mock_db_connection.fetch.return_value = [
        {
            "document_id": doc_id,
            "document_name": "anatomia_spalla.pdf",
            "upload_date": created_at,
            "chunk_count": 15,
            "primary_chunking_strategy": "recursive"
        }
    ]
    
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_admin.get("/api/v1/admin/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "documents" in data
        assert "total_count" in data
        assert data["total_count"] == 1
        assert len(data["documents"]) == 1
        
        doc = data["documents"][0]
        assert doc["document_id"] == str(doc_id)
        assert doc["document_name"] == "anatomia_spalla.pdf"
        assert doc["chunk_count"] == 15
        
    finally:
        app.dependency_overrides.clear()


def test_get_documents_forbidden_non_admin(client_student, mock_db_connection):
    """Test: GET /api/v1/admin/documents non-admin → 403."""
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_student.get("/api/v1/admin/documents")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden: admin only"
        
        mock_db_connection.fetch.assert_not_called()
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_success(client_admin, mock_db_connection):
    """Test: GET /api/v1/admin/documents/{id}/chunks → 200."""
    doc_id = str(uuid4())
    chunk_id = uuid4()
    created_at = datetime.now(timezone.utc)
    
    mock_db_connection.fetch.return_value = [
        {
            "chunk_id": chunk_id,
            "content": "Contenuto del chunk di test",
            "chunk_size": 26,
            "chunk_index": 0,
            "chunking_strategy": "recursive",
            "page_number": 1,
            "embedding_status": "indexed",
            "created_at": created_at
        }
    ]
    
    mock_db_connection.fetchval.side_effect = [5, "anatomia_spalla.pdf"]
    
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_admin.get(f"/api/v1/admin/documents/{doc_id}/chunks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == doc_id
        assert data["document_name"] == "anatomia_spalla.pdf"
        assert data["total_chunks"] == 5
        assert len(data["chunks"]) == 1
        
        chunk = data["chunks"][0]
        assert chunk["chunk_id"] == str(chunk_id)
        assert chunk["content"] == "Contenuto del chunk di test"
        assert chunk["chunk_size"] == 26
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_filter_strategy(client_admin, mock_db_connection):
    """Test: filtro ?strategy=recursive funziona."""
    doc_id = str(uuid4())
    
    mock_db_connection.fetch.return_value = []
    mock_db_connection.fetchval.side_effect = [0, "test.pdf"]
    
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_admin.get(
            f"/api/v1/admin/documents/{doc_id}/chunks",
            params={"strategy": "recursive"}
        )
        
        assert response.status_code == 200
        
        query_executed = mock_db_connection.fetch.call_args[0][0]
        params_executed = mock_db_connection.fetch.call_args[0][1:]
        
        assert "metadata->>'chunking_strategy'" in query_executed
        assert "recursive" in params_executed
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_sort_by_size(client_admin, mock_db_connection):
    """Test: ?sort_by=chunk_size ordina correttamente."""
    doc_id = str(uuid4())
    
    mock_db_connection.fetch.return_value = []
    mock_db_connection.fetchval.side_effect = [0, "test.pdf"]
    
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_admin.get(
            f"/api/v1/admin/documents/{doc_id}/chunks",
            params={"sort_by": "chunk_size"}
        )
        
        assert response.status_code == 200
        
        query_executed = mock_db_connection.fetch.call_args[0][0]
        # Story 5.5 Task 2: Query uses qualified alias with table prefix
        assert "ORDER BY c.chunk_size" in query_executed
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_pagination(client_admin, mock_db_connection):
    """Test: ?limit=10&skip=5 pagination funziona."""
    doc_id = str(uuid4())
    
    mock_db_connection.fetch.return_value = []
    mock_db_connection.fetchval.side_effect = [20, "test.pdf"]
    
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_admin.get(
            f"/api/v1/admin/documents/{doc_id}/chunks",
            params={"limit": 10, "skip": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_chunks"] == 20
        
        query_executed = mock_db_connection.fetch.call_args[0][0]
        params_executed = mock_db_connection.fetch.call_args[0][1:]
        
        assert "LIMIT" in query_executed
        assert "OFFSET" in query_executed
        assert 10 in params_executed
        assert 5 in params_executed
        
    finally:
        app.dependency_overrides.clear()

