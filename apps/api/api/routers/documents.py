"""
Documents router - Gestisce document explorer admin endpoints.

Endpoints:
- GET /api/v1/admin/documents - Lista documenti con metadata (Story 4.4)
- GET /api/v1/admin/documents/{document_id}/chunks - Chunk per documento (Story 4.4)

Story: 4.4
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
import asyncpg

from ..schemas.knowledge_base import (
    DocumentSummary,
    DocumentListResponse,
    ChunkDetail,
    DocumentChunksResponse,
)
from ..dependencies import _auth_bridge, TokenPayload, _is_admin, get_db_connection

router = APIRouter(prefix="/api/v1/admin/documents", tags=["Admin - Documents"])
logger = logging.getLogger("api")


def _admin_rate_limit_key(request: Request) -> str:
    """
    Rate limiting key per-admin per document endpoints.
    
    Args:
        request: FastAPI Request
        
    Returns:
        Rate limit key basato su user_id o client IP
    """
    import jwt
    import os
    
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
    EXPECTED_AUD = "authenticated"
    
    try:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=EXPECTED_AUD,
                options={"require": ["exp", "iat"]},
            )
            sub = payload.get("sub")
            if sub:
                return f"doc_rl::{sub}"
    except Exception:
        pass
    return (request.client.host if request.client else "unknown_ip")


@router.get("", response_model=DocumentListResponse)
async def get_documents(
    request: Request,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Recupera lista documenti con metadata aggregati (Story 4.4).
    
    Features:
    - MODE() WITHIN GROUP per strategia predominante
    - COUNT aggregato per numero chunk
    - LEFT JOIN per includere documenti senza chunk
    
    Args:
        request: FastAPI Request
        conn: Database connection
        payload: JWT payload verificato
        
    Returns:
        DocumentListResponse con lista documenti e total_count
        
    Security:
        - Admin-only access
        - Rate limiting: 30/hour (gestito da SlowAPI su main.app)
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    query = """
        SELECT 
            d.id AS document_id,
            d.file_name AS document_name,
            d.created_at AS upload_date,
            COUNT(c.id) AS chunk_count,
            MODE() WITHIN GROUP (ORDER BY c.metadata->>'chunking_strategy') AS primary_chunking_strategy
        FROM documents d
        LEFT JOIN document_chunks c ON d.id = c.document_id
        GROUP BY d.id, d.file_name, d.created_at
        ORDER BY d.created_at DESC
    """
    
    rows = await conn.fetch(query)
    documents = []
    for row in rows:
        documents.append(DocumentSummary(
            document_id=str(row["document_id"]),
            document_name=row["document_name"] or "",
            upload_date=row["upload_date"].isoformat() if row["upload_date"] else "",
            chunk_count=int(row["chunk_count"]) if row["chunk_count"] else 0,
            primary_chunking_strategy=row["primary_chunking_strategy"]
        ))
    
    logger.info({
        "event": "documents_list_accessed",
        "path": "/api/v1/admin/documents",
        "user_id": payload.get("sub"),
        "documents_count": len(documents),
    })
    
    return DocumentListResponse(
        documents=documents,
        total_count=len(documents)
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(
    request: Request,
    document_id: str,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
    skip: int = 0,
    limit: int = 100,
    strategy: str | None = None,
    min_size: int | None = None,
    sort_by: str = "created_at",
):
    """
    Recupera chunk per documento con filtri opzionali (Story 4.4).
    
    Features:
    - Query parametrizzate con $1, $2 (SQL injection safe)
    - Filtri dinamici opzionali
    - Paginazione
    - Sort configurabile
    
    Args:
        request: FastAPI Request
        document_id: Document identifier
        conn: Database connection
        payload: JWT payload verificato
        skip: Offset per paginazione (default: 0)
        limit: Numero chunk per pagina (default: 100)
        strategy: Filtro opzionale per chunking_strategy
        min_size: Filtro opzionale per dimensione minima chunk
        sort_by: Campo sort (default: "created_at")
        
    Returns:
        DocumentChunksResponse con lista chunk e total_count
        
    Security:
        - Admin-only access
        - Rate limiting: 30/hour (gestito da SlowAPI su main.app)
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    # Query base
    query_parts = ["""
        SELECT 
            c.id AS chunk_id,
            c.content,
            LENGTH(c.content) AS chunk_size,
            (c.metadata->>'chunk_index')::INTEGER AS chunk_index,
            c.metadata->>'chunking_strategy' AS chunking_strategy,
            (c.metadata->>'page_number')::INTEGER AS page_number,
            CASE WHEN c.embedding IS NOT NULL THEN 'indexed' ELSE 'pending' END AS embedding_status,
            c.created_at
        FROM document_chunks c
        WHERE c.document_id = $1
    """]
    
    params = [document_id]
    param_idx = 2
    
    # Filtro opzionale per strategia
    if strategy:
        query_parts.append(f"AND c.metadata->>'chunking_strategy' = ${param_idx}")
        params.append(strategy)
        param_idx += 1
    
    # Filtro opzionale per dimensione minima
    if min_size:
        query_parts.append(f"AND LENGTH(c.content) >= ${param_idx}")
        params.append(min_size)
        param_idx += 1
    
    # Validazione sort_by
    allowed_sort = {"created_at", "chunk_size"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    
    # Query count separata (senza limit/offset)
    count_query = " ".join(query_parts)
    count_result = await conn.fetchval(f"SELECT COUNT(*) FROM ({count_query}) AS sub", *params)
    total_count = int(count_result) if count_result else 0
    
    # Query document_name (Story 5.4 Task 2.1 FIX)
    document_name = await conn.fetchval(
        "SELECT file_name FROM documents WHERE id = $1",
        document_id
    )
    if not document_name:
        document_name = "unknown"
    
    # Query chunks con sort e paginazione (Story 5.5 Task 2: Qualified alias)
    query_parts.append(f"ORDER BY c.{sort_by} DESC")  # Story 5.5 Task 2: Added table alias 'c.'
    query_parts.append(f"LIMIT ${param_idx} OFFSET ${param_idx + 1}")
    params.extend([limit, skip])
    
    query = " ".join(query_parts)
    rows = await conn.fetch(query, *params)
    
    chunks = []
    for row in rows:
        chunks.append(ChunkDetail(
            chunk_id=str(row["chunk_id"]),
            content=row["content"] or "",
            chunk_size=int(row["chunk_size"]) if row["chunk_size"] else 0,
            chunk_index=row["chunk_index"],
            chunking_strategy=row["chunking_strategy"],
            page_number=row["page_number"],
            embedding_status=row["embedding_status"],
            created_at=row["created_at"].isoformat() if row["created_at"] else ""
        ))
    
    logger.info({
        "event": "document_chunks_accessed",
        "path": f"/api/v1/admin/documents/{document_id}/chunks",
        "user_id": payload.get("sub"),
        "document_id": document_id,
        "chunks_returned": len(chunks),
        "total_chunks": total_count,
    })
    
    return DocumentChunksResponse(
        document_id=document_id,  # Story 5.4 Task 2.1
        document_name=document_name,  # Story 5.4 Task 2.1 FIX
        chunks=chunks,
        total_chunks=total_count  # Story 5.4.1 Phase 2: renamed to total_chunks
    )

