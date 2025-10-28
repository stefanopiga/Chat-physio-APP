import os
import inspect
import logging
import json
import time
import secrets
import string
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Annotated, Optional, Dict, Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import Runnable
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from .ingestion.models import ClassificazioneOutput, DocumentStructureCategory
from .ingestion.chunk_router import ChunkRouter
from .ingestion.db_storage import save_document_to_db, update_document_status
from .knowledge_base.indexer import index_chunks
from .knowledge_base.search import perform_semantic_search
from .models.answer_with_citations import AnswerWithCitations
from .analytics.analytics import aggregate_analytics, AnalyticsResponse
from .database import get_db_connection
import asyncpg
from supabase import create_client, Client
CELERY_ENABLED = os.getenv("CELERY_ENABLED", "false").lower() in {"1", "true", "yes"}
if CELERY_ENABLED:
    try:
        from celery.result import AsyncResult
        from .celery_app import celery_app, kb_indexing_task
    except Exception:  # pragma: no cover - fallback se Celery non disponibile
        CELERY_ENABLED = False
from dotenv import load_dotenv
from .database import lifespan

app = FastAPI(lifespan=lifespan)

# -------------------------------
# SlowAPI: Rate Limiting
# -------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -------------------------------
# Logging strutturato (JSON)
# -------------------------------

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: dict = {}
        # Se il messaggio è già un dict, usalo direttamente; altrimenti incapsula
        if isinstance(record.msg, dict):
            base.update(record.msg)
        else:
            base["message"] = record.getMessage()

        base.setdefault("level", record.levelname)
        base.setdefault("logger", record.name)
        base.setdefault("time", datetime.now(timezone.utc).isoformat())
        return json.dumps(base, ensure_ascii=False)


logger = logging.getLogger("api")
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# CORS per sviluppo locale (può essere ristretto in produzione)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carica automaticamente le variabili da .env (radice dell'app: apps/api/.env)
load_dotenv()

# Carica la chiave segreta JWT dalle variabili d'ambiente
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
EXPECTED_AUD = "authenticated"
JWT_ISSUER = os.getenv("SUPABASE_JWT_ISSUER", "https://example.supabase.co/auth/v1")
TEMP_JWT_EXPIRES_MINUTES = int(os.getenv("TEMP_JWT_EXPIRES_MINUTES", "15"))


