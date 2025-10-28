from __future__ import annotations
from typing import List
from .strategy import ChunkingStrategy, ChunkingResult


class TabularStructuralStrategy(ChunkingStrategy):
    """
    Placeholder modulare per documenti tabellari/strutturati.
    Implementazione semplice: split per doppie nuove linee, con fallback su newline singola.
    """

    def __init__(self, min_section_len: int = 200):
        self._min_section_len = min_section_len

    @property
    def name(self) -> str:
        return "tabular_structural"

    def _greedy_sections(self, content: str) -> List[str]:
        raw = [s.strip() for s in (content or "").split("\n\n")]
        sections: List[str] = []
        buffer: List[str] = []
        current_len = 0
        for part in raw:
            if not part:
                continue
            if current_len + len(part) >= self._min_section_len:
                buffer.append(part)
                sections.append("\n".join(buffer))
                buffer = []
                current_len = 0
            else:
                buffer.append(part)
                current_len += len(part)
        if buffer:
            sections.append("\n".join(buffer))
        if len(sections) <= 1:
            # fallback grezzo a righe
            sections = [s for s in (content or "").split("\n") if s.strip()]
        return sections

    def split(self, content: str) -> ChunkingResult:
        chunks = self._greedy_sections(content)
        return ChunkingResult(
            chunks=chunks,
            strategy_name=self.name,
            parameters={"min_section_len": self._min_section_len},
        )
