from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from ..config import Settings, get_settings
from ..ingestion.watcher_metrics import (
    format_metrics_for_prometheus,
    get_watcher_metrics_snapshot,
)

router = APIRouter(prefix="/metrics", tags=["monitoring"])


@router.get(
    "/watcher",
    summary="Watcher ingestion metrics",
    description="Ritorna le metriche della pipeline watcher in formato JSON (default) o Prometheus.",
)
def watcher_metrics(
    format: str = Query("json", regex="^(json|prometheus)$"),
    settings: Settings = Depends(get_settings),
):
    snapshot = get_watcher_metrics_snapshot(settings)
    if format == "prometheus":
        return PlainTextResponse(
            format_metrics_for_prometheus(snapshot),
            media_type="text/plain",
        )
    return snapshot
