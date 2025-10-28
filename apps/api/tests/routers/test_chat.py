"""
Test suite per Chat Router (Story 3.1 + 3.2 + 3.4).

Coverage:
- POST /api/v1/chat/query (semantic search)
- POST /api/v1/chat/sessions/{sessionId}/messages (augmented generation)
- POST /api/v1/chat/messages/{messageId}/feedback
- Authorization
- Rate limiting
- Validation
"""
import sys
import types
import time
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, FastAPI
from api.services.rate_limit_service import rate_limit_service
from unittest.mock import patch, MagicMock


# =============================================================================
# Test Chat Query (Story 3.1)
# =============================================================================

def test_chat_query_endpoint_with_mocks(monkeypatch, test_client):
    """Test: POST /api/v1/chat/query con match_threshold."""
    # Mock auth
    def fake_verify_jwt_token(_=None):
        return {"role": "authenticated", "sub": "user-1"}

    monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))

    # Mock search
    state = {"threshold": None}

    def fake_search(question: str, match_count: int = 8, match_threshold=None):
        state["threshold"] = match_threshold
        return [
            {"content": "c1", "metadata": {"id": "ch1", "document_id": "d1"}, "score": 0.91},
            {"content": "c2", "metadata": {"id": "ch2", "document_id": "d2"}, "score": 0.88},
        ]

    monkeypatch.setattr("api.routers.chat.perform_semantic_search", lambda q, k=8, t=None: fake_search(q, k, t))

    resp = test_client.post(
        "/api/v1/chat/query",
        headers={"Authorization": "Bearer x"},
        json={"sessionId": "s1", "question": "ciao", "match_count": 2, "match_threshold": 0.8},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "chunks" in data and isinstance(data["chunks"], list)
    assert len(data["chunks"]) == 2
    assert data["chunks"][0]["id"] == "ch1"
    assert state["threshold"] == 0.8


def test_chat_query_unauthorized_returns_401(test_client):
    """Test: richiesta senza JWT → 401."""
    resp = test_client.post(
        "/api/v1/chat/query",
        json={"sessionId": "s1", "question": "ciao"},
    )
    assert resp.status_code == 401


def test_chat_query_rate_limited_returns_429(monkeypatch, test_client):
    """Test: rate limiting enforcement."""
    call_state = {"count": 0}

    def fake_verify_jwt_token(_=None):
        call_state["count"] += 1
        if call_state["count"] > 1:
            raise HTTPException(status_code=429, detail="rate_limited")
        return {"role": "authenticated", "sub": "user-1"}

    monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))

    monkeypatch.setattr(
        "api.routers.chat.perform_semantic_search",
        lambda q, k=8, t=None: [
            {"content": "c1", "metadata": {"id": "ch1", "document_id": "d1"}, "score": 0.91}
        ],
    )

    # First call OK
    r1 = test_client.post(
        "/api/v1/chat/query",
        headers={"Authorization": "Bearer x"},
        json={"sessionId": "s1", "question": "q"},
    )
    assert r1.status_code == 200

    # Second call 429
    r2 = test_client.post(
        "/api/v1/chat/query",
        headers={"Authorization": "Bearer x"},
        json={"sessionId": "s1", "question": "q"},
    )
    assert r2.status_code == 429


# =============================================================================
# Test Augmented Generation (Story 3.2)
# =============================================================================


