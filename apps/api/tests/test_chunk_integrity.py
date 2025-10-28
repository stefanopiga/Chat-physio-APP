"""
Test di integrità dei chunk per AC4.
Validano le regole senza dipendere da DATABASE_URL reale.
"""

from __future__ import annotations

import os
from typing import Dict, List

import asyncpg
import pytest

from api.utils.chunk_validation import analyze_chunk_integrity


@pytest.fixture
def sample_documents() -> List[Dict[str, str]]:
    return [
        {"id": "doc-1", "title": "Manuale fisioterapia"},
        {"id": "doc-2", "title": "Linee guida riabilitazione"},
    ]


@pytest.fixture
def sample_chunks() -> List[Dict[str, object]]:
    return [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "content": "Lorem ipsum dolor sit amet.",
            "metadata": {"chunk_index": "0"},
        },
        {
            "id": "chunk-2",
            "document_id": "doc-1",
            "content": "Consectetur adipiscing elit.",
            "metadata": {"chunk_index": "1"},
        },
        {
            "id": "chunk-3",
            "document_id": "doc-2",
            "content": "Sed do eiusmod tempor incididunt.",
            "metadata": {"chunk_index": "0"},
        },
    ]


def test_chunk_integrity_passes_with_valid_dataset(sample_chunks, sample_documents):
    report = analyze_chunk_integrity(sample_chunks, sample_documents)
    assert report.is_valid, f"Integrity report unexpectedly invalid: {report}"
    assert report.duplicate_ids == []
    assert report.duplicate_indexes == []
    assert report.missing_chunk_index == []
    assert report.orphaned_chunks == []


def test_chunk_integrity_detects_duplicate_ids(sample_chunks, sample_documents):
    duplicate_sample = sample_chunks + [
        {
            "id": "chunk-1",
            "document_id": "doc-2",
            "content": "Duplicated chunk id with different document.",
            "metadata": {"chunk_index": "1"},
        }
    ]
    report = analyze_chunk_integrity(duplicate_sample, sample_documents)
    assert report.duplicate_ids == ["chunk-1"]
    assert not report.is_valid


def test_chunk_integrity_detects_duplicate_indexes(sample_chunks, sample_documents):
    duplicate_index_sample = sample_chunks + [
        {
            "id": "chunk-4",
            "document_id": "doc-1",
            "content": "Duplicate index for same document.",
            "metadata": {"chunk_index": "1"},
        }
    ]
    report = analyze_chunk_integrity(duplicate_index_sample, sample_documents)
    assert ("doc-1", "1") in report.duplicate_indexes
    assert not report.is_valid


def test_chunk_integrity_detects_missing_metadata(sample_chunks, sample_documents):
    missing_metadata_sample = sample_chunks + [
        {"id": "chunk-5", "document_id": "doc-2", "content": "No index", "metadata": {}}
    ]
    report = analyze_chunk_integrity(missing_metadata_sample, sample_documents)
    assert "chunk-5" in report.missing_chunk_index
    assert not report.is_valid


def test_chunk_integrity_detects_orphaned_chunks(sample_chunks, sample_documents):
    orphan_sample = sample_chunks + [
        {
            "id": "chunk-6",
            "document_id": "doc-unknown",
            "content": "Unknown document reference",
            "metadata": {"chunk_index": "0"},
        },
        {
            "id": "chunk-7",
            "document_id": None,
            "content": "Missing document id",
            "metadata": {"chunk_index": "1"},
        },
    ]
    report = analyze_chunk_integrity(orphan_sample, sample_documents)
    assert "chunk-6" in report.orphaned_chunks
    assert "chunk-7" in report.orphaned_chunks
    assert not report.is_valid


@pytest.mark.asyncio
@pytest.mark.integration
async def test_chunk_integrity_against_database_snapshot():
    """
    Integration test opzionale per validare dataset reale quando DATABASE_URL è disponibile.
    Story 6.2 fix: aggiunto timeout connessione per evitare blocchi.
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL non configurato, skip integration check")

    try:
        conn = await asyncpg.connect(dsn, statement_cache_size=0, timeout=5.0)
    except Exception as exc:
        pytest.skip(f"DATABASE_URL non raggiungibile: {exc}")

    try:
        chunks = await conn.fetch(
            "SELECT id, document_id, metadata FROM document_chunks LIMIT 1000;"
        )
        documents = await conn.fetch("SELECT id FROM documents;")
    finally:
        await conn.close()

    report = analyze_chunk_integrity(chunks, documents)
    assert report.is_valid, (
        "Chunk integrity violation rilevata sul dataset reale: "
        f"duplicate_ids={report.duplicate_ids}, "
        f"duplicate_indexes={report.duplicate_indexes}, "
        f"missing_chunk_index={report.missing_chunk_index}, "
        f"orphaned_chunks={report.orphaned_chunks}"
    )
