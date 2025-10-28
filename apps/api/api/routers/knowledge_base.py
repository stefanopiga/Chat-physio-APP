"""
Knowledge Base router - Gestisce classification, search, sync jobs.

Endpoints:
- POST /classify - Document classification (Story 2.2)
- POST /api/v1/knowledge-base/search - Semantic search (Story 2.4)
- POST /api/v1/admin/knowledge-base/sync-jobs - Start sync job (Story 2.4, 2.5)
- GET /api/v1/admin/knowledge-base/sync-jobs/{job_id} - Job status (Story 2.4)

Stories: 2.2, 2.4, 2.5
"""
import os
import time
import json
import hashlib
import logging
from typing import Annotated, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
import asyncpg

from ..schemas.knowledge_base import (
    ClassifyRequest,
    ClassifyResponse,
    SearchRequest,
    SearchResponse,
    StartSyncJobRequest,
    StartSyncJobResponse,
    SyncJobStatusResponse,
)
from ..dependencies import _auth_bridge, TokenPayload, _is_admin, get_db_connection
from ..knowledge_base.search import perform_semantic_search
from ..knowledge_base.indexer import index_chunks
from ..ingestion.models import ClassificazioneOutput, DocumentStructureCategory
from ..ingestion.chunk_router import ChunkRouter
from ..ingestion.db_storage import save_document_to_db, update_document_status
from ..stores import sync_jobs_store
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

# Celery setup
CELERY_ENABLED = os.getenv("CELERY_ENABLED", "false").lower() in {"1", "true", "yes"}
if CELERY_ENABLED:
    try:
        from celery.result import AsyncResult
        from ..celery_app import celery_app, kb_indexing_task
    except Exception:  # pragma: no cover - fallback se Celery non disponibile
        CELERY_ENABLED = False

# Split routers: /classify root-level, altri endpoint con prefix
router_classify = APIRouter(tags=["Knowledge Base - Classification"])
router = APIRouter(prefix="/api/v1", tags=["Knowledge Base"])
logger = logging.getLogger("api")


def _build_classification_chain(llm) -> Runnable:
    """
    Costruisce chain LangChain per classificazione documenti.
    
    Args:
        llm: Language model instance
        
    Returns:
        Runnable chain per classificazione
    """
    parser = PydanticOutputParser(pydantic_object=ClassificazioneOutput)
    categories = ", ".join([
        DocumentStructureCategory.TESTO_ACCADEMICO_DENSO.value,
        DocumentStructureCategory.PAPER_SCIENTIFICO_MISTO.value,
        DocumentStructureCategory.DOCUMENTO_TABELLARE.value,
    ])
    template = (
        """
Analizza il seguente documento medico-scientifico e restituisci una classificazione strutturale.
Scegli UNA sola categoria tra: {categories}.

Documento:
{testo}

{format_instructions}
"""
    )
    prompt = PromptTemplate(
        template=template,
        input_variables=["testo"],
        partial_variables={
            "categories": categories,
            "format_instructions": parser.get_format_instructions(),
        },
    )
    chain: Runnable = prompt | llm | parser
    return chain


def _get_llm():
    """
    Istanzia language model per classificazione strutturale.

    Nota:
        `gpt-5-nano` accetta solo la temperatura di default (1.0). Passare esplicitamente
        `temperature=0` genera un errore \"Unsupported value: temperature\". Lasciamo quindi
        il valore di default per garantire compatibilita con il modello approvato.
    """
    return ChatOpenAI(model="gpt-5-nano")


@router_classify.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    """
    Document classification endpoint (Story 2.2).
    
    Classifica documento in categoria strutturale per ottimizzazione
    strategia chunking.
    
    Args:
        req: ClassifyRequest con testo documento
        
    Returns:
        ClassifyResponse con classificazione, motivazione, confidenza
        
    Security:
        - No authentication (public endpoint)
    
    Note:
        Router dedicato per endpoint root-level /classify (Story 5.3)
    """
    if not req.testo or not req.testo.strip():
        raise HTTPException(status_code=400, detail="testo mancante")
    
    # Per test: consente mocking della chain via dependency override/monkeypatch.
    try:
        llm = _get_llm()
        chain = _build_classification_chain(llm)
        result: ClassificazioneOutput = chain.invoke({"testo": req.testo})
    except HTTPException:
        # Se LLM non configurato, simuliamo minimo comportamento coerente con struttura per evitare crash locali.
        # I test useranno comunque mocking della catena.
        result = ClassificazioneOutput(
            classificazione=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
            motivazione="fallback",
            confidenza=0.5,
        )
    
    logger.info({
        "event": "classify_result",
        "output": json.loads(result.model_dump_json()),
    })
    return ClassifyResponse(**result.model_dump())


