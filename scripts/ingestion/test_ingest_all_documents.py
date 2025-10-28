#!/usr/bin/env python3
"""
Unit tests for batch ingestion script.
"""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

# Import the module to test
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ingest_all_documents import (
    preflight_check,
    extract_text_from_file,
    prepare_payload,
    find_documents,
    IngestionState,
    IngestionResult,
    generate_reports,
    ingest_document,
)


class TestPreflightCheck:
    """Test preflight environment check."""

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "SUPABASE_JWT_SECRET": "test-secret",
        },
    )
    def test_preflight_check_success(self):
        """Test preflight check with all required vars."""
        assert preflight_check() is True
    
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key",  # Alternative name
            "SUPABASE_JWT_SECRET": "test-secret",
        },
    )
    def test_preflight_check_success_alt_key_name(self):
        """Test preflight check with alternative service key name."""
        assert preflight_check() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_preflight_check_missing_vars(self):
        """Test preflight check with missing vars."""
        assert preflight_check() is False

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            # Missing other vars
        },
        clear=True,
    )
    def test_preflight_check_partial_vars(self):
        """Test preflight check with some missing vars."""
        assert preflight_check() is False


class TestTextExtraction:
    """Test text extraction from various file formats."""

    def test_extract_text_from_txt(self, tmp_path):
        """Test extracting text from .txt file."""
        test_file = tmp_path / "test.txt"
        content = "This is a test document.\nWith multiple lines."
        test_file.write_text(content, encoding="utf-8")

        result = extract_text_from_file(test_file)
        assert result == content

    def test_extract_text_from_md(self, tmp_path):
        """Test extracting text from .md file."""
        test_file = tmp_path / "test.md"
        content = "# Test Markdown\n\nThis is a test."
        test_file.write_text(content, encoding="utf-8")

        result = extract_text_from_file(test_file)
        assert result == content

    @patch("ingest_all_documents.Document")
    def test_extract_text_from_docx(self, mock_doc_class, tmp_path):
        """Test extracting text from .docx file."""
        test_file = tmp_path / "test.docx"
        test_file.touch()  # Create empty file

        # Mock Document class
        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "Paragraph 1"
        mock_para2 = MagicMock()
        mock_para2.text = "Paragraph 2"
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc_class.return_value = mock_doc

        result = extract_text_from_file(test_file)
        assert result == "Paragraph 1\nParagraph 2"

    def test_extract_text_unsupported_format(self, tmp_path):
        """Test extracting text from unsupported format."""
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text_from_file(test_file)


class TestPayloadPreparation:
    """Test payload preparation."""

    def test_prepare_payload(self, tmp_path):
        """Test payload preparation with correct structure."""
        # Create test file structure
        category_dir = tmp_path / "fisioterapia" / "lombare"
        category_dir.mkdir(parents=True)
        test_file = category_dir / "test_doc.docx"
        test_file.write_text("test content")

        document_text = "This is the document content"

        with patch("ingest_all_documents.project_root", tmp_path):
            payload = prepare_payload(test_file, document_text, "fisioterapia")

        assert payload["document_text"] == document_text
        assert "metadata" in payload
        assert payload["metadata"]["document_name"] == "test_doc.docx"
        assert payload["metadata"]["category"] == "fisioterapia"
        assert payload["metadata"]["topic"] == "lombare"
        assert "source_path" in payload["metadata"]
        assert "ingestion_batch" in payload["metadata"]
        assert "file_size" in payload["metadata"]


class TestDocumentFinding:
    """Test document discovery."""

    def test_find_documents(self, tmp_path):
        """Test finding documents with pattern."""
        # Create test files
        (tmp_path / "doc1.docx").touch()
        (tmp_path / "doc2.docx").touch()
        (tmp_path / "doc3.txt").touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "doc4.docx").touch()

        # Find .docx files
        results = find_documents(tmp_path, "*.docx")

        assert len(results) == 3
        assert all(f.suffix == ".docx" for f in results)

    def test_find_documents_no_matches(self, tmp_path):
        """Test finding documents with no matches."""
        (tmp_path / "doc1.txt").touch()

        results = find_documents(tmp_path, "*.docx")
        assert len(results) == 0


class TestIngestionState:
    """Test state management for resume capability."""

    def test_state_initialization(self, tmp_path):
        """Test state initialization."""
        state_file = tmp_path / "state.json"
        state = IngestionState(state_file)

        assert len(state.processed_files) == 0

    def test_state_mark_and_check(self, tmp_path):
        """Test marking files as processed."""
        state_file = tmp_path / "state.json"
        state = IngestionState(state_file)

        file_path = "conoscenza/fisioterapia/test.docx"
        assert not state.is_processed(file_path)

        state.mark_processed(file_path)
        assert state.is_processed(file_path)

    def test_state_persistence(self, tmp_path):
        """Test state persistence across instances."""
        state_file = tmp_path / "state.json"

        # First instance
        state1 = IngestionState(state_file)
        state1.mark_processed("file1.docx")
        state1.mark_processed("file2.docx")

        # Second instance should load the state
        state2 = IngestionState(state_file)
        assert state2.is_processed("file1.docx")
        assert state2.is_processed("file2.docx")
        assert not state2.is_processed("file3.docx")

    def test_state_corrupted_file(self, tmp_path):
        """Test handling of corrupted state file."""
        state_file = tmp_path / "state.json"
        state_file.write_text("invalid json{{{")

        # Should not crash, just start fresh
        state = IngestionState(state_file)
        assert len(state.processed_files) == 0


