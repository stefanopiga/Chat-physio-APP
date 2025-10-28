from __future__ import annotations
import os
import logging
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from supabase import Client, create_client

logger = logging.getLogger("api")


def _get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY non impostati")
    return create_client(url, key)


def _get_embeddings_model() -> OpenAIEmbeddings:
    # richiede OPENAI_API_KEY nell'ambiente
    return OpenAIEmbeddings(model="text-embedding-3-small")


def perform_semantic_search(
    query: str,
    match_count: int = 8,
    match_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Esegue ricerca semantica su Supabase (pgvector) e restituisce lista di risultati.
    """
    if not query or not query.strip():
        return []

    supabase = _get_supabase_client()
    embeddings = _get_embeddings_model()

    try:
        query_embedding = embeddings.embed_query(query)
    except Exception as exc:  # pragma: no cover - errore embedding propagato
        logger.error(
            {"event": "embedding_query_failed", "error": str(exc)}
        )
        raise

    # Soglia predefinita meno rigida per recuperare risultati pertinenti
    threshold = match_threshold if match_threshold is not None else 0.6

    def _execute(threshold_value: float) -> List[Dict[str, Any]]:
        response = supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": float(threshold_value),
                "match_count": match_count,
            },
        ).execute()

        rows = response.data or []
        results: List[Dict[str, Any]] = []
        for row in rows:
            metadata: Dict[str, Any] = dict(row.get("metadata") or {})
            chunk_id = row.get("id")
            document_id = row.get("document_id")
            if chunk_id and not metadata.get("id"):
                metadata["id"] = str(chunk_id)
            if chunk_id and not metadata.get("chunk_id"):
                metadata["chunk_id"] = str(chunk_id)
            if document_id and not metadata.get("document_id"):
                metadata["document_id"] = str(document_id)

            results.append(
                {
                    "id": str(chunk_id) if chunk_id else None,
                    "document_id": str(document_id) if document_id else None,
                    "content": row.get("content"),
                    "metadata": metadata,
                    "similarity_score": row.get("similarity"),
                }
            )
        return results

    try:
        hits = _execute(threshold)
        if not hits and threshold > 0.0:
            logger.info(
                {
                    "event": "semantic_search_threshold_fallback",
                    "query": query[:100],
                    "match_count": match_count,
                    "previous_threshold": threshold,
                }
            )
            hits = _execute(0.0)
        return hits
    except Exception as exc:
        logger.warning(
            {"event": "semantic_search_rpc_error", "error": str(exc)}
        )
        return []
