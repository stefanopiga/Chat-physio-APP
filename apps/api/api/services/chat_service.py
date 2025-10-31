"""
Chat service - Business logic per chat RAG orchestration.

Story: 3.1, 3.2, 3.4
"""
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel

from ..config import Settings, get_settings


# Metriche performance per AG
AG_LATENCY_MAX_SAMPLES = 10000  # Increased for production use
ag_latency_samples_ms: list[int] = []
logger = logging.getLogger("api")


def _percentile(values: list[float], p: float) -> float:
    """Calcola percentile (nearest-rank)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = round((p / 100.0) * (len(ordered) - 1))
    idx = max(0, min(len(ordered) - 1, int(idx)))
    return float(ordered[idx])


def track_ag_latency(duration_ms: int) -> None:
    """
    Registra latenza AG (alias per compatibilità test).
    
    Args:
        duration_ms: Durata AG in millisecondi
    """
    global ag_latency_samples_ms
    
    ag_latency_samples_ms.append(int(duration_ms))
    
    # Mantieni finestra scorrevole
    excess = len(ag_latency_samples_ms) - AG_LATENCY_MAX_SAMPLES
    if excess > 0:
        del ag_latency_samples_ms[:excess]


def get_latency_p95() -> int:
    """
    Ritorna percentile 95 delle latenze AG.
    
    Returns:
        p95 in millisecondi
    """
    if not ag_latency_samples_ms:
        return 0
    return int(_percentile(ag_latency_samples_ms, 95.0))


def get_latency_p50() -> int:
    """
    Ritorna percentile 50 (median) delle latenze AG.

    Returns:
        p50 in millisecondi
    """
    if not ag_latency_samples_ms:
        return 0
    return int(_percentile(ag_latency_samples_ms, 50.0))


def get_latency_p99() -> int:
    """
    Ritorna percentile 99 delle latenze AG.
    
    Returns:
        p99 in millisecondi
    """
    if not ag_latency_samples_ms:
        return 0
    return int(_percentile(ag_latency_samples_ms, 99.0))


def record_ag_latency_ms(duration_ms: int) -> dict:
    """
    Registra latenza AG e ritorna metriche aggiornate.
    
    Args:
        duration_ms: Durata AG in millisecondi
        
    Returns:
        dict con p50_ms, p95_ms e count samples
    """
    track_ag_latency(duration_ms)
    
    return {
        "p50_ms": get_latency_p50(),
        "p95_ms": get_latency_p95(),
        "count": len(ag_latency_samples_ms)
    }


def get_llm(settings: Optional[Settings] = None) -> BaseLanguageModel:
    """
    Istanzia language model per chat orchestration.

    Args:
        settings: Application settings (iniettate via DI; fallback a singleton).

    Returns:
        ChatOpenAI instance configurato per AG.
    """
    resolved_settings = settings or get_settings()

    if not resolved_settings.llm_config_refactor_enabled:
        logger.warning({
            "event": "chat_llm_feature_flag_disabled",
            "fallback_model": "gpt-5-nano",
            "reason": "llm_config_refactor_disabled",
        })
        # Story 6.5: Explicit temperature=1.0 for nano (ChatOpenAI default 0.7 causes error)
        return ChatOpenAI(model="gpt-5-nano", temperature=1.0)

    model = resolved_settings.openai_model
    model_kwargs: dict[str, object] = {"model": model}
    
    # gpt-5-nano requires default temperature (1.0) - MUST be explicit
    # Story 6.5 AC1: Set temperature=1.0 explicitly for nano models
    # (ChatOpenAI default is 0.7, which causes API error with nano)
    if "nano" in model.lower():
        model_kwargs["temperature"] = 1.0
        logger.info({
            "event": "chat_llm_nano_default_temperature",
            "model": model,
            "temperature_decision": "explicit_1.0_for_nano",
            "temperature_set": 1.0,
            "reason": "gpt-5-nano requires explicit temperature=1.0 (ChatOpenAI default 0.7 causes error)"
        })
    elif resolved_settings.openai_temperature_chat is not None:
        model_kwargs["temperature"] = resolved_settings.openai_temperature_chat
        logger.info({
            "event": "chat_llm_temperature_override",
            "model": model,
            "temperature": resolved_settings.openai_temperature_chat,
            "source": "settings",
        })

    logger.info({
        "event": "chat_llm_initialized",
        "model": model_kwargs["model"],
        "temperature": model_kwargs.get("temperature", "default"),
        "source": "settings",
    })
    return ChatOpenAI(**model_kwargs)