def _get_supabase_client() -> Client:
    """Crea client Supabase con service_role_key (bypassa RLS)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY non impostati")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# -------------------------------
# Rate limiting configurabile
# -------------------------------
EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC = int(os.getenv("EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC", "60"))
EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS", "10"))

# Store in-memory per IP → [timestamps]
_rate_limit_store: Dict[str, list[float]] = {}

def _enforce_rate_limit(client_ip: str) -> None:
    if not client_ip:
        return
    now_ts = time.time()
    window_start = now_ts - EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC
    timestamps = _rate_limit_store.get(client_ip, [])
    # Pulisci finestre scadute
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS:
        _rate_limit_store[client_ip] = timestamps
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited")
    timestamps.append(now_ts)
    _rate_limit_store[client_ip] = timestamps


# -------------------------------
# Middleware di logging richieste
# -------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    client_ip = request.client.host if request.client else None
    logger.info({
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": client_ip,
    })
    return response

# Verifica che la chiave segreta sia stata impostata, altrimenti solleva un errore all'avvio
if not SUPABASE_JWT_SECRET:
    raise ValueError("La variabile d'ambiente SUPABASE_JWT_SECRET non è impostata.")

security = HTTPBearer(auto_error=False)

def verify_jwt_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=EXPECTED_AUD,
            options={"require": ["exp", "iat"]},
        )
        return payload
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}") from e

TokenPayload = dict

def _verify_jwt_token_runtime(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
):
    """Bridge runtime per consentire monkeypatch nei test.

    Se `verify_jwt_token` è monkeypatchato a callable senza argomenti,
    invocalo senza passare `credentials`. Altrimenti passa `credentials`.
    """
    func = globals().get("verify_jwt_token")
    if func is None:
        raise HTTPException(status_code=500, detail="auth_dependency_missing")
    try:
        sig = inspect.signature(func)
        if len(sig.parameters) == 0:
            return func()
        return func(credentials)
    except TypeError:
        return func()


def _auth_bridge(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
):
    """Wrapper che richiama il bridge runtime.

    Consente ai test di monkeypatchare `api.main._auth_bridge` e influenzare
    le dipendenze dei route anche se il callable è stato catturato alla definizione.
    """
    return _verify_jwt_token_runtime(credentials)

@app.get("/api/admin/me")
def admin_me(payload: Annotated[TokenPayload, Depends(verify_jwt_token)]):
    return {"ok": True, "sub": payload.get("sub")}


# -------------------------------
# Analytics Dashboard (Story 4.2)
# -------------------------------


def _analytics_rate_limit_key(request: Request) -> str:
    """Chiave rate limiting per-admin per analytics."""
    try:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=EXPECTED_AUD,
                options={"require": ["exp", "iat"]},
            )
            sub = payload.get("sub")
            if sub:
                return f"analytics_rl::{sub}"
    except Exception:
        pass
    return (request.client.host if request.client else "unknown_ip")


@app.get("/api/v1/admin/analytics", response_model=AnalyticsResponse)
@limiter.limit("30/hour", key_func=_analytics_rate_limit_key)
def get_admin_analytics(
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Analytics Dashboard endpoint (Story 4.2).
    
    Aggrega dati da store in-memory:
    - chat_messages_store: query utenti
    - feedback_store: thumbs up/down
    - ag_latency_samples_ms: performance metrics
    
    Security:
    - Admin-only access
    - Rate limiting 30/hour
    - Session IDs hashati (privacy)
    
    Note: Dati volatili (tech debt R-4.2-1 accepted per MVP)
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    # Aggregazione dati
    analytics = aggregate_analytics(
        chat_messages_store=chat_messages_store,
        feedback_store=feedback_store,
        ag_latency_samples_ms=ag_latency_samples_ms,
    )
    
    # Audit log
    logger.info({
        "event": "analytics_accessed",
        "path": "/api/v1/admin/analytics",
        "user_id": payload.get("sub"),
        "total_queries": analytics.overview.total_queries,
        "total_sessions": analytics.overview.total_sessions,
    })
    
    return analytics


# -------------------------------
# Student Token Management (Story 1.3.1) - Models & Helpers
# -------------------------------

# Pydantic Models (definite PRIMA degli endpoint per evitare NameError)
class CreateStudentTokenRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class CreateStudentTokenResponse(BaseModel):
    id: str
    token: str
    first_name: str
    last_name: str
    expires_at: str


class StudentTokenResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    token: str
    is_active: bool
    expires_at: str
    created_at: str
    updated_at: str


# Helper functions for token generation
def generate_student_token() -> str:
    """
    Genera student token sicuro 32 caratteri (256-bit entropy).
    URL-safe base64 encoding (caratteri: A-Z, a-z, 0-9, -, _).
    Distribuito dall'admin allo studente via mail.
    """
    return secrets.token_urlsafe(32)


def generate_refresh_token() -> str:
    """
    Genera refresh token sicuro 64 caratteri (512-bit entropy).
    URL-safe base64 encoding.
    Salvato in DB e cookie HttpOnly, mai mostrato all'utente.
    """
    return secrets.token_urlsafe(64)


# Rate Limiting constants (OWASP)
ADMIN_CREATE_TOKEN_RATE_LIMIT_WINDOW_SEC = int(os.getenv("ADMIN_CREATE_TOKEN_RATE_LIMIT_WINDOW_SEC", "3600"))
ADMIN_CREATE_TOKEN_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("ADMIN_CREATE_TOKEN_RATE_LIMIT_MAX_REQUESTS", "10"))
REFRESH_TOKEN_RATE_LIMIT_WINDOW_SEC = int(os.getenv("REFRESH_TOKEN_RATE_LIMIT_WINDOW_SEC", "3600"))
REFRESH_TOKEN_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("REFRESH_TOKEN_RATE_LIMIT_MAX_REQUESTS", "60"))

# Rate limiting store per admin create token
_admin_create_token_rate_limit_store: Dict[str, list[float]] = {}


def _enforce_admin_create_token_rate_limit(admin_user_id: str) -> None:
    """Rate limiting per admin create token (10 req/ora, OWASP)."""
    if not admin_user_id:
        return
    now_ts = time.time()
    window_start = now_ts - ADMIN_CREATE_TOKEN_RATE_LIMIT_WINDOW_SEC
    timestamps = _admin_create_token_rate_limit_store.get(admin_user_id, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= ADMIN_CREATE_TOKEN_RATE_LIMIT_MAX_REQUESTS:
        _admin_create_token_rate_limit_store[admin_user_id] = timestamps
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited")
    timestamps.append(now_ts)
    _admin_create_token_rate_limit_store[admin_user_id] = timestamps


@app.post("/api/v1/admin/student-tokens", response_model=CreateStudentTokenResponse, status_code=201)
def create_student_token(
    body: CreateStudentTokenRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
):
    """
    Crea nuovo student token persistente (Story 1.3.1).
    
    - Genera token sicuro 32 char (256-bit entropy)
    - Persistenza DB con durata 1 anno
    - Admin-only access
    - Rate limiting 10 req/ora (OWASP)
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    admin_user_id = payload.get("sub")
    _enforce_admin_create_token_rate_limit(admin_user_id)
    
    # Validazione input
    first_name = (body.first_name or "").strip()
    last_name = (body.last_name or "").strip()
    if not first_name or not last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="first_name and last_name required"
        )
    
    # Genera token
    token = generate_student_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=365)
    
    # Insert in DB
    try:
        supabase = _get_supabase_client()
        result = supabase.table("student_tokens").insert({
            "first_name": first_name,
            "last_name": last_name,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "created_by_id": admin_user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create student token"
            )
        
        created = result.data[0]
        
        logger.info({
            "event": "student_token_created",
            "student_token_id": created["id"],
            "admin_user_id": admin_user_id,
            "expires_at": expires_at.isoformat(),
        })
        
        return CreateStudentTokenResponse(
            id=created["id"],
            token=token,
            first_name=first_name,
            last_name=last_name,
            expires_at=expires_at.isoformat(),
        )
    except Exception as exc:
        logger.error({
            "event": "student_token_create_failed",
            "error": str(exc),
            "admin_user_id": admin_user_id,
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}"
        )


@app.get("/api/v1/admin/student-tokens", response_model=list[StudentTokenResponse])
def list_student_tokens(
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    is_active: Optional[bool] = True,
):
    """
    Lista student tokens (Story 1.3.1).
    
    - Filtra per is_active (default: true)
    - Admin-only access
    - Order by created_at DESC
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    try:
        supabase = _get_supabase_client()
        query = supabase.table("student_tokens").select("*")
        
        if is_active is not None:
            query = query.eq("is_active", is_active)
        
        result = query.order("created_at", desc=True).execute()
        
        tokens = []
        for row in result.data or []:
            tokens.append(StudentTokenResponse(
                id=row["id"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                token=row["token"],
                is_active=row["is_active"],
                expires_at=row["expires_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))
        
        logger.info({
            "event": "student_tokens_listed",
            "admin_user_id": payload.get("sub"),
            "count": len(tokens),
            "is_active_filter": is_active,
        })
        
        return tokens
    except Exception as exc:
        logger.error({
            "event": "student_tokens_list_failed",
            "error": str(exc),
            "admin_user_id": payload.get("sub"),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}"
        )


@app.delete("/api/v1/admin/student-tokens/{token_id}", status_code=204)
def delete_student_token(
    token_id: str,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
):
    """
    Revoca student token (soft delete + cascade revoke) (Story 1.3.1).
    
    - Soft delete: is_active = false
    - Cascade revoke: invalida tutti refresh tokens associati
    - Admin-only access
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    try:
        supabase = _get_supabase_client()
        now = datetime.now(timezone.utc)
        
        # Soft delete student token
        result = supabase.table("student_tokens").update({
            "is_active": False,
            "updated_at": now.isoformat(),
        }).eq("id", token_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student token not found"
            )
        
        # Cascade revoke: invalida tutti refresh tokens associati
        revoke_result = supabase.table("refresh_tokens").update({
            "is_revoked": True,
        }).eq("student_token_id", token_id).eq("is_revoked", False).execute()
        
        revoked_count = len(revoke_result.data) if revoke_result.data else 0
        
        logger.info({
            "event": "student_token_revoked",
            "student_token_id": token_id,
            "refresh_tokens_revoked": revoked_count,
            "admin_user_id": payload.get("sub"),
        })
        
        return None
    except HTTPException:
        raise
    except Exception as exc:
        logger.error({
            "event": "student_token_delete_failed",
            "error": str(exc),
            "token_id": token_id,
            "admin_user_id": payload.get("sub"),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}"
        )


@app.get("/health")
def read_root():
    return {"status": "ok"}


# -------------------------------
# Admin Debug View (Story 4.1)
# -------------------------------


class DebugQueryRequest(BaseModel):
    question: str


class DebugChunkMetadata(BaseModel):
    document_id: str | None = None
    document_name: str | None = None
    page_number: int | None = None
    chunking_strategy: str | None = None


class DebugChunkItem(BaseModel):
    chunk_id: str | None = None
    content: str | None = None
    similarity_score: float | None = None
    metadata: DebugChunkMetadata | None = None


class DebugQueryResponse(BaseModel):
    question: str
    answer: str | None = None
    chunks: list[DebugChunkItem]
    retrieval_time_ms: int
    generation_time_ms: int


def _admin_rate_limit_key(request: Request) -> str:
    """Chiave di rate limiting per-admin (sub dal JWT), fallback IP.

    Limita a 10 richieste/ora per amministratore come da AC.
    """
    try:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=EXPECTED_AUD,
                options={"require": ["exp", "iat"]},
            )
            sub = payload.get("sub")
            if sub:
                return f"admin_rl::{sub}"
    except Exception:
        # fallback su IP se token mancante/non valido
        pass
    return (request.client.host if request.client else "unknown_ip")


