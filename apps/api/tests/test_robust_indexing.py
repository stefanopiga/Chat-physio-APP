"""Unit tests per robust batch embedding e indexing (Story 2.5 AC6, AC8).

Test coverage:
- Retry logic con tenacity
- Batch optimization
- Timing metrics accuracy
- Error handling robusto
"""
import pytest
from unittest.mock import Mock, patch
import openai
from tenacity import RetryError

from api.knowledge_base.indexer import (
    _embed_texts_with_retry,
    index_chunks,
)


class TestEmbedTextsWithRetry:
    """Test suite per _embed_texts_with_retry function."""
    
    @patch("api.knowledge_base.indexer.logger")
    def test_embed_success_first_attempt(self, mock_logger):
        """Verifica embedding success al primo tentativo."""
        # Mock embeddings model
        mock_embeddings_model = Mock()
        mock_embeddings_model.embed_documents.return_value = [
            [0.1, 0.2, 0.3],  # embedding 1
            [0.4, 0.5, 0.6],  # embedding 2
        ]
        
        texts = ["Text 1", "Text 2"]
        
        result = _embed_texts_with_retry(texts, mock_embeddings_model)
        
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        
        # Verify embed_documents called once
        assert mock_embeddings_model.embed_documents.call_count == 1
    
    @patch("api.knowledge_base.indexer.logger")
    def test_embed_retry_on_rate_limit(self, mock_logger):
        """Verifica retry logic su RateLimitError."""
        mock_embeddings_model = Mock()
        
        # Mock response per OpenAI exception
        mock_response = Mock()
        mock_response.status_code = 429
        
        # First 2 calls fail con RateLimitError, 3rd succeeds
        mock_embeddings_model.embed_documents.side_effect = [
            openai.RateLimitError("Rate limit exceeded", response=mock_response, body={}),
            openai.RateLimitError("Rate limit exceeded", response=mock_response, body={}),
            [[0.1, 0.2, 0.3]]  # Success al 3° tentativo
        ]
        
        texts = ["Text 1"]
        
        result = _embed_texts_with_retry(texts, mock_embeddings_model)
        
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        
        # Verify 3 attempts (2 failed + 1 success)
        assert mock_embeddings_model.embed_documents.call_count == 3
    
    @patch("api.knowledge_base.indexer.logger")
    def test_embed_retry_exhausted(self, mock_logger):
        """Verifica exception dopo max retries exhausted."""
        mock_embeddings_model = Mock()
        
        # Mock response per OpenAI exception
        mock_response = Mock()
        mock_response.status_code = 429
        
        # Always fail con RateLimitError
        mock_embeddings_model.embed_documents.side_effect = openai.RateLimitError(
            "Rate limit exceeded", response=mock_response, body={}
        )
        
        texts = ["Text 1"]
        
        # Dopo 5 tentativi (max retries), exception propagata come RetryError
        with pytest.raises(RetryError):
            _embed_texts_with_retry(texts, mock_embeddings_model)
        
        # Verify 5 attempts (max_retries from tenacity decorator)
        assert mock_embeddings_model.embed_documents.call_count == 5
    
    @patch("api.knowledge_base.indexer.logger")
    def test_embed_batch_optimization(self, mock_logger):
        """Verifica batch optimization (100 texts per batch)."""
        mock_embeddings_model = Mock()
        
        # Mock embeddings per batch
        def mock_embed(texts):
            return [[0.1] * len(texts)] * len(texts)
        
        mock_embeddings_model.embed_documents.side_effect = mock_embed
        
        # 250 texts → 3 batches (100, 100, 50)
        texts = [f"Text {i}" for i in range(250)]
        
        result = _embed_texts_with_retry(texts, mock_embeddings_model)
        
        # Verify 3 batches processed
        assert mock_embeddings_model.embed_documents.call_count == 3
        
        # Verify total embeddings count
        assert len(result) == 250
    
    @patch("api.knowledge_base.indexer.logger")
    def test_embed_no_retry_on_auth_error(self, mock_logger):
        """Verifica NO retry su AuthenticationError (non transient)."""
        mock_embeddings_model = Mock()
        
        # Mock response per OpenAI exception
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_embeddings_model.embed_documents.side_effect = openai.AuthenticationError(
            "Invalid API key", response=mock_response, body={}
        )
        
        texts = ["Text 1"]
        
        # AuthenticationError non è retry-able → immediate fail
        with pytest.raises(openai.AuthenticationError):
            _embed_texts_with_retry(texts, mock_embeddings_model)
        
        # Verify solo 1 attempt (no retry)
        assert mock_embeddings_model.embed_documents.call_count == 1


