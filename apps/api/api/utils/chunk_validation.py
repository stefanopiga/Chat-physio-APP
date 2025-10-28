from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple, Union

ChunkRecord = Union[Mapping[str, Any], Any]


def _get_attr(record: ChunkRecord, key: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


def _get_metadata(record: ChunkRecord) -> Mapping[str, Any]:
    metadata = _get_attr(record, "metadata")
    if isinstance(metadata, Mapping):
        return metadata
    return {}


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


@dataclass
class ChunkIntegrityReport:
    duplicate_ids: list[str]
    duplicate_indexes: list[Tuple[str, str]]
    missing_chunk_index: list[str]
    orphaned_chunks: list[str]

    @property
    def is_valid(self) -> bool:
        return not any(
            [
                self.duplicate_ids,
                self.duplicate_indexes,
                self.missing_chunk_index,
                self.orphaned_chunks,
            ]
        )


def analyze_chunk_integrity(
    chunks: Iterable[ChunkRecord],
    documents: Optional[Sequence[ChunkRecord]] = None,
) -> ChunkIntegrityReport:
    """
    Analizza una collezione di chunk e restituisce un report di integrit��.

    Args:
        chunks: Iterable di record chunk (dict, asyncpg.Record, ecc.)
        documents: Iterable opzionale di documenti per verificare chunk orfani

    Returns:
        ChunkIntegrityReport con liste di anomalie individuate.
    """
    duplicate_ids: list[str] = []
    duplicate_indexes: list[Tuple[str, str]] = []
    missing_chunk_index: list[str] = []
    orphaned_chunks: list[str] = []

    seen_ids: dict[str, int] = {}
    seen_indexes: set[Tuple[str, str]] = set()
    duplicates_index_tracker: set[Tuple[str, str]] = set()

    valid_document_ids: set[str] = set()
    if documents:
        for doc in documents:
            doc_id = _as_str(_get_attr(doc, "id"))
            if doc_id:
                valid_document_ids.add(doc_id)

    for record in chunks:
        chunk_id = _as_str(_get_attr(record, "id"))
        document_id = _as_str(_get_attr(record, "document_id"))
        metadata = _get_metadata(record)
        chunk_index = _as_str(metadata.get("chunk_index"))

        if chunk_id:
            seen_ids[chunk_id] = seen_ids.get(chunk_id, 0) + 1

        if document_id and chunk_index is not None:
            key = (document_id, chunk_index)
            if key in seen_indexes and key not in duplicates_index_tracker:
                duplicate_indexes.append(key)
                duplicates_index_tracker.add(key)
            seen_indexes.add(key)

        if chunk_index is None:
            missing_chunk_index.append(chunk_id or "unknown")

        if document_id is None:
            orphaned_chunks.append(chunk_id or "unknown::missing_document")
        elif valid_document_ids and document_id not in valid_document_ids:
            orphaned_chunks.append(chunk_id or f"unknown::{document_id}")

    duplicate_ids = [chunk_id for chunk_id, count in seen_ids.items() if count > 1]
    missing_chunk_index = list(dict.fromkeys(missing_chunk_index))
    orphaned_chunks = list(dict.fromkeys(orphaned_chunks))

    return ChunkIntegrityReport(
        duplicate_ids=duplicate_ids,
        duplicate_indexes=duplicate_indexes,
        missing_chunk_index=missing_chunk_index,
        orphaned_chunks=orphaned_chunks,
    )