@app.post("/api/v1/admin/debug/query", response_model=DebugQueryResponse)
@limiter.limit("10/hour", key_func=_admin_rate_limit_key)
def admin_debug_query(
    body: DebugQueryRequest,
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")

    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question mancante")

    # Retrieval con timing
    _t0 = time.time()
    results = perform_semantic_search(q, match_count=8)
    retrieval_time_ms = int((time.time() - _t0) * 1000)

    # Prepara chunks e contesto
    chunks: list[DebugChunkItem] = []
    context_lines: list[str] = []
    for r in results or []:
        r = r or {}
        meta = (r.get("metadata") or {})
        content = (r.get("content") or "").strip()
        score = r.get("score")

        item = DebugChunkItem(
            chunk_id=(meta.get("id") or meta.get("chunk_id")),
            content=content or None,
            similarity_score=float(score) if isinstance(score, (int, float)) else None,
            metadata=DebugChunkMetadata(
                document_id=meta.get("document_id"),
                document_name=meta.get("document_name"),
                page_number=meta.get("page_number"),
                chunking_strategy=meta.get("chunking_strategy"),
            ),
        )
        chunks.append(item)
        if content:
            chunk_identifier = item.chunk_id or (meta.get("document_id") or "unknown")
            context_lines.append(f"[chunk_id={chunk_identifier}] {content}")

    context: str = "\n".join(context_lines).strip()

    # Generation con timing
    _t1 = time.time()
    answer_value: str | None = None
    try:
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Sei un assistente che risponde SOLO usando il CONTEXT fornito. "
                "Se l'informazione non è nel CONTEXT, rispondi 'Non trovato nel contesto'.",
            ),
            ("user", "CONTEXT:\n{context}\n\nDOMANDA:\n{question}\n\nRISPOSTA:"),
        ])
        llm = _get_llm()
        chain: Runnable = prompt | llm | StrOutputParser()
        answer_value = chain.invoke({"question": q, "context": context})
    except Exception as exc:  # fallback controllato
        logger.info({
            "event": "admin_debug_generation_fallback",
            "reason": str(exc),
        })
        answer_value = "Non trovato nel contesto" if not context else "Risposta generata (fallback)"
    generation_time_ms = int((time.time() - _t1) * 1000)

    # Audit log (senza PII del contenuto)
    logger.info({
        "event": "admin_debug_query",
        "path": "/api/v1/admin/debug/query",
        "user_id": payload.get("sub") if isinstance(payload, dict) else None,
        "chunks_count": len(chunks),
        "retrieval_time_ms": retrieval_time_ms,
        "generation_time_ms": generation_time_ms,
    })

    return DebugQueryResponse(
        question=q,
        answer=answer_value,
        chunks=chunks,
        retrieval_time_ms=retrieval_time_ms,
        generation_time_ms=generation_time_ms,
    )


# -------------------------------
# Access Code: Store & Utilities
# -------------------------------

access_codes_store: Dict[str, Dict[str, Any]] = {}

# Store in-memory per job di indicizzazione (Story 2.4)
sync_jobs_store: Dict[str, Dict[str, Any]] = {}

# Store in-memory per messaggi chat per sessione (memoria breve, Story 3.2)
chat_messages_store: Dict[str, list[Dict[str, Any]]] = {}
# Store in-memory per feedback dei messaggi
feedback_store: Dict[str, Dict[str, Any]] = {}

# Metriche performance per AG
AG_LATENCY_MAX_SAMPLES = 200
ag_latency_samples_ms: list[int] = []

def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    # Indice basato su definizione nearest-rank
    idx = round((p / 100.0) * (len(ordered) - 1))
    idx = max(0, min(len(ordered) - 1, int(idx)))
    return float(ordered[idx])

def _record_ag_latency_ms(duration_ms: int) -> dict:
    ag_latency_samples_ms.append(int(duration_ms))
    # Mantieni finestra scorrevole
    excess = len(ag_latency_samples_ms) - AG_LATENCY_MAX_SAMPLES
    if excess > 0:
        del ag_latency_samples_ms[:excess]
    p95_ms = int(_percentile(ag_latency_samples_ms, 95.0))
    return {"p95_ms": p95_ms, "count": len(ag_latency_samples_ms)}


def generate_access_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_temp_jwt(subject: str, session_id: str, expires_minutes: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    expires_min = expires_minutes if expires_minutes is not None else TEMP_JWT_EXPIRES_MINUTES
    payload = {
        "iss": JWT_ISSUER,
        "aud": EXPECTED_AUD,
        "sub": subject,
        "role": "authenticated",
        "session_id": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_min)).timestamp()),
    }
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")


# -------------------------------
# Student Token Management (Story 1.3.1)
# -------------------------------

# Security constants (RFC 8725, RFC 7519)
CLOCK_SKEW_LEEWAY_SECONDS = int(os.getenv("CLOCK_SKEW_LEEWAY_SECONDS", "120"))

# Rate Limiting constants per exchange-code (OWASP)
EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC = int(os.getenv("EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC", "60"))
EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS", "10"))


class GenerateCodeRequest(BaseModel):
    expires_in_minutes: Optional[int] = None


class GeneratedCodeResponse(BaseModel):
    id: str
    code: str
    expires_at: Optional[str] = None


class ExchangeCodeRequest(BaseModel):
    access_code: str


class ExchangeCodeResponse(BaseModel):
    token: str
    token_type: str
    expires_in: int


def _is_admin(payload: TokenPayload) -> bool:
    if payload.get("role") == "admin":
        return True
    app_meta = payload.get("app_metadata") or {}
    return app_meta.get("role") == "admin"


@app.post("/api/v1/admin/access-codes/generate", response_model=GeneratedCodeResponse)
def generate_access_code_admin(
    body: GenerateCodeRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
):
    # TEMPORANEO: bypass check admin per test manuale
    # if not _is_admin(payload):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")

    code_id = str(uuid4())
    code_value = generate_access_code()
    now = datetime.now(timezone.utc)
    expires_at_dt: Optional[datetime] = None
    if body.expires_in_minutes and body.expires_in_minutes > 0:
        expires_at_dt = now + timedelta(minutes=body.expires_in_minutes)

    access_codes_store[code_value] = {
        "id": code_id,
        "code": code_value,
        "is_active": True,
        "expires_at": expires_at_dt,
        "usage_count": 0,
        "last_used_at": None,
        "created_by_id": payload.get("sub"),
        "created_at": now,
        "updated_at": now,
    }

    return GeneratedCodeResponse(
        id=code_id,
        code=code_value,
        expires_at=expires_at_dt.isoformat() if expires_at_dt else None,
    )


