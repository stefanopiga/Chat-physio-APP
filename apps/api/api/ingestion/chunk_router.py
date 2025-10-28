from __future__ import annotations
from typing import Dict, Optional

from .models import ClassificazioneOutput, DocumentStructureCategory
from .chunking.recursive import RecursiveCharacterStrategy
from .chunking.tabular import TabularStructuralStrategy
from .chunking.strategy import ChunkingStrategy, ChunkingResult


CONFIDENZA_SOGLIA_FALLBACK: float = 0.7


class ChunkRouter:
    def __init__(self,
                 recursive: Optional[ChunkingStrategy] = None,
                 tabular: Optional[ChunkingStrategy] = None,
                 fallback: Optional[ChunkingStrategy] = None):
        self._strategies: Dict[str, ChunkingStrategy] = {
            "recursive": recursive or RecursiveCharacterStrategy(),
            "tabular": tabular or TabularStructuralStrategy(),
        }
        # fallback predefinito: uso lo stesso recursive con parametri standard
        self._fallback: ChunkingStrategy = fallback or self._strategies["recursive"]

    def route(self, content: str, classification: Optional[ClassificazioneOutput]) -> ChunkingResult:
        # Applica fallback se classificazione assente o confidenza bassa
        if classification is None or classification.confidenza < CONFIDENZA_SOGLIA_FALLBACK:
            result = self._fallback.split(content)
            return ChunkingResult(
                chunks=result.chunks,
                strategy_name=f"fallback::{result.strategy_name}",
                parameters=result.parameters,
            )

        categoria = classification.classificazione
        if categoria == DocumentStructureCategory.TESTO_ACCADEMICO_DENSO:
            return self._strategies["recursive"].split(content)

        if categoria in (DocumentStructureCategory.DOCUMENTO_TABELLARE, DocumentStructureCategory.PAPER_SCIENTIFICO_MISTO):
            return self._strategies["tabular"].split(content)

        # Fallback per categoria non mappata
        result = self._fallback.split(content)
        return ChunkingResult(
            chunks=result.chunks,
            strategy_name=f"fallback::{result.strategy_name}",
            parameters=result.parameters,
        )
