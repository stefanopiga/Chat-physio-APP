from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Literal, Optional

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..database import get_db_connection
from ..knowledge_base import search

router = APIRouter(tags=["Health"])
logger = logging.getLogger("api")


class HealthStatusResponse(BaseModel):
    status: Literal["ok"]


class DependencyStatus(BaseModel):
    name: str
    status: Literal["ok", "error"]
    detail: Optional[str] = None


class HealthDependenciesResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    checks: list[DependencyStatus]


@router.get("/health", response_model=HealthStatusResponse)
async def health() -> HealthStatusResponse:
    """
    Health check basilare per monitoring.
    """
    return HealthStatusResponse(status="ok")


async def _check_supabase_client(settings: Settings) -> tuple[str, Optional[str]]:
    """
    Verifica disponibilit�� del vector store Supabase.
    """
    try:
        client = search._get_supabase_client()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - fallback gestito nel chiamante
        logger.warning(
            {
                "event": "health_supabase_client_init_failed",
                "environment": settings.environment,
                "error": str(exc),
            }
        )
        return "error", f"supabase_client_error: {exc}"

    def _execute_ping() -> None:
        client.table("documents").select("id").limit(1).execute()

    try:
        await asyncio.to_thread(_execute_ping)
        return "ok", None
    except Exception as exc:
        logger.warning(
            {
                "event": "health_supabase_check_failed",
                "environment": settings.environment,
                "error": str(exc),
            }
        )
        return "error", f"supabase_unreachable: {exc}"


@router.get("/health/dependencies", response_model=HealthDependenciesResponse)
async def health_dependencies(
    settings: Annotated[Settings, Depends(get_settings)],
    connection: Annotated[asyncpg.Connection, Depends(get_db_connection)],
) -> HealthDependenciesResponse:
    """
    Health check completo che verifica le dipendenze critiche:
    - Database PostgreSQL
    - Vector store Supabase (pgvector)
    """
    checks: list[DependencyStatus] = []

    # Database check
    db_status = "ok"
    db_detail: Optional[str] = None
    try:
        await connection.fetchval("SELECT 1;")  # type: ignore[func-returns-value]
    except Exception as exc:
        db_status = "error"
        db_detail = str(exc)
        logger.warning(
            {
                "event": "health_db_check_failed",
                "error": db_detail,
            }
        )
    checks.append(DependencyStatus(name="database", status=db_status, detail=db_detail))

    # Supabase/vector store check
    supabase_status, supabase_detail = await _check_supabase_client(settings)
    checks.append(
        DependencyStatus(
            name="vector_store",
            status=supabase_status,
            detail=supabase_detail,
        )
    )

    if all(item.status == "ok" for item in checks):
        status: Literal["ok", "degraded", "error"] = "ok"
    elif any(item.status == "error" for item in checks):
        status = "degraded"
    else:  # pragma: no cover - unreachable con i valori consentiti
        status = "degraded"

    return HealthDependenciesResponse(status=status, checks=checks)