class TestIngestionResult:
    """Test ingestion result dataclass."""

    def test_result_creation(self):
        """Test creating ingestion result."""
        result = IngestionResult(
            file_path="test.docx",
            status="success",
            job_id="job-123",
            inserted_chunks=10,
            latency_ms=1500.0,
        )

        assert result.file_path == "test.docx"
        assert result.status == "success"
        assert result.job_id == "job-123"
        assert result.inserted_chunks == 10
        assert result.latency_ms == 1500.0
        assert result.timestamp  # Should be auto-generated

    def test_result_failed(self):
        """Test creating failed result."""
        result = IngestionResult(
            file_path="test.docx", status="failed", error="Network timeout"
        )

        assert result.status == "failed"
        assert result.error == "Network timeout"
        assert result.job_id is None


class TestReportGeneration:
    """Test report generation."""

    def test_generate_reports(self, tmp_path):
        """Test generating all report formats."""
        results = [
            IngestionResult(
                file_path="doc1.docx",
                status="success",
                job_id="job-1",
                inserted_chunks=10,
                latency_ms=1000.0,
            ),
            IngestionResult(
                file_path="doc2.docx",
                status="success",
                job_id="job-2",
                inserted_chunks=15,
                latency_ms=1200.0,
            ),
            IngestionResult(
                file_path="doc3.docx", status="failed", error="Timeout"
            ),
        ]

        start_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 1, 12, 10, 0, tzinfo=timezone.utc)

        report_path = tmp_path / "reports" / "test_report"

        generate_reports(results, report_path, start_time, end_time)

        # Check all formats were created
        assert (tmp_path / "reports" / "test_report.md").exists()
        assert (tmp_path / "reports" / "test_report.json").exists()
        assert (tmp_path / "reports" / "test_report.csv").exists()

        # Verify JSON content
        with open(tmp_path / "reports" / "test_report.json") as f:
            data = json.load(f)

        assert data["summary"]["total"] == 3
        assert data["summary"]["success"] == 2
        assert data["summary"]["failed"] == 1
        assert data["summary"]["total_chunks"] == 25

        # Verify CSV format
        csv_content = (tmp_path / "reports" / "test_report.csv").read_text()
        assert "file_path,status,job_id" in csv_content
        assert '"doc1.docx",success,job-1' in csv_content

        # Verify Markdown format
        md_content = (tmp_path / "reports" / "test_report.md").read_text()
        assert "# Batch Ingestion Report" in md_content
        assert "**Success:** 2" in md_content
        assert "**Failed:** 1" in md_content


class TestAPIIngestion:
    """Test API ingestion with retry logic."""

    @patch("ingest_all_documents.requests.post")
    def test_ingest_document_success(self, mock_post):
        """Test successful document ingestion."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-123",
            "inserted": 10,
            "status": "completed",
        }
        mock_post.return_value = mock_response

        result = ingest_document(
            api_url="http://localhost/api/sync-jobs",
            jwt_token="test-token",
            payload={"document_text": "test"},
            max_retries=3,
        )

        assert result["job_id"] == "job-123"
        assert result["inserted"] == 10

    @patch("ingest_all_documents.requests.post")
    def test_ingest_document_rate_limit_retry(self, mock_post):
        """Test retry on 429 rate limit."""
        # First call returns 429, second succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "2"}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"job_id": "job-123"}

        mock_post.side_effect = [mock_response_429, mock_response_200]

        with patch("ingest_all_documents.time.sleep"):  # Mock sleep to speed up test
            result = ingest_document(
                api_url="http://localhost/api/sync-jobs",
                jwt_token="test-token",
                payload={"document_text": "test"},
                max_retries=3,
            )

        assert result["job_id"] == "job-123"
        assert mock_post.call_count == 2

    @patch("ingest_all_documents.requests.post")
    def test_ingest_document_server_error_retry(self, mock_post):
        """Test retry on 5xx server error."""
        # First call returns 500, second succeeds
        mock_response_500 = Mock()
        mock_response_500.status_code = 500

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"job_id": "job-123"}

        mock_post.side_effect = [mock_response_500, mock_response_200]

        with patch("ingest_all_documents.time.sleep"):
            result = ingest_document(
                api_url="http://localhost/api/sync-jobs",
                jwt_token="test-token",
                payload={"document_text": "test"},
                max_retries=3,
            )

        assert result["job_id"] == "job-123"
        assert mock_post.call_count == 2

    @patch("ingest_all_documents.requests.post")
    def test_ingest_document_max_retries_exceeded(self, mock_post):
        """Test failure after max retries."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with patch("ingest_all_documents.time.sleep"):
            with pytest.raises(Exception, match="Max retries"):
                ingest_document(
                    api_url="http://localhost/api/sync-jobs",
                    jwt_token="test-token",
                    payload={"document_text": "test"},
                    max_retries=2,
                )

        assert mock_post.call_count == 2

    @patch("ingest_all_documents.requests.post")
    def test_ingest_document_auth_error_no_retry(self, mock_post):
        """Test no retry on 401 auth error."""
        mock_response = Mock()
        mock_response.status_code = 401
        
        # Create HTTPError with response attribute (like real requests does)
        http_error = requests.HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        
        mock_post.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            ingest_document(
                api_url="http://localhost/api/sync-jobs",
                jwt_token="bad-token",
                payload={"document_text": "test"},
                max_retries=3,
            )

        # Should not retry on 401
        assert mock_post.call_count == 1

    @patch("ingest_all_documents.requests.post")
    def test_ingest_document_timeout_retry(self, mock_post):
        """Test retry on request timeout."""
        # First call times out, second succeeds
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"job_id": "job-123"}

        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            mock_response_200,
        ]

        with patch("ingest_all_documents.time.sleep"):
            result = ingest_document(
                api_url="http://localhost/api/sync-jobs",
                jwt_token="test-token",
                payload={"document_text": "test"},
                max_retries=3,
            )

        assert result["job_id"] == "job-123"
        assert mock_post.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

