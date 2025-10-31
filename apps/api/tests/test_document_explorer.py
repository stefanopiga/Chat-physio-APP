"""
Unit tests for Document Explorer endpoints (Story 4.4).

Test Coverage:
1. GET /api/v1/admin/documents - 200 con lista documenti
2. GET /api/v1/admin/documents - 403 per non-admin
3. GET /api/v1/admin/documents/{id}/chunks - 200 con chunk list
4. GET /api/v1/admin/documents/{id}/chunks - filtro per strategy funziona
5. GET /api/v1/admin/documents/{id}/chunks - sort per size funziona
6. GET /api/v1/admin/documents/{id}/chunks - pagination funziona

Migration Notes (Story 5.3):
- Migrated to modern fixture pattern (client_admin, client_student)
- Removed manual TestClient(app) fixture
- Removed manual dependency_overrides (handled by conftest.py fixtures)
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


@pytest.fixture
def mock_admin_auth():
    """Mock admin authentication payload."""
    return {"sub": "admin-123", "role": "admin"}


@pytest.fixture
def mock_student_auth():
    """Mock student authentication payload (non-admin)."""
    return {"sub": "student-123", "role": "authenticated"}


def test_get_documents_success(client_admin, mock_db_connection, mock_admin_auth):
    """
    Test 1: GET /api/v1/admin/documents - 200 con lista documenti.
    
    AC:
    - Admin autenticato riceve lista documenti
    - Ogni documento include: id, nome, data upload, chunk count, strategia predominante
    - Response include total_count
    """
    # Setup mock data
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
    
    # Override database connection
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
        assert doc["primary_chunking_strategy"] == "recursive"
        
        # Verifica query eseguita
        mock_db_connection.fetch.assert_called_once()
        query_executed = mock_db_connection.fetch.call_args[0][0]
        assert "MODE() WITHIN GROUP" in query_executed
        assert "LEFT JOIN document_chunks" in query_executed
        
    finally:
        app.dependency_overrides.clear()


def test_get_documents_forbidden_non_admin(client_student, mock_db_connection, mock_student_auth):
    """
    Test 2: GET /api/v1/admin/documents - 403 per non-admin.
    
    AC:
    - Utente non-admin riceve 403 Forbidden
    - Query database non viene eseguita
    """
    from api.main import app
    from api.database import get_db_connection
    
    async def mock_get_conn():
        yield mock_db_connection
    
    app.dependency_overrides[get_db_connection] = mock_get_conn
    
    try:
        response = client_student.get("/api/v1/admin/documents")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden: admin only"
        
        # Database non deve essere chiamato
        mock_db_connection.fetch.assert_not_called()
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_success(client_admin, mock_db_connection, mock_admin_auth):
    """
    Test 3: GET /api/v1/admin/documents/{id}/chunks - 200 con chunk list.
    
    AC:
    - Admin autenticato riceve lista chunk per documento
    - Ogni chunk include: id, content, size, index, strategy, embedding status
    - Response include document_name e total_chunks
    """
    doc_id = str(uuid4())
    chunk_id = uuid4()
    created_at = datetime.now(timezone.utc)
    
    # Mock fetch per chunk list
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
    
    # Mock fetchval per count e document name
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
        assert chunk["chunk_index"] == 0
        assert chunk["chunking_strategy"] == "recursive"
        assert chunk["embedding_status"] == "indexed"
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_filter_strategy(client_admin, mock_db_connection, mock_admin_auth):
    """
    Test 4: GET /api/v1/admin/documents/{id}/chunks - filtro per strategy funziona.
    
    AC:
    - Parametro ?strategy=recursive filtra solo chunk con quella strategia
    - Query include WHERE condition per metadata->>'chunking_strategy'
    """
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
        
        # Verifica query include filtro strategia
        query_executed = mock_db_connection.fetch.call_args[0][0]
        params_executed = mock_db_connection.fetch.call_args[0][1:]
        
        assert "metadata->>'chunking_strategy'" in query_executed
        assert "recursive" in params_executed
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_sort_by_size(client_admin, mock_db_connection, mock_admin_auth):
    """
    Test 5: GET /api/v1/admin/documents/{id}/chunks - sort per size funziona.
    
    AC:
    - Parametro ?sort_by=chunk_size ordina chunk per dimensione
    - Query include ORDER BY chunk_size
    """
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
        
        # Verifica query include ORDER BY
        query_executed = mock_db_connection.fetch.call_args[0][0]
        assert "ORDER BY c.chunk_size" in query_executed
        
    finally:
        app.dependency_overrides.clear()


def test_get_document_chunks_pagination(client_admin, mock_db_connection, mock_admin_auth):
    """
    Test 6: GET /api/v1/admin/documents/{id}/chunks - pagination funziona.
    
    AC:
    - Parametri ?limit=10&skip=5 limitano risultati
    - Query include LIMIT e OFFSET con valori corretti
    """
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
        
        # Total chunks deve essere 20 (senza paginazione)
        assert data["total_chunks"] == 20
        
        # Verifica query include LIMIT e OFFSET
        query_executed = mock_db_connection.fetch.call_args[0][0]
        params_executed = mock_db_connection.fetch.call_args[0][1:]
        
        assert "LIMIT" in query_executed
        assert "OFFSET" in query_executed
        assert 10 in params_executed  # limit
        assert 5 in params_executed   # skip
        
    finally:
        app.dependency_overrides.clear()

