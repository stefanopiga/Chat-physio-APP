from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class ChunkingResult:
    chunks: List[str]
    strategy_name: str
    parameters: Dict[str, Any] | None = None


class ChunkingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def split(self, content: str) -> ChunkingResult:
        ...
