from __future__ import annotations
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .strategy import ChunkingStrategy, ChunkingResult


class RecursiveCharacterStrategy(ChunkingStrategy):
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 160):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    @property
    def name(self) -> str:
        return f"recursive_character_{self._chunk_size}_{self._chunk_overlap}"

    def split(self, content: str) -> ChunkingResult:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            length_function=len,
        )
        chunks: List[str] = splitter.split_text(content or "")
        return ChunkingResult(
            chunks=chunks,
            strategy_name=self.name,
            parameters={
                "chunk_size": self._chunk_size,
                "chunk_overlap": self._chunk_overlap,
            },
        )
