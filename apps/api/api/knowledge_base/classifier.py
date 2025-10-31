"""
Enhanced content classification con domini fisioterapici.

Story 2.5: Intelligent Document Preprocessing & Pipeline Completion
AC2
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..config import Settings, get_settings

from ..ingestion.models import (
    EnhancedClassificationOutput,
)
from .classification_cache import get_classification_cache

logger = logging.getLogger("api")


def _get_llm(settings: Optional[Settings] = None) -> BaseLanguageModel:
    """Istanzia model LLM per classification.

    GPT-5 nano accetta esclusivamente la temperatura di default (=1).
    """
    resolved_settings = settings or get_settings()

    client_args = {
        "api_key": resolved_settings.openai_api_key,
    }

    if resolved_settings.openai_base_url:
        client_args["base_url"] = resolved_settings.openai_base_url

    # Story 6.2 Fix: Skip project parameter - not supported by all OpenAI endpoints
    # User can configure via OPENAI_PROJECT env but we don't pass to ChatOpenAI
    # to avoid "Completions.create() got an unexpected keyword argument 'project'" error

    if not resolved_settings.llm_config_refactor_enabled:
        logger.warning({
            "event": "classifier_llm_feature_flag_disabled",
            "fallback_model": "gpt-5-nano",
            "fallback_temperature": 1,
        })
        return ChatOpenAI(model="gpt-5-nano", temperature=1, **client_args)

    temperature = resolved_settings.openai_temperature_classification
    log_payload: Dict[str, Any] = {
        "event": "classifier_llm_initialized",
        "model": resolved_settings.openai_model,
        "temperature": temperature,
        "source": "settings",
    }
    if resolved_settings.openai_base_url:
        log_payload["base_url"] = resolved_settings.openai_base_url
    # project not logged - see comment above about endpoint compatibility
    logger.info(log_payload)
    return ChatOpenAI(
        model=resolved_settings.openai_model,
        temperature=temperature,
        **client_args,
    )


def _apply_metadata_features(
    result: EnhancedClassificationOutput,
    has_images: bool,
    has_tables: bool,
) -> None:
    """Ensure metadata-derived flags are reflected on the result."""
    if not result.detected_features:
        result.detected_features = {}
    result.detected_features["has_images"] = has_images
    result.detected_features["has_tables"] = has_tables


def classify_content_enhanced(
    text: str,
    extraction_metadata: Dict[str, Any] | None = None,
) -> EnhancedClassificationOutput:
    """Classifica contenuto con dominio + struttura (Story 2.5 AC2).

    Args:
        text: Testo documento da classificare
        extraction_metadata: Metadata da extraction (images_count, tables_count)

    Returns:
        EnhancedClassificationOutput con domain, structure_type, confidence, reasoning
    """
    metadata = extraction_metadata or {}
    has_images = metadata.get("images_count", 0) > 0
    has_tables = metadata.get("tables_count", 0) > 0

    cache = get_classification_cache()
    lookup_started = time.perf_counter()
    cached_result = cache.get(text, metadata)
    lookup_latency_ms = (time.perf_counter() - lookup_started) * 1000

    if cached_result:
        _apply_metadata_features(cached_result, has_images, has_tables)
        cache.record_latency(lookup_latency_ms, cached=True)
        return cached_result

    parser = PydanticOutputParser(pydantic_object=EnhancedClassificationOutput)
    template = """
Analizza il seguente documento medico-fisioterapico e classifica:

1. DOMINIO CONTENUTO (scegli uno):
   - fisioterapia_clinica: casi clinici, trattamenti specifici
   - anatomia: strutture anatomiche, biomeccanica
   - patologia: descrizioni patologie muscoloscheletriche
   - esercizi_riabilitativi: protocolli esercizi terapeutici
   - valutazione_diagnostica: test clinici, assessment
   - evidence_based: paper scientifici, RCT, revisioni sistematiche
   - divulgativo: materiale educativo per pazienti
   - tecnico_generico: altro contenuto tecnico

2. TIPO STRUTTURA (scegli uno):
   - TESTO_ACCADEMICO_DENSO
   - PAPER_SCIENTIFICO_MISTO
   - DOCUMENTO_TABELLARE

3. FEATURE RILEVATE (indica presenza):
   - has_images: presenza immagini/diagrammi (gia rilevato: {has_images})
   - has_tables: presenza tabelle dati (gia rilevato: {has_tables})
   - has_references: presenza bibliografia
   - has_clinical_cases: presenza casi clinici

TESTO DA ANALIZZARE:
{text}

{format_instructions}
""".strip()

    prompt = PromptTemplate(
        template=template,
        input_variables=["text"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
            "has_images": has_images,
            "has_tables": has_tables,
        },
    )

    llm = _get_llm()
    chain = prompt | llm | parser

    try:
        classification_started = time.perf_counter()
        result: EnhancedClassificationOutput = chain.invoke({"text": text})
        classification_latency_ms = (
            time.perf_counter() - classification_started
        ) * 1000

        _apply_metadata_features(result, has_images, has_tables)

        cache.set(text, metadata, result)
        cache.record_latency(classification_latency_ms, cached=False)

        logger.info(
            {
                "event": "classification_complete",
                "domain": result.domain.value,
                "structure": result.structure_type.value,
                "confidence": result.confidence,
                "features": result.detected_features,
                "latency_ms": classification_latency_ms,
                "cache_enabled": cache.enabled,
            }
        )

        return result
    except Exception as exc:
        logger.error({"event": "classification_error", "error": str(exc)})
        raise