@router.post("/knowledge-base/search", response_model=SearchResponse)
def semantic_search_endpoint(body: SearchRequest, request: Request):
    """
    Semantic search endpoint (Story 2.4).
    
    Esegue ricerca semantica sui chunk indicizzati.
    
    Args:
        body: SearchRequest con query e match_count
        request: FastAPI Request
        
    Returns:
        SearchResponse con risultati
        
    Security:
        - No authentication (public endpoint)
        - Rate limiting: 60/minute (gestito da SlowAPI su main.app)
    """
    results = perform_semantic_search(
        body.query,
        body.match_count,
        body.match_threshold,
    )
    return SearchResponse(results=results)


@router.post("/admin/knowledge-base/sync-jobs", response_model=StartSyncJobResponse)
async def start_sync_job(
    request: Request,
    body: StartSyncJobRequest,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Start document sync job endpoint (Story 2.4 + 2.5).
    
    Enhanced sync job con full pipeline monitoring.
    
    Pipeline Steps (logged con timing):
    1. Enhanced extraction (con images/tables) se source_path fornito
    2. Enhanced classification (domain + structure)
    3. Polymorphic chunking
    4. Document persistence
    5. Batch embedding (con retry)
    6. Vector indexing
    7. Status update
    
    Args:
        request: FastAPI Request
        body: StartSyncJobRequest con document_text, metadata, classification
        conn: Database connection
        payload: JWT payload verificato
        
    Returns:
        StartSyncJobResponse con job_id, inserted count, timing metrics
        
    Security:
        - Admin-only access
        - Rate limiting: 10/minute (gestito da SlowAPI su main.app)
        
    Stories: 2.4.1 Document Persistence + 2.5 Enhanced Pipeline
    """
    from ..knowledge_base.extractors import DocumentExtractor
    from ..knowledge_base.classifier import classify_content_enhanced
    
    start_pipeline = time.time()
    timing_metrics = {}
    
    if not _is_admin(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")
    
    if not body.document_text or not body.document_text.strip():
        raise HTTPException(status_code=400, detail="document_text mancante")
    
    # Step 1: Enhanced extraction (se file_path fornito)
    extraction_result = None
    file_path_str = (body.metadata or {}).get("source_path")
    if file_path_str:
        start_extract = time.time()
        try:
            extractor = DocumentExtractor()
            extraction_result = extractor.extract(Path(file_path_str))
            document_text = extraction_result["text"]
            timing_metrics["extraction_ms"] = int((time.time() - start_extract) * 1000)
            
            # Update metadata con extracted features
            body.metadata["images_count"] = len(extraction_result["images"])
            body.metadata["tables_count"] = len(extraction_result["tables"])
            
            logger.info({
                "event": "extraction_complete",
                "images_count": body.metadata["images_count"],
                "tables_count": body.metadata["tables_count"],
                "duration_ms": timing_metrics["extraction_ms"]
            })
        except Exception as e:
            logger.warning({
                "event": "extraction_failed_fallback",
                "source_path": file_path_str,
                "error": str(e)
            })
            document_text = body.document_text
    else:
        document_text = body.document_text
    
    # Step 2: Enhanced classification (domain + structure)
    start_classify = time.time()
    try:
        extraction_metadata = extraction_result.get("metadata") if extraction_result else None
        classification_enhanced = classify_content_enhanced(
            document_text,
            extraction_metadata
        )
        timing_metrics["classification_ms"] = int((time.time() - start_classify) * 1000)
        
        # Update metadata con classification results
        body.metadata["domain"] = classification_enhanced.domain.value
        body.metadata["structure_type"] = classification_enhanced.structure_type.value
        body.metadata["classification_confidence"] = classification_enhanced.confidence
        
        logger.info({
            "event": "classification_complete",
            "domain": classification_enhanced.domain.value,
            "structure": classification_enhanced.structure_type.value,
            "confidence": classification_enhanced.confidence,
            "duration_ms": timing_metrics["classification_ms"]
        })
    except Exception as e:
        # Fallback classification base se enhanced fallisce
        logger.warning({
            "event": "enhanced_classification_fallback",
            "error": str(e)
        })
        classification_enhanced = None
    
    # Step 3: Chunking
    start_chunk = time.time()
    router_chunking = ChunkRouter()
    
    # Use enhanced classification se disponibile, altrimenti base classification
    classification_for_chunking = None
    if classification_enhanced:
        # Convert enhanced classification to base format per ChunkRouter
        classification_for_chunking = ClassificazioneOutput(
            classificazione=classification_enhanced.structure_type,
            motivazione=classification_enhanced.reasoning,
            confidenza=classification_enhanced.confidence
        )
    elif body.classification:
        classification_for_chunking = body.classification
    
    chunks_result = router_chunking.route(
        content=document_text,
        classification=classification_for_chunking
    )
    timing_metrics["chunking_ms"] = int((time.time() - start_chunk) * 1000)
    
    logger.info({
        "event": "chunking_complete",
        "chunks_count": len(chunks_result.chunks),
        "strategy": chunks_result.strategy_name,
        "strategy_params": chunks_result.parameters or {},
        "duration_ms": timing_metrics["chunking_ms"]
    })
    
    # Step 4: Document persistence
    file_hash = hashlib.sha256(document_text.encode('utf-8')).hexdigest()
    document_name = (body.metadata or {}).get("document_name", "manual_upload.txt")
    file_path = (body.metadata or {}).get("file_path", "")
    
    document_id = await save_document_to_db(
        conn=conn,
        file_name=document_name,
        file_path=file_path,
        file_hash=file_hash,
        status="processing",
        chunking_strategy=chunks_result.strategy_name,
        metadata=body.metadata or {},
    )
    
    # Step 5-6: Indexing (embedding + vector storage)
    metadata_list = []
    base_metadata = body.metadata or {}
    strategy_params = chunks_result.parameters or {}
    for idx, chunk in enumerate(chunks_result.chunks):
        metadata_list.append({
            **base_metadata,
            "document_id": str(document_id),
            "document_name": document_name,
            "chunking_strategy": chunks_result.strategy_name,
            "chunk_index": idx,
            "chunk_size": len(chunk),
            "chunk_size_target": strategy_params.get("chunk_size"),
            "chunk_overlap": strategy_params.get("chunk_overlap"),
        })
    
    if CELERY_ENABLED:
        # Enqueue async task (Celery handles persistence and status updates)
        task = kb_indexing_task.delay({
            "chunks": chunks_result.chunks,
            "metadata_list": metadata_list,
            "document_id": str(document_id),
        })
        
        timing_metrics["total_pipeline_ms"] = int((time.time() - start_pipeline) * 1000)
        
        return StartSyncJobResponse(
            job_id=str(task.id),
            document_id=str(document_id),
            inserted=None,
            timing=timing_metrics
        )
    else:
        # Synchronous indexing
        job_id_str = str(document_id)
        sync_jobs_store[job_id_str] = {
            "status": "running",
            "inserted": 0,
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            inserted = index_chunks(chunks_result.chunks, metadata_list)
            sync_jobs_store[job_id_str]["inserted"] = inserted
            sync_jobs_store[job_id_str]["status"] = "completed"
            
            # Step 7: Update document status
            await update_document_status(conn, document_id, status="completed")
            
            timing_metrics["total_pipeline_ms"] = int((time.time() - start_pipeline) * 1000)
            
            logger.info({
                "event": "pipeline_complete",
                "document_id": str(document_id),
                "chunks_count": len(chunks_result.chunks),
                "inserted": inserted,
                "timing": timing_metrics
            })
            
        except Exception as exc:
            sync_jobs_store[job_id_str]["status"] = "failed"
            sync_jobs_store[job_id_str]["error"] = str(exc)
            
            await update_document_status(conn, document_id, status="error", error=str(exc))
            
            logger.error({
                "event": "pipeline_failed",
                "document_id": str(document_id),
                "error": str(exc),
                "timing": timing_metrics
            })
            
            raise HTTPException(status_code=500, detail="indexing_failed") from exc
        
        return StartSyncJobResponse(
            job_id=job_id_str,
            inserted=sync_jobs_store[job_id_str]["inserted"],
            document_id=str(document_id),
            timing=timing_metrics
        )


@router.get("/admin/knowledge-base/sync-jobs/{job_id}", response_model=SyncJobStatusResponse)
def get_sync_job_status(
    request: Request,
    job_id: str,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Get sync job status endpoint (Story 2.4).
    
    Recupera status di sync job tramite job_id.
    
    Args:
        request: FastAPI Request
        job_id: Job identifier (document_id)
        payload: JWT payload verificato
        
    Returns:
        SyncJobStatusResponse con status, inserted count, error
        
    Security:
        - Admin-only access
        - Rate limiting: 10/minute (gestito da SlowAPI su main.app)
    """
    if not _is_admin(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")
    
    if CELERY_ENABLED:
        try:
            r = AsyncResult(job_id, app=celery_app)
            body = {
                "job_id": job_id,
                "status": r.state,
                "inserted": None,
                "error": None,
                "document_id": None,
            }
            if r.successful():
                result = r.get(propagate=False)  # dict con {inserted}
                if isinstance(result, dict):
                    body["inserted"] = result.get("inserted")
                    body["document_id"] = result.get("document_id")
            elif r.failed():
                body["error"] = str(r.result)
            return SyncJobStatusResponse(**body)
        except Exception as exc:
            # Fallback 404 se AsyncResult non disponibile/errore
            raise HTTPException(status_code=404, detail="job_not_found") from exc
    else:
        job = sync_jobs_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")
        
        return SyncJobStatusResponse(
            job_id=job_id,
            status=str(job.get("status")),
            inserted=job.get("inserted"),
            error=job.get("error"),
            document_id=str(job_id),
        )