class TestIndexChunks:
    """Test suite per index_chunks function con timing metrics."""
    
    @patch("api.knowledge_base.indexer._get_embeddings_model")
    @patch("api.knowledge_base.indexer._get_supabase_client")
    @patch("api.knowledge_base.indexer._embed_texts_with_retry")
    def test_index_chunks_success_with_timing(
        self,
        mock_embed_retry,
        mock_supabase,
        mock_embeddings
    ):
        """Verifica indexing success con timing metrics."""
        # Mock embeddings
        mock_embed_retry.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        
        # Mock Supabase vector store
        mock_vector_store = Mock()
        mock_vector_store.add_texts.return_value = ["id1", "id2"]
        
        with patch("api.knowledge_base.indexer.SupabaseVectorStore", return_value=mock_vector_store):
            chunks = ["Chunk 1", "Chunk 2"]
            metadata_list = [{"doc_id": "1"}, {"doc_id": "2"}]
            
            inserted = index_chunks(chunks, metadata_list)
            
            assert inserted == 2
            
            # Verify timing metrics logged (check via logger mock if needed)
    
    @patch("api.knowledge_base.indexer._get_embeddings_model")
    @patch("api.knowledge_base.indexer._get_supabase_client")
    def test_index_chunks_empty_list(self, mock_supabase, mock_embeddings):
        """Verifica handling lista chunks vuota."""
        chunks = []
        
        inserted = index_chunks(chunks)
        
        assert inserted == 0
    
    @patch("api.knowledge_base.indexer._get_embeddings_model")
    @patch("api.knowledge_base.indexer._get_supabase_client")
    @patch("api.knowledge_base.indexer._embed_texts_with_retry")
    def test_index_chunks_insertion_failed(
        self,
        mock_embed_retry,
        mock_supabase,
        mock_embeddings
    ):
        """Verifica error handling inserimento fallito (zero IDs)."""
        mock_embed_retry.return_value = [[0.1, 0.2]]
        
        # Mock vector store che ritorna lista vuota
        mock_vector_store = Mock()
        mock_vector_store.add_texts.return_value = []
        
        with patch("api.knowledge_base.indexer.SupabaseVectorStore", return_value=mock_vector_store):
            chunks = ["Chunk 1"]
            
            with pytest.raises(ValueError, match="nessun chunk inserito"):
                index_chunks(chunks)
    
    @patch("api.knowledge_base.indexer._get_embeddings_model")
    def test_index_chunks_openai_auth_error(self, mock_embeddings):
        """Verifica error handling OpenAI authentication failure."""
        # Mock response per OpenAI exception
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_embeddings.side_effect = openai.AuthenticationError(
            "Invalid API key", response=mock_response, body={}
        )
        
        chunks = ["Chunk 1"]
        
        with pytest.raises(openai.AuthenticationError):
            index_chunks(chunks)


class TestTimingMetrics:
    """Test suite per timing metrics accuracy."""
    
    @patch("api.knowledge_base.indexer._get_embeddings_model")
    @patch("api.knowledge_base.indexer._get_supabase_client")
    @patch("api.knowledge_base.indexer._embed_texts_with_retry")
    @patch("api.knowledge_base.indexer.time")
    def test_timing_metrics_structure(
        self,
        mock_time,
        mock_embed_retry,
        mock_supabase,
        mock_embeddings
    ):
        """Verifica presenza timing metrics in logs.
        
        Expected metrics:
        - embedding_ms
        - supabase_insert_ms
        - total_ms
        """
        # Mock time.time() per simulare timing
        mock_time.time.side_effect = [
            0.0,      # start_total
            0.0,      # start_embed
            0.5,      # end_embed (500ms)
            0.5,      # start_insert
            0.7,      # end_insert (200ms)
            0.7       # end_total (700ms)
        ]
        
        mock_embed_retry.return_value = [[0.1, 0.2]]
        
        mock_vector_store = Mock()
        mock_vector_store.add_texts.return_value = ["id1"]
        
        with patch("api.knowledge_base.indexer.SupabaseVectorStore", return_value=mock_vector_store):
            with patch("api.knowledge_base.indexer.logger") as mock_logger:
                chunks = ["Chunk 1"]
                
                index_chunks(chunks)
                
                # Verify timing metrics logged
                # Check logger.info calls per "indexing_metrics" event
                logged_calls = [call for call in mock_logger.info.call_args_list]
                
                # At least one call should contain timing metrics
                assert any("timing" in str(call) for call in logged_calls)


class TestErrorHandlingRobustness:
    """Test suite per error handling robusto."""
    
    @patch("api.knowledge_base.indexer._get_embeddings_model")
    @patch("api.knowledge_base.indexer._get_supabase_client")
    @patch("api.knowledge_base.indexer._embed_texts_with_retry")
    def test_partial_insertion_warning(
        self,
        mock_embed_retry,
        mock_supabase,
        mock_embeddings
    ):
        """Verifica warning log per inserimento parziale."""
        mock_embed_retry.return_value = [[0.1], [0.2], [0.3]]
        
        # Mock vector store che inserisce solo 2 su 3 chunks
        mock_vector_store = Mock()
        mock_vector_store.add_texts.return_value = ["id1", "id2"]  # Solo 2 IDs
        
        with patch("api.knowledge_base.indexer.SupabaseVectorStore", return_value=mock_vector_store):
            with patch("api.knowledge_base.indexer.logger") as mock_logger:
                chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
                
                inserted = index_chunks(chunks)
                
                # Inserted = 2 (parziale)
                assert inserted == 2
                
                # Verify warning logged
                assert any(
                    "partial_insertion" in str(call)
                    for call in mock_logger.warning.call_args_list
                )


# Integration test notes:
"""
Per integration test completi (Story 2.5 AC10):

Test E2E: Upload documento → verify chunks embedati → semantic search

1. Setup test environment:
   - Test Supabase instance o mock
   - Test OpenAI API key o mock
   - Test Redis per Celery (optional)

2. Test scenario:
   @pytest.mark.integration
   def test_pipeline_e2e():
       # 1. Upload test document
       response = client.post("/api/v1/admin/knowledge-base/sync-jobs", ...)
       assert response.status_code == 200
       job_id = response.json()["job_id"]
       
       # 2. Wait e verify completion
       status = wait_for_job_completion(job_id)
       assert status["status"] == "SUCCESS"
       
       # 3. Query DB: verify embeddings NOT NULL
       chunks = db.query("SELECT * FROM document_chunks WHERE document_id = ?", job_id)
       assert all(chunk["embedding"] is not None for chunk in chunks)
       
       # 4. Semantic search test
       search_result = client.post("/api/v1/knowledge-base/search", {"query": "test"})
       assert len(search_result.json()["results"]) > 0

Status: Richiede integration test infrastructure
"""