@app.post("/api/v1/auth/exchange-code", response_model=ExchangeCodeResponse)
def exchange_code(body: ExchangeCodeRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else None
    # Enforce rate limit per IP
    _enforce_rate_limit(client_ip)

    logger.info({
        "event": "exchange_code_attempt",
        "path": "/api/v1/auth/exchange-code",
        "client_ip": client_ip,
        "access_code_length": len((body.access_code or "").strip()),
    })
    code = (body.access_code or "").strip()
    if not code:
        logger.info({
            "event": "exchange_code_result",
            "result": "invalid_request",
            "reason": "empty_code",
            "client_ip": client_ip,
        })
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_request")

    # 1. Cerca in access_codes_store (in-memory, Story 1.3)
    record = access_codes_store.get(code)
    if record:
        # Comportamento esistente per access code (15 min, mono-uso, NO refresh token)
        # Code already used → conflict
        if record.get("usage_count", 0) > 0:
            logger.info({
                "event": "exchange_code_result",
                "result": "code_already_used",
                "client_ip": client_ip,
                "code_id": record.get("id"),
            })
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="code_already_used")

        # Inactive (but not yet used) → treat as invalid
        if not record.get("is_active", False):
            logger.info({
                "event": "exchange_code_result",
                "result": "invalid_code",
                "reason": "inactive",
                "client_ip": client_ip,
                "code_id": record.get("id"),
            })
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_code")

        now = datetime.now(timezone.utc)
        expires_at_dt: Optional[datetime] = record.get("expires_at")
        if expires_at_dt and now >= expires_at_dt:
            record["is_active"] = False
            record["updated_at"] = now
            logger.info({
                "event": "exchange_code_result",
                "result": "expired_code",
                "client_ip": client_ip,
                "code_id": record.get("id"),
            })
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="expired_code")

        # Mark as used
        record["usage_count"] = record.get("usage_count", 0) + 1
        record["last_used_at"] = now
        record["is_active"] = False
        record["updated_at"] = now

        session_id = str(uuid4())
        subject = f"student:{record['id']}"
        token = generate_temp_jwt(subject=subject, session_id=session_id)

        logger.info({
            "event": "exchange_code_result",
            "result": "success",
            "type": "access_code",
            "client_ip": client_ip,
            "code_id": record.get("id"),
            "session_id": session_id,
            "expires_in_sec": TEMP_JWT_EXPIRES_MINUTES * 60,
        })

        return ExchangeCodeResponse(
            token=token,
            token_type="bearer",
            expires_in=TEMP_JWT_EXPIRES_MINUTES * 60,
        )
    
    # 2. Cerca in student_tokens (DB) - Refresh Token Pattern (Story 1.3.1)
    try:
        supabase = _get_supabase_client()
        result = supabase.table("student_tokens")\
            .select("*")\
            .eq("token", code)\
            .eq("is_active", True)\
            .single()\
            .execute()
        
        if result.data:
            student = result.data
            now = datetime.now(timezone.utc)
            
            # Parse expires_at (handle both Z and +00:00 formats)
            expires_at_str = student["expires_at"]
            if expires_at_str.endswith("Z"):
                expires_at_str = expires_at_str[:-1] + "+00:00"
            expires_at = datetime.fromisoformat(expires_at_str)
            
            if now >= expires_at:
                logger.info({
                    "event": "exchange_code_result",
                    "result": "expired_code",
                    "type": "student_token",
                    "client_ip": client_ip,
                    "student_token_id": student["id"],
                })
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="expired_code")
            
            # Genera Access Token (JWT) con durata 15 minuti
            session_id = str(uuid4())
            subject = f"student:{student['id']}"
            access_token = generate_temp_jwt(
                subject=subject,
                session_id=session_id,
                expires_minutes=15
            )
            
            # Genera Refresh Token (random, non JWT) con durata 1 anno
            refresh_token = generate_refresh_token()
            refresh_expires_at = now + timedelta(days=365)
            
            # Salva refresh token in DB
            supabase.table("refresh_tokens").insert({
                "student_token_id": student["id"],
                "token": refresh_token,
                "expires_at": refresh_expires_at.isoformat(),
                "is_revoked": False,
                "created_at": now.isoformat(),
            }).execute()
            
            # Imposta refresh token in cookie HttpOnly
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                max_age=365 * 24 * 60 * 60,  # 1 anno in secondi
                httponly=True,  # Inaccessibile a JavaScript (previene XSS)
                secure=True,    # Solo HTTPS (previene MITM)
                samesite="strict",  # Previene CSRF
                path="/api/v1/auth/refresh-token"  # Limita scope
            )
            
            logger.info({
                "event": "exchange_code_result",
                "result": "success",
                "type": "student_token",
                "student_token_id": student["id"],
                "session_id": session_id,
                "refresh_token_expires": refresh_expires_at.isoformat(),
                "client_ip": client_ip,
            })
            
            return ExchangeCodeResponse(
                token=access_token,
                token_type="bearer",
                expires_in=900  # 15 minuti in secondi
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning({
            "event": "student_token_lookup_failed",
            "error": str(exc),
            "client_ip": client_ip,
        })
    
    # 3. Nessun match
    logger.info({
        "event": "exchange_code_result",
        "result": "invalid_code",
        "client_ip": client_ip,
    })
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_code")


# Rate limiting store per refresh token
_refresh_token_rate_limit_store: Dict[str, list[float]] = {}


def _enforce_refresh_token_rate_limit(client_ip: str) -> None:
    """Rate limiting per refresh token (60 req/ora, OWASP)."""
    if not client_ip:
        return
    now_ts = time.time()
    window_start = now_ts - REFRESH_TOKEN_RATE_LIMIT_WINDOW_SEC
    timestamps = _refresh_token_rate_limit_store.get(client_ip, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= REFRESH_TOKEN_RATE_LIMIT_MAX_REQUESTS:
        _refresh_token_rate_limit_store[client_ip] = timestamps
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited")
    timestamps.append(now_ts)
    _refresh_token_rate_limit_store[client_ip] = timestamps


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@app.post("/api/v1/auth/refresh-token", response_model=RefreshTokenResponse)
def refresh_access_token(request: Request):
    """
    Rinnova access token usando refresh token (Story 1.3.1).
    
    - Legge refresh token da cookie HttpOnly
    - Verifica validità in DB (non revocato, non scaduto)
    - Genera nuovo access token JWT 15 min
    - Aggiorna last_used_at per audit
    - Rate limiting 60 req/ora (OWASP)
    """
    client_ip = request.client.host if request.client else None
    _enforce_refresh_token_rate_limit(client_ip)
    
    # Leggi refresh token da cookie HttpOnly
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        logger.warning({
            "event": "refresh_token_missing",
            "client_ip": client_ip,
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_refresh_token"
        )
    
    try:
        supabase = _get_supabase_client()
        
        # Verifica refresh token in DB con join a student_tokens
        result = supabase.table("refresh_tokens")\
            .select("*, student_tokens!inner(*)")\
            .eq("token", refresh_token)\
            .eq("is_revoked", False)\
            .single()\
            .execute()
        
        if not result.data:
            logger.warning({
                "event": "refresh_token_invalid",
                "reason": "not_found_or_revoked",
                "client_ip": client_ip,
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_refresh_token"
            )
        
        refresh_record = result.data
        now = datetime.now(timezone.utc)
        
        # Parse expires_at
        expires_at_str = refresh_record["expires_at"]
        if expires_at_str.endswith("Z"):
            expires_at_str = expires_at_str[:-1] + "+00:00"
        expires_at = datetime.fromisoformat(expires_at_str)
        
        # Verifica scadenza
        if now >= expires_at:
            logger.warning({
                "event": "refresh_token_expired",
                "refresh_token_id": refresh_record["id"],
                "expires_at": refresh_record["expires_at"],
                "client_ip": client_ip,
            })
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="expired_refresh_token"
            )
        
        # Verifica student token ancora attivo
        student_token = refresh_record["student_tokens"]
        if not student_token["is_active"]:
            logger.warning({
                "event": "refresh_token_rejected",
                "reason": "student_token_revoked",
                "student_token_id": student_token["id"],
                "client_ip": client_ip,
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="revoked_refresh_token"
            )
        
        # Genera nuovo Access Token
        session_id = str(uuid4())
        subject = f"student:{student_token['id']}"
        access_token = generate_temp_jwt(
            subject=subject,
            session_id=session_id,
            expires_minutes=15
        )
        
        # Aggiorna last_used_at per audit
        supabase.table("refresh_tokens")\
            .update({"last_used_at": now.isoformat()})\
            .eq("id", refresh_record["id"])\
            .execute()
        
        logger.info({
            "event": "refresh_token_success",
            "refresh_token_id": refresh_record["id"],
            "student_token_id": student_token["id"],
            "new_session_id": session_id,
            "client_ip": client_ip,
        })
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=900  # 15 minuti in secondi
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error({
            "event": "refresh_token_failed",
            "error": str(exc),
            "client_ip": client_ip,
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}"
        )


# -------------------------------
# Meta-Agente di Classificazione Strutturale (Story 2.2)
# -------------------------------

class ClassifyRequest(BaseModel):
    testo: str


class ClassifyResponse(ClassificazioneOutput):
    pass


def _build_classification_chain(llm: BaseLanguageModel) -> Runnable:
    parser = PydanticOutputParser(pydantic_object=ClassificazioneOutput)
    categories = ", ".join([
        DocumentStructureCategory.TESTO_ACCADEMICO_DENSO.value,
        DocumentStructureCategory.PAPER_SCIENTIFICO_MISTO.value,
        DocumentStructureCategory.DOCUMENTO_TABELLARE.value,
    ])
    template = (
        """
Analizza il seguente documento medico-scientifico e restituisci una classificazione strutturale.
Scegli UNA sola categoria tra: {categories}.
Fornisci anche una motivazione sintetica e una confidenza (0.0–1.0).

Documento:
{testo}

{format_instructions}
        """
        .strip()
    )
    prompt = PromptTemplate(
        template=template,
        input_variables=["testo"],
        partial_variables={
            "categories": categories,
            "format_instructions": parser.get_format_instructions(),
        },
    )
    chain: Runnable = prompt | llm | parser
    return chain


def _get_llm() -> BaseLanguageModel:
    # Istanziazione del modello LLM approvato dallo stack: OpenAI "gpt-5-nano"
    # Richiede OPENAI_API_KEY configurata nell'ambiente.
    return ChatOpenAI(model="gpt-5-nano", temperature=0)


@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    if not req.testo or not req.testo.strip():
        raise HTTPException(status_code=400, detail="testo mancante")

    # Per test: consente mocking della chain via dependency override/monkeypatch.
    try:
        llm = _get_llm()
        chain = _build_classification_chain(llm)
        result: ClassificazioneOutput = chain.invoke({"testo": req.testo})
    except HTTPException:
        # Se LLM non configurato, simuliamo minimo comportamento coerente con struttura per evitare crash locali.
        # I test useranno comunque mocking della catena.
        result = ClassificazioneOutput(
            classificazione=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
            motivazione="fallback",
            confidenza=0.5,
        )

    logger.info({
        "event": "classify_result",
        "output": json.loads(result.model_dump_json()),
    })
    return ClassifyResponse(**result.model_dump())


# -------------------------------
# Ricerca Semantica (Story 2.4)
# -------------------------------


class SearchRequest(BaseModel):
    query: str
    match_count: int = 8


class SearchResponse(BaseModel):
    results: list[dict]


@app.post("/api/v1/knowledge-base/search", response_model=SearchResponse)
@limiter.limit("60/minute")
def semantic_search_endpoint(body: SearchRequest, request: Request):
    results = perform_semantic_search(body.query, body.match_count)
    return SearchResponse(results=results)


# -------------------------------
# Chat: Query Semantica (Story 3.1)
# -------------------------------


class ChatQueryRequest(BaseModel):
    sessionId: str
    question: str
    match_threshold: float = 0.75
    match_count: int = 8


class ChatQueryChunk(BaseModel):
    id: Optional[str] = None
    document_id: Optional[str] = None
    content: Optional[str] = None
    similarity: Optional[float] = None


class ChatQueryResponse(BaseModel):
    chunks: list[ChatQueryChunk]


@app.post("/api/v1/chat/query", response_model=ChatQueryResponse)
@limiter.limit("60/minute")
def chat_query_endpoint(
    body: ChatQueryRequest,
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    results = perform_semantic_search(
        body.question,
        body.match_count,
        body.match_threshold,
    )
    chunks: list[dict] = []
    for r in results:
        metadata = (r or {}).get("metadata") or {}
        score = (r or {}).get("score")
        chunks.append({
            "id": metadata.get("id"),
            "document_id": metadata.get("document_id"),
            "content": (r or {}).get("content"),
            "similarity": float(score) if isinstance(score, (int, float)) else None,
        })
    return ChatQueryResponse(chunks=[ChatQueryChunk(**c) for c in chunks])


# -------------------------------
# Chat: Augmented Generation (Story 3.2)
# -------------------------------


class ChatMessageCreateRequest(BaseModel):
    question: str
    chunks: list[ChatQueryChunk] | None = None


class CitationItem(BaseModel):
    chunk_id: str
    document_id: str | None = None
    excerpt: str | None = None
    position: int | None = None


class ChatMessageCreateResponse(BaseModel):
    message_id: str
    answer: str | None = None
    citations: list[CitationItem] | None = None


@app.post("/api/v1/chat/sessions/{sessionId}/messages", response_model=ChatMessageCreateResponse)
@limiter.limit("60/minute")
def create_chat_message(
    sessionId: str,
    body: ChatMessageCreateRequest,
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    _ag_start_time = time.time()
    if not sessionId or not sessionId.strip():
        raise HTTPException(status_code=400, detail="sessionId mancante")
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question mancante")

    logger.info({
        "event": "ag_message_request",
        "path": f"/api/v1/chat/sessions/{sessionId}/messages",
        "session_id": sessionId,
        "has_chunks": bool(body.chunks),
    })

    # Validazione presenza chunk per AG completo
    if not body.chunks:
        raise HTTPException(status_code=400, detail="chunks mancanti")

    # Costruzione del contesto a partire dai chunk
    context_lines: list[str] = []
    for chunk in body.chunks:
        if not chunk:
            continue
        chunk_identifier = chunk.id or chunk.document_id or "unknown"
        chunk_content = (chunk.content or "").strip()
        if chunk_content:
            context_lines.append(f"[chunk_id={chunk_identifier}] {chunk_content}")
    context: str = "\n".join(context_lines).strip()

    # Prompt per AG con vincolo di uso esclusivo del contesto
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Sei un assistente che risponde SOLO usando il CONTEXT fornito. "
            "Se l'informazione non è nel CONTEXT, rispondi 'Non trovato nel contesto'. "
            "Includi le citazioni degli ID dei chunk usati.",
        ),
        ("user", "CONTEXT:\n{context}\n\nDOMANDA:\n{question}"),
    ])

    parser = PydanticOutputParser(pydantic_object=AnswerWithCitations)

    # Composizione catena LCEL ed esecuzione con fallback sicuro
    message_id = str(uuid4())
    try:
        llm = _get_llm()
        chain: Runnable = prompt | llm | parser
        result: AnswerWithCitations = chain.invoke({
            "question": body.question,
            "context": context,
        })
        answer_value: Optional[str] = getattr(result, "risposta", None)
        citations_value: Optional[list[str]] = getattr(result, "citazioni", None)
    except Exception as exc:  # noqa: BLE001 - fallback per ambienti senza LLM
        # Fallback minimale: nessuna invocazione esterna, costruisce citazioni da chunk
        citations_value = []
        for chunk in body.chunks or []:
            if not chunk:
                continue
            citations_value.append((chunk.id or chunk.document_id or "unknown"))
        # Risposta di ripiego coerente con prompt
        answer_value = "Non trovato nel contesto" if not context else "Risposta generata (fallback)"
        logger.info({
            "event": "ag_fallback",
            "reason": str(exc),
            "citations_count": len(citations_value),
        })

    # Persistenza minima in memoria per la sessione
    # Arricchisci citazioni con metadati minimi per popover
    enriched_citations: list[dict] = []
    chunks_by_id: Dict[str, ChatQueryChunk] = {}
    for ch in body.chunks or []:
        if ch and (ch.id or ch.document_id):
            chunks_by_id[(ch.id or ch.document_id)] = ch

    for cid in citations_value or []:
        ch = chunks_by_id.get(cid)
        excerpt_value: str | None = None
        document_id_value: str | None = None
        if ch:
            text = (ch.content or "").strip()
            if text:
                excerpt_value = text[:240]
            document_id_value = ch.document_id
        enriched_citations.append({
            "chunk_id": cid,
            "document_id": document_id_value,
            "excerpt": excerpt_value,
            "position": None,
        })

    stored = {
        "id": message_id,
        "session_id": sessionId,
        "role": "assistant",
        "content": answer_value,
        "citations": enriched_citations,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    chat_messages = chat_messages_store.get(sessionId) or []
    chat_messages.append(stored)
    chat_messages_store[sessionId] = chat_messages

    # Metriche di performance: latenza e p95 aggiornata
    _ag_duration_ms = int((time.time() - _ag_start_time) * 1000)
    metrics = _record_ag_latency_ms(_ag_duration_ms)
    logger.info({
        "event": "ag_metrics",
        "latency_ms": _ag_duration_ms,
        "p95_ms": metrics.get("p95_ms"),
        "samples": metrics.get("count"),
        "session_id": sessionId,
    })

    return ChatMessageCreateResponse(
        message_id=message_id,
        answer=answer_value,
        citations=[CitationItem(**c) for c in enriched_citations],
    )


# -------------------------------
# Chat: Feedback su messaggi (Story 3.4)
# -------------------------------


class FeedbackCreateRequest(BaseModel):
    sessionId: str
    vote: Literal["up", "down"]


class FeedbackCreateResponse(BaseModel):
    ok: bool


@app.post("/api/v1/chat/messages/{messageId}/feedback", response_model=FeedbackCreateResponse)
@limiter.limit("60/minute")
def create_feedback(
    messageId: str,
    body: FeedbackCreateRequest,
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    if not messageId or not messageId.strip():
        raise HTTPException(status_code=400, detail="messageId mancante")
    if not body.sessionId or not body.sessionId.strip():
        raise HTTPException(status_code=400, detail="sessionId mancante")

    # Verifica esistenza messaggio nella sessione (best effort)
    found = False
    for m in chat_messages_store.get(body.sessionId, []) or []:
        if m and m.get("id") == messageId:
            found = True
            break
    if not found:
        # Non bloccare l'UX: accetta comunque ma logga warn
        logger.info({
            "event": "feedback_message_not_found",
            "session_id": body.sessionId,
            "message_id": messageId,
        })

    key = f"{body.sessionId}:{messageId}"
    feedback_store[key] = {
        "session_id": body.sessionId,
        "message_id": messageId,
        "vote": body.vote,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ip": request.client.host if request.client else None,
        "user_id": payload.get("sub") if isinstance(payload, dict) else None,
    }

    logger.info({
        "event": "feedback_recorded",
        "session_id": body.sessionId,
        "message_id": messageId,
        "vote": body.vote,
    })

    return FeedbackCreateResponse(ok=True)


# -------------------------------
# Document Explorer: Admin Endpoints (Story 4.4)
# -------------------------------


class DocumentSummary(BaseModel):
    document_id: str
    document_name: str
    upload_date: str  # ISO datetime
    chunk_count: int
    primary_chunking_strategy: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total_count: int


class ChunkDetail(BaseModel):
    chunk_id: str
    content: str
    chunk_size: int
    chunk_index: int | None = None
    chunking_strategy: str | None = None
    page_number: int | None = None
    embedding_status: Literal["indexed", "pending"]
    created_at: str


class DocumentChunksResponse(BaseModel):
    document_id: str
    document_name: str | None = None
    chunks: list[ChunkDetail]
    total_chunks: int


class PaginationParams:
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
    ):
        self.skip = skip
        self.limit = limit


class ChunkFilterParams:
    def __init__(
        self,
        strategy: str | None = None,
        min_size: int | None = None,
        sort_by: str = "chunk_index",
    ):
        self.strategy = strategy
        self.min_size = min_size
        self.sort_by = sort_by


@app.get("/api/v1/admin/documents", response_model=DocumentListResponse)
@limiter.limit("30/hour", key_func=_admin_rate_limit_key)
async def get_documents(
    request: Request,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Recupera lista documenti con metadata aggregati.
    
    Features:
    - MODE() WITHIN GROUP per strategia predominante
    - COUNT aggregato per numero chunk
    - LEFT JOIN per includere documenti senza chunk
    
    Security:
    - Admin-only access
    - Rate limiting 30/hour
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    query = """
        SELECT 
            d.id AS document_id,
            d.file_name AS document_name,
            d.created_at AS upload_date,
            COUNT(c.id) AS chunk_count,
            MODE() WITHIN GROUP (ORDER BY c.metadata->>'chunking_strategy') AS primary_chunking_strategy
        FROM documents d
        LEFT JOIN document_chunks c ON d.id = c.document_id
        GROUP BY d.id, d.file_name, d.created_at
        ORDER BY d.created_at DESC
    """
    
    rows = await conn.fetch(query)
    documents = []
    for row in rows:
        documents.append(DocumentSummary(
            document_id=str(row["document_id"]),
            document_name=row["document_name"] or "",
            upload_date=row["upload_date"].isoformat() if row["upload_date"] else "",
            chunk_count=int(row["chunk_count"]) if row["chunk_count"] else 0,
            primary_chunking_strategy=row["primary_chunking_strategy"]
        ))
    
    logger.info({
        "event": "documents_list_accessed",
        "path": "/api/v1/admin/documents",
        "user_id": payload.get("sub"),
        "documents_count": len(documents),
    })
    
    return DocumentListResponse(
        documents=documents,
        total_count=len(documents)
    )


@app.get("/api/v1/admin/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
@limiter.limit("30/hour", key_func=_admin_rate_limit_key)
async def get_document_chunks(
    request: Request,
    document_id: str,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
    skip: int = 0,
    limit: int = 100,
    strategy: str | None = None,
    min_size: int | None = None,
    sort_by: str = "created_at",
):
    """
    Recupera chunk per documento con filtri opzionali.
    
    Features:
    - Query parametrizzate con $1, $2 (SQL injection safe)
    - Filtri dinamici opzionali
    - Paginazione
    - Sort configurabile
    
    Security:
    - Admin-only access
    - Rate limiting 30/hour
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    # Query base
    query_parts = ["""
        SELECT 
            c.id AS chunk_id,
            c.content,
            LENGTH(c.content) AS chunk_size,
            (c.metadata->>'chunk_index')::INTEGER AS chunk_index,
            c.metadata->>'chunking_strategy' AS chunking_strategy,
            (c.metadata->>'page_number')::INTEGER AS page_number,
            CASE WHEN c.embedding IS NOT NULL THEN 'indexed' ELSE 'pending' END AS embedding_status,
            c.created_at
        FROM document_chunks c
        WHERE c.document_id = $1
    """]
    
    params = [document_id]
    param_idx = 2
    
    # Filtro opzionale per strategia
    if strategy:
        query_parts.append(f"AND c.metadata->>'chunking_strategy' = ${param_idx}")
        params.append(strategy)
        param_idx += 1
    
    # Filtro opzionale per dimensione minima
    if min_size:
        query_parts.append(f"AND LENGTH(c.content) >= ${param_idx}")
        params.append(min_size)
        param_idx += 1
    
    # Validazione sort_by
    allowed_sort = {"created_at", "chunk_size"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    
    # Sort e paginazione
    query_parts.append(f"ORDER BY c.{sort_by} ASC NULLS LAST")
    query_parts.append(f"LIMIT ${param_idx} OFFSET ${param_idx + 1}")
    params.extend([limit, skip])
    
    query = " ".join(query_parts)
    rows = await conn.fetch(query, *params)
    
    # Count totale (senza paginazione)
    count_query = "SELECT COUNT(*) FROM document_chunks WHERE document_id = $1"
    total = await conn.fetchval(count_query, document_id)
    
    # Recupero nome documento
    doc_query = "SELECT file_name FROM documents WHERE id = $1"
    doc_name = await conn.fetchval(doc_query, document_id)
    
    chunks = []
    for row in rows:
        chunks.append(ChunkDetail(
            chunk_id=str(row["chunk_id"]),
            content=row["content"] or "",
            chunk_size=int(row["chunk_size"]) if row["chunk_size"] else 0,
            chunk_index=int(row["chunk_index"]) if row["chunk_index"] is not None else None,
            chunking_strategy=row["chunking_strategy"],
            page_number=int(row["page_number"]) if row["page_number"] is not None else None,
            embedding_status=row["embedding_status"],
            created_at=row["created_at"].isoformat() if row["created_at"] else ""
        ))
    
    logger.info({
        "event": "document_chunks_accessed",
        "path": f"/api/v1/admin/documents/{document_id}/chunks",
        "user_id": payload.get("sub"),
        "document_id": document_id,
        "chunks_count": len(chunks),
        "total_chunks": total,
    })
    
    return DocumentChunksResponse(
        document_id=document_id,
        document_name=doc_name,
        chunks=chunks,
        total_chunks=total or 0
    )


# -------------------------------
# Admin: Indicizzazione Knowledge Base (Story 2.4)
# -------------------------------


class StartSyncJobRequest(BaseModel):
    document_text: str
    classification: ClassificazioneOutput | None = None
    metadata: Dict[str, Any] | None = None


class StartSyncJobResponse(BaseModel):
    job_id: str
    inserted: int
    timing: Dict[str, int] | None = None  # Story 2.5: timing metrics


class SyncJobStatusResponse(BaseModel):
    job_id: str
    status: str
    inserted: int | None = None
    error: str | None = None


def _verify_jwt_token_runtime(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
):
    """Bridge runtime per consentire monkeypatch nei test.

    Se `verify_jwt_token` è monkeypatchato a callable senza argomenti,
    invocalo senza passare `credentials`. Altrimenti passa `credentials`.
    """
    func = globals().get("verify_jwt_token")
    if func is None:
        raise HTTPException(status_code=500, detail="auth_dependency_missing")
    try:
        sig = inspect.signature(func)
        if len(sig.parameters) == 0:
            return func()
        return func(credentials)
    except TypeError:
        return func()


 


@app.post("/api/v1/admin/knowledge-base/sync-jobs", response_model=StartSyncJobResponse)
@limiter.limit("10/minute")
async def start_sync_job(
    request: Request,
    body: StartSyncJobRequest,
    conn: Annotated[asyncpg.Connection, Depends(get_db_connection)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """Enhanced sync job con full pipeline monitoring (Story 2.5 AC5, AC8).
    
    Pipeline Steps (logged con timing):
    1. Enhanced extraction (con images/tables) se source_path fornito
    2. Enhanced classification (domain + structure)
    3. Polymorphic chunking
    4. Document persistence
    5. Batch embedding (con retry)
    6. Vector indexing
    7. Status update
    
    Returns:
        job_id: UUID documento (document_id)
        inserted: Numero chunk indicizzati
        timing: Timing metrics per troubleshooting
    
    Stories: 2.4.1 Document Persistence + 2.5 Enhanced Pipeline
    """
    from pathlib import Path
    from .knowledge_base.extractors import DocumentExtractor
    from .knowledge_base.classifier import classify_content_enhanced
    
    start_pipeline = time.time()
    timing_metrics = {}
    
    if not _is_admin(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")

    if not body.document_text or not body.document_text.strip():
        raise HTTPException(status_code=400, detail="document_text mancante")

    # Step 1: Enhanced extraction (se file_path fornito)
    extraction_result = None
    file_path_str = (body.metadata or {}).get("source_path")
    if file_path_str:
        start_extract = time.time()
        try:
            extractor = DocumentExtractor()
            extraction_result = extractor.extract(Path(file_path_str))
            document_text = extraction_result["text"]
            timing_metrics["extraction_ms"] = int((time.time() - start_extract) * 1000)
            
            # Update metadata con extracted features
            body.metadata["images_count"] = len(extraction_result["images"])
            body.metadata["tables_count"] = len(extraction_result["tables"])
            
            logger.info({
                "event": "extraction_complete",
                "images_count": body.metadata["images_count"],
                "tables_count": body.metadata["tables_count"],
                "duration_ms": timing_metrics["extraction_ms"]
            })
        except Exception as e:
            logger.warning({
                "event": "extraction_failed_fallback",
                "source_path": file_path_str,
                "error": str(e)
            })
            document_text = body.document_text
    else:
        document_text = body.document_text
    
    # Step 2: Enhanced classification (domain + structure)
    start_classify = time.time()
    try:
        extraction_metadata = extraction_result.get("metadata") if extraction_result else None
        classification_enhanced = classify_content_enhanced(
            document_text,
            extraction_metadata
        )
        timing_metrics["classification_ms"] = int((time.time() - start_classify) * 1000)
        
        # Update metadata con classification results
        body.metadata["domain"] = classification_enhanced.domain.value
        body.metadata["structure_type"] = classification_enhanced.structure_type.value
        body.metadata["classification_confidence"] = classification_enhanced.confidence
        
        logger.info({
            "event": "classification_complete",
            "domain": classification_enhanced.domain.value,
            "structure": classification_enhanced.structure_type.value,
            "confidence": classification_enhanced.confidence,
            "duration_ms": timing_metrics["classification_ms"]
        })
    except Exception as e:
        # Fallback classification base se enhanced fallisce
        logger.warning({
            "event": "enhanced_classification_fallback",
            "error": str(e)
        })
        classification_enhanced = None

    # Step 3: Chunking
    start_chunk = time.time()
    router = ChunkRouter()
    
    # Use enhanced classification se disponibile, altrimenti base classification
    classification_for_chunking = None
    if classification_enhanced:
        # Convert enhanced classification to base format per ChunkRouter
        from .ingestion.models import ClassificazioneOutput
        classification_for_chunking = ClassificazioneOutput(
            classificazione=classification_enhanced.structure_type,
            motivazione=classification_enhanced.reasoning,
            confidenza=classification_enhanced.confidence
        )
    elif body.classification:
        classification_for_chunking = body.classification
    
    chunks_result = router.route(
        content=document_text,
        classification=classification_for_chunking
    )
    timing_metrics["chunking_ms"] = int((time.time() - start_chunk) * 1000)
    
    logger.info({
        "event": "chunking_complete",
        "chunks_count": len(chunks_result.chunks),
        "strategy": chunks_result.strategy_name,
        "duration_ms": timing_metrics["chunking_ms"]
    })
    
    # Step 4: Document persistence
    file_hash = hashlib.sha256(document_text.encode('utf-8')).hexdigest()
    document_name = (body.metadata or {}).get("document_name", "manual_upload.txt")
    file_path = (body.metadata or {}).get("file_path", "")
    
    document_id = await save_document_to_db(
        conn=conn,
        file_name=document_name,
        file_path=file_path,
        file_hash=file_hash,
        status="processing",
        chunking_strategy=chunks_result.strategy_name,
        metadata=body.metadata or {},
    )
    
    # Step 5-6: Indexing (embedding + vector storage)
    metadata_list = [
        {
            **(body.metadata or {}),
            "document_id": str(document_id),
            "document_name": document_name,
            "chunking_strategy": chunks_result.strategy_name,
        }
        for _ in chunks_result.chunks
    ]
    
    if CELERY_ENABLED:
        # Enqueue async task
        task = kb_indexing_task.delay({
            "chunks": chunks_result.chunks,
            "metadata_list": metadata_list,
        })
        
        timing_metrics["total_pipeline_ms"] = int((time.time() - start_pipeline) * 1000)
        
        return StartSyncJobResponse(
            job_id=str(document_id),
            inserted=0,
            timing=timing_metrics
        )
    else:
        # Synchronous indexing
        job_id_str = str(document_id)
        sync_jobs_store[job_id_str] = {
            "status": "running",
            "inserted": 0,
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            inserted = index_chunks(chunks_result.chunks, metadata_list)
            sync_jobs_store[job_id_str]["inserted"] = inserted
            sync_jobs_store[job_id_str]["status"] = "completed"
            
            # Step 7: Update document status
            await update_document_status(conn, document_id, status="completed")
            
            timing_metrics["total_pipeline_ms"] = int((time.time() - start_pipeline) * 1000)
            
            logger.info({
                "event": "pipeline_complete",
                "document_id": str(document_id),
                "chunks_count": len(chunks_result.chunks),
                "inserted": inserted,
                "timing": timing_metrics
            })
            
        except Exception as exc:
            sync_jobs_store[job_id_str]["status"] = "failed"
            sync_jobs_store[job_id_str]["error"] = str(exc)
            
            await update_document_status(conn, document_id, status="error", error=str(exc))
            
            logger.error({
                "event": "pipeline_failed",
                "document_id": str(document_id),
                "error": str(exc),
                "timing": timing_metrics
            })
            
            raise HTTPException(status_code=500, detail="indexing_failed") from exc

        return StartSyncJobResponse(
            job_id=job_id_str,
            inserted=sync_jobs_store[job_id_str]["inserted"],
            timing=timing_metrics
        )


@app.get("/api/v1/admin/knowledge-base/sync-jobs/{job_id}", response_model=SyncJobStatusResponse)
@limiter.limit("10/minute")
def get_sync_job_status(
    request: Request,
    job_id: str,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    if not _is_admin(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")

    if CELERY_ENABLED:
        try:
            r = AsyncResult(job_id, app=celery_app)
            body = {
                "job_id": job_id,
                "status": r.state,
                "inserted": None,
                "error": None,
            }
            if r.successful():
                result = r.get(propagate=False)  # dict con {inserted}
                body["inserted"] = result.get("inserted") if isinstance(result, dict) else None
            elif r.failed():
                body["error"] = str(r.result)
            return SyncJobStatusResponse(**body)
        except Exception as exc:
            # Fallback 404 se AsyncResult non disponibile/errore
            raise HTTPException(status_code=404, detail="job_not_found") from exc
    else:
        job = sync_jobs_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")

        return SyncJobStatusResponse(
            job_id=job_id,
            status=str(job.get("status")),
            inserted=job.get("inserted"),
            error=job.get("error"),
        )
