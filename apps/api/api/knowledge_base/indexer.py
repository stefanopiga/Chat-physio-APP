from __future__ import annotations
import os
import logging
import time
import openai
from typing import List, Dict, Any

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client, Client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger("api")


def _get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    # Try both SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_ROLE_KEY (alias)
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL o SUPABASE_SERVICE_KEY/SUPABASE_SERVICE_ROLE_KEY non impostati")
    return create_client(url, key)


def _get_embeddings_model() -> OpenAIEmbeddings:
    """Crea istanza OpenAIEmbeddings con gestione errori.
    
    Raises:
        openai.AuthenticationError: Chiave API invalida o mancante
        openai.APIConnectionError: Server OpenAI non raggiungibile
        openai.RateLimitError: Rate limit superato
        openai.APIStatusError: Altri errori API
    """
    try:
        return OpenAIEmbeddings(model="text-embedding-3-small")
    except openai.AuthenticationError as e:
        logger.error(
            f"Autenticazione OpenAI fallita: {e}. "
            "Verificare OPENAI_API_KEY in .env"
        )
        raise
    except openai.APIConnectionError as e:
        logger.error(
            f"Impossibile raggiungere server OpenAI: {e.__cause__}. "
            "Verificare connessione di rete"
        )
        raise
    except openai.RateLimitError as e:
        logger.warning(
            f"Rate limit OpenAI raggiunto: {e}. "
            "Implementare retry con backoff esponenziale"
        )
        raise
    except openai.APIStatusError as e:
        logger.error(
            f"Errore API OpenAI [{e.status_code}]: {e.response}",
            extra={"status_code": e.status_code}
        )
        raise


@retry(
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
def _embed_texts_with_retry(
    texts: List[str], 
    embeddings_model: OpenAIEmbeddings
) -> List[List[float]]:
    """Batch embedding con exponential backoff retry (Story 2.5 AC6).
    
    Handles:
    - Rate limit errors (429): retry con backoff esponenziale
    - Transient connection errors: retry automatico
    - Timeout errors: retry automatico
    
    Batch size ottimizzato: 100 texts per batch (OpenAI best practice)
    
    Args:
        texts: Lista di testi da embedare
        embeddings_model: Model OpenAIEmbeddings configurato
        
    Returns:
        Lista di embeddings (vectors)
        
    Raises:
        openai.AuthenticationError: Invalid API key (no retry)
        openai.InvalidRequestError: Invalid request (no retry)
        Exception: After max retries exhausted (5 attempts)
    """
    logger.info({
        "event": "embedding_start",
        "texts_count": len(texts),
        "batch_size": 100
    })
    
    # Batch size optimization: OpenAI recommends < 2048 texts per batch
    BATCH_SIZE = 100
    all_embeddings = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(texts) - 1) // BATCH_SIZE + 1
        
        logger.info({
            "event": "embedding_batch",
            "batch": batch_num,
            "total_batches": total_batches,
            "batch_size": len(batch)
        })
        
        # embed_documents può sollevare RateLimitError/APIConnectionError
        # → tenacity gestisce retry automatico
        batch_embeddings = embeddings_model.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        
        logger.info({
            "event": "embedding_batch_complete",
            "batch": batch_num,
            "embeddings_count": len(batch_embeddings)
        })
    
    logger.info({
        "event": "embedding_complete",
        "total_embeddings": len(all_embeddings)
    })
    
    return all_embeddings


def index_chunks(chunks: List[str], metadata_list: List[Dict[str, Any]] | None = None) -> int:
    """Calcola embedding e inserisce in Supabase con timing metrics (Story 2.5 AC5, AC8).
    
    Pipeline:
    1. Embedding batch con retry logic (AC6)
    2. Supabase insert con timing metrics
    
    Timing metrics:
    - embedding_ms: Tempo embedding con OpenAI
    - supabase_insert_ms: Tempo inserimento Supabase
    - total_ms: Tempo totale pipeline
    
    Returns:
        Numero record inseriti
    
    Raises:
        openai.AuthenticationError: Autenticazione OpenAI fallita
        ValueError: Inserimento fallito (zero chunks inseriti)
        Exception: Errori Supabase o altri errori inattesi
    """
    if not chunks:
        logger.warning("No chunks to index")
        return 0

    start_total = time.time()
    timing_metrics = {}

    logger.info({
        "event": "indexing_start",
        "chunks_count": len(chunks)
    })

    try:
        # Phase 1: Embedding con retry logic
        start_embed = time.time()
        embeddings_model = _get_embeddings_model()
        embeddings = _embed_texts_with_retry(chunks, embeddings_model)
        timing_metrics["embedding_ms"] = int((time.time() - start_embed) * 1000)
        
        logger.info({
            "event": "embedding_phase_complete",
            "duration_ms": timing_metrics["embedding_ms"],
            "embeddings_count": len(embeddings)
        })
        
        # Phase 2: Supabase insert
        start_insert = time.time()
        supabase = _get_supabase_client()
        
        # Normalizza metadata list
        metadata_list = metadata_list or [{} for _ in chunks]
        
        vector_store = SupabaseVectorStore(
            embedding=embeddings_model,
            client=supabase,
            table_name="document_chunks",
            query_name="match_document_chunks",
        )
        
        ids = vector_store.add_texts(texts=chunks, metadatas=metadata_list)
        if len(ids) != len(set(ids)):
            logger.error({
                "event": "chunk_id_collision_detected",
                "inserted_ids": ids,
            })
            raise ValueError("Duplicate chunk IDs detected during indexing")
        timing_metrics["supabase_insert_ms"] = int((time.time() - start_insert) * 1000)
        
        # Verifica post-inserimento OBBLIGATORIA
        if not ids or len(ids) == 0:
            logger.error({
                "event": "insertion_failed",
                "reason": "empty_ids_list",
                "chunks_count": len(chunks)
            })
            raise ValueError(
                "Operazione di inserimento fallita: nessun chunk inserito nel vector store"
            )
        
        # Verifica coerenza
        if len(ids) != len(chunks):
            logger.warning({
                "event": "partial_insertion",
                "inserted": len(ids),
                "expected": len(chunks)
            })
        
        timing_metrics["total_ms"] = int((time.time() - start_total) * 1000)
        
        logger.info({
            "event": "indexing_complete",
            "inserted_count": len(ids),
            "timing": timing_metrics
        })
        
        return len(ids)
        
    except openai.AuthenticationError as e:
        logger.error({
            "event": "openai_auth_failed",
            "error": str(e)
        })
        raise
        
    except ValueError as e:
        logger.error({
            "event": "validation_failed",
            "error": str(e)
        })
        raise
        
    except Exception as e:
        error_msg = str(e)
        
        if "Error inserting: No rows added" in error_msg:
            logger.error({
                "event": "supabase_insertion_rejected",
                "error": error_msg,
                "troubleshooting": "Verificare: 1) Connessione DB, 2) Permessi tabella, 3) Schema"
            })
        else:
            logger.error({
                "event": "indexing_error",
                "error_type": type(e).__name__,
                "error": str(e)
            })
        
        raise
    finally:
        # Log timing metrics anche in caso di errore
        if timing_metrics:
            logger.info({
                "event": "indexing_metrics",
                "timing": timing_metrics
            })


