from __future__ import annotations

import os
from typing import Dict, Any, List

from celery import Celery

# Configurazione Celery (broker/backend da env, default Redis locale)
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))

celery_app = Celery(
    "api",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# Serializer sicuri
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
    name="kb_indexing_task",
)
def kb_indexing_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task Celery per indicizzazione chunk nella knowledge base.

    Payload atteso:
      - chunks: List[str]
      - metadata_list: Optional[List[Dict[str, Any]]]
      - document_id: Optional[str]
    """
    # Import locale per evitare dipendenze a import-time lato worker
    from .knowledge_base.indexer import index_chunks

    chunks: List[str] = payload.get("chunks") or []
    metadata_list = payload.get("metadata_list")
    document_id = payload.get("document_id")
    inserted = index_chunks(chunks, metadata_list)
    return {"inserted": inserted, "document_id": document_id}


