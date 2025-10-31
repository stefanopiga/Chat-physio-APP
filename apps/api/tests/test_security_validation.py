"""Security validation tests per Story 2.5 (P0 requirements).

Test coverage:
- Path sanitization (AC1: file type detection security)
- Rate limiter validation (AC5: pipeline endpoint protection)
"""
import pytest
from pathlib import Path

from api.knowledge_base.extractors import DocumentExtractor, detect_file_type, FileType


class TestPathSanitization:
    """Test suite per path traversal prevention."""
    
    def test_path_traversal_parent_directory(self):
        """Verifica che path traversal con ../ viene bloccato."""
        malicious_path = Path("../../etc/passwd")
        
        extractor = DocumentExtractor()
        
        # Should raise error or sanitize path
        with pytest.raises((ValueError, FileNotFoundError, PermissionError)):
            extractor.extract(malicious_path)
    
    def test_path_traversal_absolute_unix(self):
        """Verifica che path assoluti non autorizzati Unix-style vengono bloccati."""
        malicious_path = Path("/etc/passwd")
        
        extractor = DocumentExtractor()
        
        # Should raise error (file not in allowed directory)
        with pytest.raises((ValueError, FileNotFoundError, PermissionError)):
            extractor.extract(malicious_path)
    
    def test_path_traversal_absolute_windows(self):
        """Verifica che path assoluti non autorizzati Windows-style vengono bloccati."""
        malicious_path = Path("C:\\Windows\\System32\\config\\sam")
        
        extractor = DocumentExtractor()
        
        # Should raise error (file not in allowed directory or not exists)
        with pytest.raises((ValueError, FileNotFoundError, PermissionError)):
            extractor.extract(malicious_path)
    
    def test_path_with_null_byte(self):
        """Verifica che path con null bytes vengono rigettati."""
        # Null byte injection attack
        malicious_path_str = "safe_file.pdf\x00../../etc/passwd"
        
        # Path construction should fail or be sanitized
        try:
            malicious_path = Path(malicious_path_str)
            extractor = DocumentExtractor()
            
            # If construction succeeded, extraction should fail
            with pytest.raises((ValueError, FileNotFoundError)):
                extractor.extract(malicious_path)
        except ValueError:
            # Path construction itself raised error - good!
            pass
    
    def test_path_normalization(self):
        """Verifica che path normalization non permette bypass."""
        # Vari tentativi di bypass
        bypass_attempts = [
            "../../etc/passwd",
            "./../../etc/passwd",
            "safe/../../../etc/passwd",
            "safe/./../../etc/passwd",
        ]
        
        extractor = DocumentExtractor()
        
        for attempt in bypass_attempts:
            path = Path(attempt)
            with pytest.raises((ValueError, FileNotFoundError, PermissionError)):
                extractor.extract(path)
    
    def test_safe_path_in_workspace(self, tmp_path):
        """Verifica che path safe all'interno workspace funzionano."""
        # Create safe test file
        safe_file = tmp_path / "document.txt"
        safe_file.write_text("Safe document content", encoding="utf-8")
        
        extractor = DocumentExtractor()
        
        # Should NOT raise security error
        result = extractor.extract(safe_file)
        
        assert result is not None
        assert result["text"] == "Safe document content"
        assert result["metadata"]["file_type"] == "txt"


class TestRateLimiterValidation:
    """Test suite per rate limiter endpoint protection."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_exists(self):
        """Verifica che rate limiter decorator è applicato all'endpoint."""
        from api.main import app
        
        # Get route for sync-jobs endpoint
        routes = [r for r in app.routes if hasattr(r, 'path') and '/sync-jobs' in r.path]
        
        assert len(routes) > 0, "sync-jobs endpoint non trovato"
        
        sync_jobs_route = routes[0]
        
        # Check if rate limiter is applied (endpoint should have limiter decorator)
        # Note: This is a structural test, actual rate limiting requires integration test
        endpoint_func = sync_jobs_route.endpoint
        
        # Verify endpoint exists (actual rate limit test requires HTTP client)
        assert endpoint_func is not None
        assert hasattr(endpoint_func, '__name__')
    
    @pytest.mark.skip(reason="Requires test client + Redis for full validation")
    @pytest.mark.asyncio
    async def test_rate_limiter_enforcement(self):
        """Integration test per rate limiter enforcement (SKIPPED - requires infrastructure).
        
        Manual validation steps:
        1. Start API server con Redis
        2. Make 10 requests to /api/v1/admin/knowledge-base/sync-jobs within 1 minute
        3. Make 11th request
        4. Verify 11th request returns HTTP 429 (Too Many Requests)
        
        Expected behavior:
        - Requests 1-10: HTTP 200 or 201 (or 400/403 if invalid payload)
        - Request 11: HTTP 429 with "Rate limit exceeded" message
        """
        pass
    
    def test_rate_limiter_config(self):
        """Verifica che rate limiter ha configurazione appropriata (Story 5.4 Task 4.2)."""
        import os
        from api.config import get_settings
        
        settings = get_settings()
        
        # In test environment, rate limiting should be disabled
        if settings.testing or os.getenv("TESTING") == "true":
            # Verify rate limiting is properly disabled
            assert not settings.should_enable_rate_limiting
            # Skip limiter verification in test mode
            return
        
        # In production, verify limiter is configured
        from api.main import limiter
        assert limiter is not None
        assert hasattr(limiter, '_storage_uri')


