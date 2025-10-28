"""Resilience tests for OpenAI integration (Story 2.8.1)."""

from __future__ import annotations

import httpx
import openai
import pytest
import tenacity

from api.knowledge_base import indexer


@pytest.fixture(autouse=True)
def disable_retry_sleep(monkeypatch):
    """Avoid exponential backoff delays during unit tests."""

    if hasattr(indexer._embed_texts_with_retry, "retry"):
        monkeypatch.setattr(
            indexer._embed_texts_with_retry.retry,
            "sleep",
            lambda *args, **kwargs: None,
        )


class _DummyEmbeddings:
    """Minimal embeddings stub exposing embed_documents."""

    def __init__(self, behavior):
        self._behavior = behavior
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        return self._behavior(self.calls, texts)


def test_embed_texts_retry_on_rate_limit():
    """Ensure retry/backoff handles transient OpenAI rate limits."""

    def behavior(call_number: int, texts):
        if call_number < 3:
            request = httpx.Request("POST", "https://api.openai.com/v1/test")
            response = httpx.Response(429, request=request)
            raise openai.RateLimitError(message="rate limited", response=response, body=None)
        # Return deterministic vectors
        return [[float(call_number)] * 3 for _ in texts]

    dummy = _DummyEmbeddings(behavior)
    payload = ["alpha", "beta"]

    result = indexer._embed_texts_with_retry(payload, dummy)

    assert dummy.calls == 3, "Expected retry attempts before success."
    assert len(result) == len(payload)
    assert result[0][0] == pytest.approx(3.0)


def test_embed_texts_retry_exhaustion_raises():
    """After max attempts, RateLimitError should surface to caller."""

    def behavior_unrecoverable(call_number: int, texts):
        request = httpx.Request("POST", "https://api.openai.com/v1/test")
        response = httpx.Response(429, request=request)
        raise openai.RateLimitError(message=f"rate limited {call_number}", response=response, body=None)

    dummy = _DummyEmbeddings(behavior_unrecoverable)

    with pytest.raises(tenacity.RetryError) as exc:
        indexer._embed_texts_with_retry(["payload"], dummy)

    assert dummy.calls == 5, "Tenacity stop_after_attempt(5) expected."
    assert isinstance(
        exc.value.last_attempt.exception(),
        openai.RateLimitError,
    )


def test_embed_texts_handles_connection_error():
    """APIConnectionError should trigger retry path before bubbling up."""

    def behavior(call_number: int, texts):
        request = httpx.Request("POST", "https://api.openai.com/v1/test")
        raise openai.APIConnectionError(message="gateway timeout", request=request)

    dummy = _DummyEmbeddings(behavior)

    with pytest.raises(tenacity.RetryError) as exc:
        indexer._embed_texts_with_retry(["chunk"], dummy)

    assert dummy.calls == 5
    assert isinstance(
        exc.value.last_attempt.exception(),
        openai.APIConnectionError,
    )