def test_ag_endpoint_rate_limited_returns_429(monkeypatch, test_client):
    """Test: rate limiting per chat endpoint restituisce 429 dopo la soglia."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")

    rate_limit_service._store.clear()

    call_state = {"count": 0}

    def fake_enforce_rate_limit(*_, **__):
        call_state["count"] += 1
        if call_state["count"] > 1:
            raise HTTPException(status_code=429, detail="rate_limited")

    monkeypatch.setattr(rate_limit_service, "enforce_rate_limit", fake_enforce_rate_limit)

    fake_settings = types.SimpleNamespace(
        chat_rate_limit_window_sec=60,
        chat_rate_limit_max_requests=1,
    )
    monkeypatch.setattr("api.routers.chat.get_settings", lambda: fake_settings)

    def fake_verify_jwt_token(_=None):
        return {"role": "authenticated", "sub": "student-1"}

    monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))

    monkeypatch.setattr(
        "api.routers.chat.perform_semantic_search",
        lambda *_, **__: [
            {
                "content": "chunk content",
                "metadata": {"id": "chunk-1", "document_id": "doc-1"},
                "similarity_score": 0.91,
            }
        ],
    )

    class DummyLLM:
        def invoke(self, _):
            class Response:
                content = "Risposta"

            return Response()

    monkeypatch.setattr("api.routers.chat.get_llm", lambda *_: DummyLLM())

    payload = {"message": "Domanda di test", "match_count": 1}
    headers = {"Authorization": "Bearer token"}

    first = test_client.post("/api/v1/chat/sessions/s1/messages", headers=headers, json=payload)
    assert first.status_code == 200

    second = test_client.post("/api/v1/chat/sessions/s1/messages", headers=headers, json=payload)
    assert second.status_code == 429
    assert second.json()["detail"] == "rate_limited"


def test_ag_endpoint_requires_auth(test_client):
    """Test: richiesta senza JWT → 401."""
    resp = test_client.post(
        "/api/v1/chat/sessions/s1/messages",
        json={"message": "q"},
    )
    assert resp.status_code == 401


def test_ag_endpoint_validates_inputs(monkeypatch, test_client):
    """Test: domanda vuota → 400."""
    def _auth(monkeypatch, role="authenticated"):
        def fake_verify_jwt_token(_=None):
            return {"role": role, "sub": "user-1"}
        monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))
    
    _auth(monkeypatch)
    
    r1 = test_client.post(
        "/api/v1/chat/sessions/s1/messages",
        headers={"Authorization": "Bearer x"},
        json={"message": ""},
    )
    assert r1.status_code == 400


def test_ag_endpoint_runs_semantic_search_when_chunks_absent(monkeypatch, test_client):
    """Test: chunks mancanti non bloccano la richiesta, viene eseguita semantic search server-side."""
    def _auth(monkeypatch, role="authenticated"):
        def fake_verify_jwt_token(_=None):
            return {"role": role, "sub": "user-1"}
        monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))
    
    _auth(monkeypatch)

    call_state = {}

    def fake_search(query: str, match_count: int = 8, match_threshold=None):
        call_state["query"] = query
        call_state["match_count"] = match_count
        call_state["match_threshold"] = match_threshold
        return [
            {
                "content": "chunk from search",
                "metadata": {"id": "cx1", "document_id": "doc-1"},
                "similarity_score": 0.87,
            }
        ]

    def fake_get_llm(_settings=None):
        raise RuntimeError("no llm in unit test")

    monkeypatch.setattr("api.routers.chat.perform_semantic_search", fake_search)
    monkeypatch.setattr("api.services.chat_service.get_llm", fake_get_llm)
    
    r = test_client.post(
        "/api/v1/chat/sessions/s1/messages",
        headers={"Authorization": "Bearer x"},
        json={"message": "ciao"},
    )
    assert r.status_code == 200
    assert call_state.get("query") == "ciao"
    data = r.json()
    assert data.get("message_id")
    assert data.get("retrieval_time_ms") is not None
    assert data.get("generation_time_ms") == 0
    citations = data.get("citations") or []
    assert any(c.get("chunk_id") == "cx1" for c in citations)
    message_text = (data.get("message") or data.get("answer") or "").lower()
    assert message_text
    assert "estratti" in message_text or "contesto non sufficiente" in message_text


def test_ag_endpoint_fallback_generates_answer_and_citations(monkeypatch, test_client):
    """Test: fallback LLM genera answer e citations."""
    def _auth(monkeypatch, role="authenticated"):
        def fake_verify_jwt_token(_=None):
            return {"role": role, "sub": "user-1"}
        monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))
    
    _auth(monkeypatch)

    def fake_get_llm(_settings=None):
        raise RuntimeError("no LLM in test")

    monkeypatch.setattr("api.services.chat_service.get_llm", fake_get_llm)

    r = test_client.post(
        "/api/v1/chat/sessions/s1/messages",
        headers={"Authorization": "Bearer x"},
        json={
            "message": "q",
            "chunks": [
                {"id": "c1", "document_id": "d1", "content": "t1"},
                {"id": None, "document_id": "d2", "content": "t2"},
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("message_id")
    assert data.get("retrieval_time_ms") == 0
    assert data.get("generation_time_ms") == 0
    citations = data.get("citations") or []
    citation_ids = {c.get("chunk_id") for c in citations if c.get("chunk_id")}
    assert citation_ids >= {"c1", "d2"}
    message_text = (data.get("message") or data.get("answer") or "").lower()
    assert message_text
    assert "estratti" in message_text or "contesto non sufficiente" in message_text


def test_chat_endpoint_returns_answer_and_sources(monkeypatch, test_client):
    """Test: POST /api/v1/chat restituisce answer e sources (Task 14)."""
    def _auth(monkeypatch, role="authenticated"):
        def fake_verify_jwt_token(_=None):
            return {"role": role, "sub": "user-1"}
        monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))

    _auth(monkeypatch)

    call_state = {}

    def fake_search(query: str, match_count: int = 8, match_threshold=None):
        call_state["search"] = (query, match_count, match_threshold)
        return [
            {"content": "Chunk 1 contenuto", "metadata": {"id": "c1", "document_id": "d1"}, "similarity_score": 0.91},
            {"content": "Chunk 2 contenuto", "metadata": {"id": "c2", "document_id": "d2"}, "similarity_score": 0.82},
        ]

    monkeypatch.setattr("api.routers.chat.perform_semantic_search", fake_search)

    class FakeChain:
        def invoke(self, params):
            call_state["llm_input"] = params
            return type("Resp", (), {"content": "Risposta test"})()

    class FakePrompt:
        def __or__(self, llm):
            call_state["llm_instance"] = llm
            return FakeChain()

    class FakePromptFactory:
        @staticmethod
        def from_messages(messages):
            call_state["prompt_messages"] = messages
            return FakePrompt()

    class FakeLLM:
        pass

    monkeypatch.setattr("api.routers.chat.ChatPromptTemplate", FakePromptFactory)
    monkeypatch.setattr("api.routers.chat.get_llm", lambda: FakeLLM())

    response = test_client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer x"},
        json={
            "message": "Quali esercizi aiutano la lombalgia?",
            "session_id": "session-1",
            "match_count": 5,
            "match_threshold": 0.2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Risposta test"
    assert data["session_id"] == "session-1"
    assert isinstance(data["sources"], list) and len(data["sources"]) == 2
    assert call_state["search"] == ("Quali esercizi aiutano la lombalgia?", 5, 0.2)
    assert call_state["llm_input"]["context"].startswith("Chunk 1 contenuto")


def test_chat_endpoint_returns_fallback_on_empty_results(monkeypatch, test_client):
    """Test: POST /api/v1/chat fallback quando nessun risultato (Task 13 prereq)."""
    def _auth(monkeypatch, role="authenticated"):
        def fake_verify_jwt_token(_=None):
            return {"role": role, "sub": "user-1"}
        monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))

    _auth(monkeypatch)

    monkeypatch.setattr("api.routers.chat.perform_semantic_search", lambda *args, **kwargs: [])

    response = test_client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer x"},
        json={
            "message": "Domanda senza contenuti rilevanti",
            "session_id": "session-empty",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Nessun contenuto rilevante trovato per la tua domanda."
    assert data["session_id"] == "session-empty"
    assert data["sources"] == []


def test_ag_endpoint_uses_settings_for_llm(monkeypatch):
    """2.12-INT-002: il service usa model/temperature dalle Settings DI."""
    from types import SimpleNamespace

    from api.routers import chat as chat_router
    from api.models.answer_with_citations import AnswerWithCitations

    monkeypatch.setattr(
        "api.dependencies.verify_jwt_token",
        lambda: {"role": "authenticated", "sub": "user-1"},
    )

    def fake_search(*args, **kwargs):
        return [
            {
                "content": "contesto",
                "metadata": {"id": "chunk-1", "document_id": "doc-1"},
                "similarity_score": 0.99,
            }
        ]

    monkeypatch.setattr("api.routers.chat.perform_semantic_search", fake_search)

    captured: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeParser:
        def __init__(self, *_, **__):
            pass

        def get_format_instructions(self):
            return ""

    class FakeChain:
        def __or__(self, _parser):
            return self

        def invoke(self, _):
            return AnswerWithCitations(
                risposta="risposta mock",
                citazioni=["chunk-1"],
            )

    class FakePrompt:
        def __or__(self, _llm):
            return FakeChain()

        def partial(self, **_kwargs):
            return self

    class FakePromptFactory:
        @staticmethod
        def from_messages(_messages):
            return FakePrompt()

    monkeypatch.setattr("api.services.chat_service.ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr("api.routers.chat.ChatPromptTemplate", FakePromptFactory)
    monkeypatch.setattr("api.routers.chat.PydanticOutputParser", FakeParser)

    stub_settings = SimpleNamespace(
        openai_model="gpt-5-turbo",
        openai_temperature_chat=0.25,
        llm_config_refactor_enabled=True,
    )

    app = FastAPI()
    app.include_router(chat_router.router)
    app.dependency_overrides[chat_router.get_settings] = lambda: stub_settings
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/sessions/s1/messages",
            headers={"Authorization": "Bearer token"},
            json={"message": "Qual e il piano?", "sessionId": "s1"},
        )

    assert response.status_code == 200
    assert captured.get("model") == "gpt-5-turbo"
    assert captured.get("temperature") == 0.25


# =============================================================================
# Test Feedback (Story 3.4)
# =============================================================================

def test_feedback_endpoint_creates_feedback(monkeypatch, test_client):
    """Test: POST /api/v1/chat/messages/{messageId}/feedback → 201."""
    def _auth(monkeypatch):
        def fake_verify_jwt_token(_=None):
            return {"role": "authenticated", "sub": "user-1"}
        monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))
    
    _auth(monkeypatch)
    
    # Mock stores
    from api.stores import chat_messages_store, feedback_store
    chat_messages_store["test_session"] = [
        {"role": "assistant", "message_id": "test_msg_1", "content": "Answer"}
    ]
    
    response = test_client.post(
        "/api/v1/chat/messages/test_msg_1/feedback",
        headers={"Authorization": "Bearer x"},
        json={"sessionId": "test_session", "vote": "up", "comment": "Helpful"}  # Story 5.5 Task 1: Added sessionId required field
    )
    
    assert response.status_code == 200  # Story 5.5 Task 1: Endpoint returns 200 OK, not 201 Created
    data = response.json()
    assert data["ok"] is True  # Story 5.5 Task 1: Response model is FeedbackCreateResponse with ok field
    
    # Cleanup
    if "test_session:test_msg_1" in feedback_store:
        del feedback_store["test_session:test_msg_1"]

# =============================================================================
# Test Chat Query (Story 3.1)
# =============================================================================


@pytest.fixture(autouse=True)
def external_stubs(monkeypatch):
    """Stub dipendenze opzionali (slowapi, asyncpg, jwt, langchain, supabase) nei test."""

    # slowapi
    slowapi_module = types.ModuleType("slowapi")
    slowapi_module.Limiter = lambda *_, **__: types.SimpleNamespace()
    slowapi_module._rate_limit_exceeded_handler = lambda request, exc: None

    errors_module = types.ModuleType("slowapi.errors")

    class RateLimitExceeded(Exception):
        """Stub RateLimitExceeded exception."""

    errors_module.RateLimitExceeded = RateLimitExceeded

    util_module = types.ModuleType("slowapi.util")
    util_module.get_remote_address = lambda request: "test-ip"

    monkeypatch.setitem(sys.modules, "slowapi", slowapi_module)
    monkeypatch.setitem(sys.modules, "slowapi.errors", errors_module)
    monkeypatch.setitem(sys.modules, "slowapi.util", util_module)
    slowapi_module.errors = errors_module
    slowapi_module.util = util_module

    # asyncpg
    asyncpg_module = types.ModuleType("asyncpg")

    async def _fake_connect(*args, **kwargs):  # pragma: no cover - stub
        raise RuntimeError("asyncpg not available in tests")

    class Pool:  # pragma: no cover - stub
        async def close(self):
            return None

        def terminate(self):
            return None

    class Connection:  # pragma: no cover - stub
        async def close(self):
            return None

    async def _fake_create_pool(*args, **kwargs):
        return Pool()

    asyncpg_module.connect = _fake_connect
    asyncpg_module.create_pool = _fake_create_pool
    asyncpg_module.Pool = Pool
    asyncpg_module.Connection = Connection
    monkeypatch.setitem(sys.modules, "asyncpg", asyncpg_module)

    # jwt
    jwt_module = types.ModuleType("jwt")

    def _encode(payload, key, algorithm=None):  # pragma: no cover - stub
        return "stub-jwt-token"

    def _decode(token, key, algorithms=None, audience=None):  # pragma: no cover - stub
        return {"sub": "stub"}

    class PyJWTError(Exception):
        """Stub PyJWTError base class."""

    jwt_module.encode = _encode
    jwt_module.decode = _decode
    jwt_module.PyJWTError = PyJWTError
    jwt_module.InvalidTokenError = PyJWTError
    monkeypatch.setitem(sys.modules, "jwt", jwt_module)

    # langchain_openai
    lc_openai_module = types.ModuleType("langchain_openai")

    class ChatOpenAI:  # pragma: no cover - stub
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __or__(self, other):
            return other

        def invoke(self, *_args, **_kwargs):
            return types.SimpleNamespace(content="stub")

    class OpenAIEmbeddings:  # pragma: no cover - stub
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    lc_openai_module.ChatOpenAI = ChatOpenAI
    lc_openai_module.OpenAIEmbeddings = OpenAIEmbeddings
    monkeypatch.setitem(sys.modules, "langchain_openai", lc_openai_module)

    # langchain_core submodules
    lc_lm_module = types.ModuleType("langchain_core.language_models")

    class BaseLanguageModel:  # pragma: no cover - stub
        pass

    lc_lm_module.BaseLanguageModel = BaseLanguageModel
    monkeypatch.setitem(sys.modules, "langchain_core.language_models", lc_lm_module)

    lc_prompts_module = types.ModuleType("langchain_core.prompts")

    class ChatPromptTemplate:  # pragma: no cover - stub
        @staticmethod
        def from_messages(_messages):
            class _Template:
                def partial(self, **_kwargs):
                    return self

                def __or__(self, other):
                    return other

            return _Template()

    class PromptTemplate:  # pragma: no cover - stub
        @staticmethod
        def from_template(_template):
            class _Prompt:
                def format(self, **_kwargs):
                    return _template

                def __or__(self, other):
                    return other

            return _Prompt()

    lc_prompts_module.ChatPromptTemplate = ChatPromptTemplate
    lc_prompts_module.PromptTemplate = PromptTemplate
    monkeypatch.setitem(sys.modules, "langchain_core.prompts", lc_prompts_module)

    lc_output_module = types.ModuleType("langchain_core.output_parsers")

    class PydanticOutputParser:  # pragma: no cover - stub
        def __init__(self, *_, **__):
            pass

        def get_format_instructions(self):
            return ""

    class StrOutputParser:  # pragma: no cover - stub
        def __init__(self, *_, **__):
            pass

        def __ror__(self, other):
            return self

        def invoke(self, _):
            return "stub"

    lc_output_module.PydanticOutputParser = PydanticOutputParser
    lc_output_module.StrOutputParser = StrOutputParser
    monkeypatch.setitem(sys.modules, "langchain_core.output_parsers", lc_output_module)

    lc_runnables_module = types.ModuleType("langchain_core.runnables")

    class Runnable:  # pragma: no cover - stub
        pass

    class RunnableConfig:  # pragma: no cover - stub
        pass

    def ensure_config(config=None):  # pragma: no cover - stub
        return config

    lc_runnables_module.Runnable = Runnable
    lc_runnables_module.RunnableConfig = RunnableConfig
    lc_runnables_module.ensure_config = ensure_config
    monkeypatch.setitem(sys.modules, "langchain_core.runnables", lc_runnables_module)

    # supabase client
    supabase_module = types.ModuleType("supabase")

    class Client:  # pragma: no cover - stub
        def __init__(self, *_, **__):
            pass

    def create_client(*args, **kwargs):
        return Client()

    supabase_module.Client = Client
    supabase_module.create_client = create_client
    monkeypatch.setitem(sys.modules, "supabase", supabase_module)

    # langchain community vectorstore
    vectorstores_module = types.ModuleType("langchain_community.vectorstores")

    class SupabaseVectorStore:  # pragma: no cover - stub
        @classmethod
        def from_existing_index(cls, *_, **__):
            return cls()

        def similarity_search(self, *_, **__):
            return []

        def similarity_search_with_score(self, *_, **__):
            return []

    vectorstores_module.SupabaseVectorStore = SupabaseVectorStore
    monkeypatch.setitem(sys.modules, "langchain_community.vectorstores", vectorstores_module)

    # langchain text splitters
    splitters_module = types.ModuleType("langchain_text_splitters")

    class RecursiveCharacterTextSplitter:  # pragma: no cover - stub
        def __init__(self, *_, **__):
            pass

        def split_text(self, text):
            return [text]

    splitters_module.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
    monkeypatch.setitem(sys.modules, "langchain_text_splitters", splitters_module)