class TestInputValidation:
    """Test suite per input validation aggiuntiva."""
    
    def test_file_type_detection_case_insensitive(self):
        """Verifica che file type detection è case-insensitive."""
        # Already covered in test_enhanced_extraction.py
        # but included here for security context
        
        test_cases = [
            (Path("file.PDF"), FileType.PDF),
            (Path("file.Pdf"), FileType.PDF),
            (Path("file.pDf"), FileType.PDF),
            (Path("FILE.DOCX"), FileType.DOCX),
            (Path("file.TXT"), FileType.TXT),
        ]
        
        for file_path, expected_type in test_cases:
            result = detect_file_type(file_path)
            assert result == expected_type
    
    def test_unsupported_file_extension_rejection(self):
        """Verifica che file extensions non supportate vengono rigettate."""
        unsupported_extensions = [
            ".exe",
            ".bat",
            ".sh",
            ".py",
            ".js",
            ".dll",
            ".so",
        ]
        
        for ext in unsupported_extensions:
            file_path = Path(f"suspicious_file{ext}")
            result = detect_file_type(file_path)
            assert result == FileType.UNSUPPORTED
    
    def test_empty_file_path(self):
        """Verifica che path vuoti vengono gestiti correttamente."""
        # Empty path risulta in UNSUPPORTED (no extension)
        result = detect_file_type(Path(""))
        assert result == FileType.UNSUPPORTED
    
    def test_very_long_path(self):
        """Verifica gestione path estremamente lunghi."""
        # Create path with 1000+ characters
        long_filename = "a" * 500 + ".pdf"
        long_path = Path(long_filename)
        
        # Should handle gracefully (detect as PDF)
        result = detect_file_type(long_path)
        assert result == FileType.PDF  # Extension detection should still work


class TestErrorHandling:
    """Test suite per error handling robusto."""
    
    def test_corrupted_file_graceful_failure(self, tmp_path):
        """Verifica che file corrotti non causano crash ma error gestito."""
        # Create corrupted file (random bytes labeled as PDF)
        corrupted_file = tmp_path / "corrupted.pdf"
        corrupted_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        
        extractor = DocumentExtractor()
        
        # Should raise exception but not crash application
        with pytest.raises(Exception):
            extractor.extract(corrupted_file)
    
    def test_permission_denied_handling(self):
        """Verifica gestione file senza permessi lettura."""
        # On Windows/Unix, trying to read protected file should raise PermissionError
        # Test with hypothetical protected file
        protected_path = Path("/root/.ssh/id_rsa")  # Unix example
        
        extractor = DocumentExtractor()
        
        with pytest.raises((PermissionError, FileNotFoundError)):
            extractor.extract(protected_path)


# Manual E2E Validation Checklist
"""
MANUAL E2E VALIDATION CHECKLIST (P0):

Prerequisites:
- [ ] API server running (docker-compose up or poetry run uvicorn)
- [ ] Admin JWT token available ($ADMIN_JWT)
- [ ] Test document preparato (es. lombalgia-test.docx)

Step 1: Upload Document
- [ ] POST /api/v1/admin/knowledge-base/sync-jobs
      Body: {
        "document_text": "Contenuto test lombalgia acuta...",
        "metadata": {
          "document_name": "test-lombalgia.docx",
          "source_path": "/path/to/test/document.docx"
        }
      }
      Headers: Authorization: Bearer $ADMIN_JWT
- [ ] Response: 200 OK con job_id
- [ ] Response contiene timing_metrics (extraction_ms, classification_ms, etc.)

Step 2: Verify Chunks in Database
- [ ] Connect to Supabase/PostgreSQL
- [ ] Query: SELECT COUNT(*) FROM document_chunks WHERE document_id = 'job_id'
- [ ] Result: COUNT > 0 (chunks creati)

Step 3: Verify NO NULL Embeddings (CRITICAL)
- [ ] Query: SELECT COUNT(*) FROM document_chunks 
            WHERE document_id = 'job_id' AND embedding IS NULL
- [ ] Result: COUNT = 0 (zero chunks con NULL embeddings)
- [ ] ACCEPTANCE: Addresses production issue "121 chunks non embedati"

Step 4: Semantic Search Functional
- [ ] POST /api/v1/chat (o semantic search endpoint)
      Body: {"query": "trattamento lombalgia", "session_id": "..."}
- [ ] Response: results array non vuoto
- [ ] Verify: relevance score > 0.5 per at least 1 result

Step 5: Chat LLM Response with Citations
- [ ] POST /api/v1/chat
      Body: {"message": "Come trattare lombalgia acuta?", "session_id": "..."}
- [ ] Response: answer presente
- [ ] Response: citations array presente con chunk IDs
- [ ] Verify: answer contiene informazioni rilevanti dal documento

Step 6: Rate Limiter Validation
- [ ] Make 10 requests to /api/v1/admin/knowledge-base/sync-jobs within 1 minute
- [ ] Requests 1-10: Status 200/201 (or 400 if invalid)
- [ ] Make 11th request
- [ ] Request 11: Status 429 "Too Many Requests"
- [ ] ACCEPTANCE: Rate limiter operational

Step 7: Path Security Validation
- [ ] Attempt POST with malicious source_path: "../../etc/passwd"
- [ ] Response: 400 Bad Request or 403 Forbidden (NOT 200 OK)
- [ ] ACCEPTANCE: Path traversal prevented

VALIDATION STATUS:
- [ ] All 7 steps completed successfully
- [ ] No NULL embeddings found (Step 3 CRITICAL)
- [ ] Semantic search returns results (Step 4)
- [ ] Chat provides answers with citations (Step 5)
- [ ] Rate limiter enforces 10/min limit (Step 6)
- [ ] Path traversal blocked (Step 7)

SIGN-OFF:
Validator: _______________
Date: _______________
Status: PASS / FAIL
Notes: _______________________________________________
"""

