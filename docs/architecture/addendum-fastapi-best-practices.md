# Addendum: FastAPI Best Practices per FisioRAG

**Status**: Active  
**Version**: 1.1  
**Date**: 2025-10-08  
**Last Update**: 2025-10-08 (RFC compliance JWT validation)

## Context

Documento creato in risposta ai rischi emersi dall'analisi Story 4.1 (Admin Debug View) e applicabile a tutti gli endpoint FastAPI del progetto FisioRAG.

**Rischi Mitigati**:
- R-4.1-1: Admin Authentication Bypass (CRITICAL)
- R-4.1-2: Data Exposure in Debug View (HIGH)
- R-4.1-3: Uncontrolled API Costs (HIGH)
- R-4.1-6: Error Handling Completeness (MEDIUM)

**Aggiornamento v1.1** (2025-10-08):
- Integrazione standard RFC 8725, RFC 7519, RFC 6749 per JWT validation
- Clock skew tolerance configurabile via environment variable
- OAuth 2.0 error codes standard conformi RFC 6749 Sezione 5.2
- Pattern riutilizzabile per Story 1.3.1 e successive implementazioni security-critical

[Fonti: `docs/qa/assessments/4.1-risk-20250930.md`; `docs/qa/assessments/4.1-test-design-20250930.md`; `materiale_ufficiale-story1.3.1.md`]

---

## 1. Endpoint Protetto con JWT (CRITICAL - R-4.1-1)

### Pattern Standard per Auth Admin

**Problema**: Rischio bypass autenticazione admin con JWT manipulation o role tampering.

**Soluzione**: Dependency riutilizzabile con verifica JWT + role check esplicito.

```python
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError

# Configurazione security
security = HTTPBearer(auto_error=False)

# Configurazione JWT (da Settings)
SECRET_KEY = "load-from-settings"
ALGORITHM = "HS256"
EXPECTED_AUDIENCE = "authenticated"

def verify_jwt_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
) -> dict:
    """
    Dipendenza riutilizzabile per verificare il token JWT Bearer.
    
    Security Features (RFC 8725 + RFC 7519 Compliant):
    - Verifica presenza token Bearer
    - Valida signature JWT con algoritmo whitelist HS256 (RFC 8725 Sezione 3.1)
    - Verifica exp (scadenza) e iat (issued at) - claims obbligatori (RFC 8725)
    - Clock skew tolerance ±2 minuti per desincronizzazioni NTP (RFC 7519)
    - Valida audience claim per prevenire token reuse cross-service
    
    RFC 8725 Quote: "Libraries MUST enable the caller to specify a supported set of 
    algorithms and MUST NOT use any other algorithms"
    
    RFC 7519 Quote: "Implementers MAY provide for some small leeway, usually no more 
    than a few minutes, to account for clock skew"
    
    Args:
        credentials: Credenziali HTTP estratte dall'header Authorization
        
    Returns:
        dict: Payload decodificato del token JWT
        
    Raises:
        HTTPException: 401 se il token è mancante o non valido
    """
    # Verifica presenza del token Bearer
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # Decodifica e verifica il token JWT con RFC compliance
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],  # Whitelist esplicita: solo HS256 (RFC 8725)
            audience=EXPECTED_AUDIENCE,
            options={
                "require": ["exp", "iat"],  # Claims obbligatori (RFC 8725 Sezione 3.1)
                "leeway": 120  # ±2 minuti clock skew tolerance (RFC 7519)
            }
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        # Token scaduto - OAuth 2.0 error format (RFC 6749)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_grant",
                "error_description": "Token expired"
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidAudienceError as e:
        # Audience mismatch - security violation
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_grant",
                "error_description": "Invalid token audience"
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except InvalidTokenError as e:
        # Generic JWT error (signature invalid, malformed, etc.)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_grant",
                "error_description": f"Invalid token: {str(e)}"
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

# Alias per tipo payload
TokenPayload = dict

def _is_admin(payload: TokenPayload) -> bool:
    """
    Verifica che il payload JWT appartenga a un admin.
    
    CRITICAL: Questo check DEVE essere eseguito esplicitamente in ogni
    endpoint admin per prevenire privilege escalation.
    
    Args:
        payload: JWT payload decodificato
        
    Returns:
        bool: True se admin, False altrimenti
    """
    app_meta = payload.get("app_metadata", {})
    return app_meta.get("role") == "admin"


# ========== PATTERN CORRETTO: Admin-Only Endpoint ==========

@app.post("/api/v1/admin/debug/query")
def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)]
):
    """
    Endpoint admin con verifica role esplicita.
    
    Security Checklist:
    ✅ JWT verification (via Depends)
    ✅ Admin role check (esplicito)
    ✅ Input validation (Pydantic)
    ✅ Rate limiting (decorator o middleware)
    ✅ Audit logging (nel body)
    """
    # CRITICAL: Verifica role admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Forbidden: admin only"
        )
    
    # Audit logging (R-4.1-2)
    admin_id = payload.get("sub")
    logger.info({
        "event": "admin_debug_query",
        "admin_id": admin_id,
        "question_hash": hashlib.sha256(body.question.encode()).hexdigest()
    })
    
    # Logica endpoint...
    return {"status": "ok"}


# ========== ANTI-PATTERN: NON FARE COSÌ ==========

@app.post("/api/v1/admin/dangerous")
def dangerous_endpoint(
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)]
):
    """
    ❌ ANTI-PATTERN: Manca verifica role admin
    
    Vulnerabilità: Qualsiasi utente autenticato (anche student) 
    può accedere a questo endpoint.
    """
    # Logica admin senza check role → VULNERABILE
    return {"data": "sensitive_admin_data"}
```

**Testing Requirements (R-4.1-1)**:
- TC-050: Request senza JWT → 401
- TC-051: JWT student role → 403
- TC-052: JWT admin valido → 200
- TC-053: JWT manipulation attempt → 401
- BT-002/003/004: Unit tests auth flow

[Fonte: `docs/qa/assessments/4.1-test-design-20250930.md` L226-L241]

---

### JWT Clock Skew Configuration (RFC 7519 Compliance)

**Problema**: Server multi-istanza possono avere orologi desincronizzati (NTP drift, timezone issues) causando falsi positivi su validazione `exp`/`nbf`.

**Soluzione RFC 7519**: "Implementers MAY provide for some small leeway, usually no more than a few minutes, to account for clock skew"

**Implementazione Configurabile**:

```python
import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configurazione JWT con clock skew configurabile."""
    
    # JWT Configuration
    supabase_jwt_secret: str = Field(..., description="Secret key per JWT validation")
    jwt_issuer: str = Field(default="https://example.supabase.co/auth/v1")
    
    # Clock Skew Tolerance (RFC 7519)
    clock_skew_leeway_seconds: int = Field(
        default=120,  # ±2 minuti (RFC 7519: "usually no more than a few minutes")
        ge=0,
        le=300,  # Max 5 minuti (limite sicurezza)
        description="Tolleranza clock skew per validazione JWT exp/nbf in secondi"
    )
    
    # Access Token Duration
    temp_jwt_expires_minutes: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Durata access token in minuti"
    )

# Singleton pattern
settings = Settings()

# Usage in JWT verification
def verify_jwt_token_with_settings(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    config: Annotated[Settings, Depends(get_settings)]
) -> dict:
    """JWT verification con clock skew configurabile."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=config.jwt_issuer,
            options={
                "require": ["exp", "iat"],
                "leeway": config.clock_skew_leeway_seconds  # Configurabile via env
            }
        )
        return payload
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_grant",
                "error_description": f"Invalid token: {e}"
            }
        ) from e
```

**Environment Variables (.env)**:

```bash
# JWT Clock Skew Configuration
CLOCK_SKEW_LEEWAY_SECONDS=120  # Default: 2 minuti (RFC 7519 recommended)
SUPABASE_JWT_SECRET=your-secret-key-here
SUPABASE_JWT_ISSUER=https://yourproject.supabase.co/auth/v1
TEMP_JWT_EXPIRES_MINUTES=15
```

**Trade-offs**:
- **Leeway 0 sec**: Massima sicurezza, rischio falsi positivi da clock drift
- **Leeway 120 sec** (raccomandato): Bilanciamento sicurezza/usabilità, conforme RFC 7519
- **Leeway 300 sec**: Massima tolleranza, estende finestra attacco token scaduto di ~5 min

**Production Best Practices**:
- Monitorare eventi `jwt.ExpiredSignatureError` per calibrare leeway ottimale
- Sincronizzazione NTP server per ridurre necessità leeway elevato
- Audit log JWT errors per rilevare manipolazioni vs. clock issues
- Testing: validare JWT con timestamp mock ±leeway per verificare tolleranza

[Fonte: `materiale_ufficiale-story1.3.1.md` Sezione 1.3, RFC 7519, RFC 9068]

---

## 2. Validazione Dati con Pydantic (Input Sanitization)

### Pattern per Request/Response Models

**Problema**: Input non validati causano errori runtime e vulnerabilità security.

**Soluzione**: Pydantic models con validatori custom.

```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ========== Request Model: Story 4.1 Debug Query ==========

class DebugQueryRequest(BaseModel):
    """
    Modello validato per debug query admin.
    
    Validazioni:
    - question: non vuota, lunghezza controllata
    - Auto-sanitization: strip whitespace
    """
    question: str = Field(
        ...,  # Required
        min_length=3,
        max_length=500,
        description="Domanda di test per debug RAG",
        examples=["Cos'è la fisioterapia respiratoria?"]
    )
    
    @field_validator('question')
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        """Validator per sanitizzare input domanda."""
        if not v or not v.strip():
            raise ValueError('La domanda non può essere vuota')
        # Auto-sanitization: rimuove whitespace extra
        return v.strip()


# ========== Response Model: Story 4.1 Debug Query ==========

class ChunkMetadata(BaseModel):
    """Metadati chunk con validazione."""
    document_id: str
    document_name: str
    page_number: Optional[int] = None  # Nullable per fallback (R-4.1-10)
    chunking_strategy: str

class DebugChunk(BaseModel):
    """Singolo chunk con similarity score."""
    chunk_id: str
    content: str = Field(..., max_length=5000)  # Limite XSS prevention
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: ChunkMetadata

class DebugQueryResponse(BaseModel):
    """
    Response completa debug query con timing metrics.
    
    Validazioni:
    - similarity_score: 0.0-1.0 range
    - timing_metrics: non-negative
    - content: max length per XSS prevention
    """
    question: str
    answer: str = Field(..., max_length=10000)
    chunks: list[DebugChunk]
    retrieval_time_ms: float = Field(..., ge=0.0)
    generation_time_ms: float = Field(..., ge=0.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Cos'è la lombalgia?",
                "answer": "La lombalgia è...",
                "chunks": [
                    {
                        "chunk_id": "chunk_123",
                        "content": "Contenuto chunk...",
                        "similarity_score": 0.95,
                        "metadata": {
                            "document_id": "doc_456",
                            "document_name": "lombare_anatomia.pdf",
                            "page_number": 12,
                            "chunking_strategy": "recursive"
                        }
                    }
                ],
                "retrieval_time_ms": 150.5,
                "generation_time_ms": 2300.2
            }
        }


# ========== Utilizzo in Endpoint ==========

@app.post("/api/v1/admin/debug/query", response_model=DebugQueryResponse)
def admin_debug_query(
    body: DebugQueryRequest,  # Auto-validazione Pydantic
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)]
) -> DebugQueryResponse:
    """
    Endpoint con validazione completa input/output.
    
    Vantaggi Pydantic:
    - Validazione automatica (422 se invalid)
    - Type hints per IDE
    - OpenAPI docs auto-generated
    - Serializzazione JSON safe
    """
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # body.question è già validato e sanitizzato
    # FastAPI valida automaticamente il return vs DebugQueryResponse
    
    return DebugQueryResponse(
        question=body.question,
        answer="...",
        chunks=[],
        retrieval_time_ms=100.0,
        generation_time_ms=500.0
    )
```

**Vantaggi Pydantic**:
- Validazione automatica con errori dettagliati (422 Unprocessable Entity)
- Documentazione OpenAPI/Swagger generata automaticamente
- Type hints completi per IDE autocomplete
- Serializzazione/deserializzazione JSON safe
- Validatori custom per logica complessa

[Fonte: `FastAPI-docs.md` L103-L253; `docs/stories/4.1.admin-debug-view.md` L91-L92]

Vedi anche: [Addendum: Enterprise Standards (SLO/SLI, Threat Modeling, SBOM, API Governance)](addendum-enterprise-standards.md) per SLO/SLI, threat modeling e governance dei contratti OpenAPI.

---

## 3. Configuration Management con pydantic-settings

> **📚 Documentazione Completa**: Per guida dettagliata su Pydantic Settings, consultare:  
> **[Addendum: Pydantic Settings Configuration](addendum-pydantic-settings-configuration.md)**  
> 
> Include: BaseSettings pattern, validators (before/after/wrap/model), SecretStr, custom sources, environment-specific config, testing patterns.

### Pattern Base per FastAPI Integration

**Problema**: Secrets hardcoded, configurazioni non validate, difficoltà gestione multi-environment.

**Soluzione**: `pydantic-settings` con validazione, SecretStr e dependency injection.

```python
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurazione centralizzata FisioRAG.
    
    Caricamento automatico da:
    1. Variabili d'ambiente
    2. File .env
    3. Valori default
    """
    
    # ========== Database ==========
    supabase_url: str = Field(
        ...,
        description="URL progetto Supabase"
    )
    supabase_service_key: str = Field(
        ...,
        description="Service role key per Supabase"
    )
    
    # ========== JWT ==========
    supabase_jwt_secret: str = Field(
        ...,
        description="Secret key per verificare JWT Supabase"
    )
    jwt_issuer: str = Field(
        default="https://example.supabase.co/auth/v1",
        description="Issuer atteso per JWT"
    )
    temp_jwt_expires_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,  # Max 24 ore
        description="Durata JWT temporanei in minuti"
    )
    
    # ========== LLM ==========
    openai_api_key: str = Field(
        ...,
        description="Chiave API OpenAI"
    )
    openai_model: str = Field(
        default="gpt-4",
        description="Modello OpenAI da utilizzare"
    )
    
    # ========== Rate Limiting (R-4.1-3) ==========
    admin_debug_rate_limit_window_hours: int = Field(
        default=1,
        ge=1,
        description="Finestra rate limiting debug queries (ore)"
    )
    admin_debug_rate_limit_max_requests: int = Field(
        default=10,
        ge=1,
        description="Max debug queries per finestra temporale"
    )
    
    # ========== Applicazione ==========
    environment: str = Field(
        default="development",
        description="Ambiente: development, staging, production"
    )
    debug: bool = Field(
        default=False,
        description="Abilita modalità debug"
    )
    log_level: str = Field(
        default="INFO",
        description="Livello logging"
    )
    
    # ========== Validatori Custom ==========
    
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Verifica URL Supabase valido."""
        if not v.startswith('https://'):
            raise ValueError('SUPABASE_URL deve iniziare con https://')
        return v
    
    @field_validator('openai_api_key', 'supabase_service_key', 'supabase_jwt_secret')
    @classmethod
    def validate_secrets(cls, v: str) -> str:
        """Verifica secrets non vuoti."""
        if not v or len(v.strip()) < 10:
            raise ValueError('I segreti devono avere almeno 10 caratteri')
        return v
    
    # ========== Configurazione ==========
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


# ========== Singleton Pattern ==========

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Dependency per ottenere settings (singleton).
    
    Testable: override con Depends override per test.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# ========== Utilizzo in Endpoint ==========

@app.post("/api/v1/admin/debug/query")
def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]  # Inject settings
):
    """Endpoint con accesso sicuro a configurazione."""
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Accesso type-safe a configurazione
    openai_key = settings.openai_api_key  # Type: str (validated)
    rate_limit = settings.admin_debug_rate_limit_max_requests  # Type: int
    
    # Logica endpoint...
    return {"status": "ok"}
```

**File .env Esempio**:
```bash
# File: apps/api/.env

# Database
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here

# JWT
SUPABASE_JWT_SECRET=your-jwt-secret-here
SUPABASE_JWT_ISSUER=https://yourproject.supabase.co/auth/v1
TEMP_JWT_EXPIRES_MINUTES=15

# LLM
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4

# Rate Limiting (Story 4.1)
ADMIN_DEBUG_RATE_LIMIT_WINDOW_HOURS=1
ADMIN_DEBUG_RATE_LIMIT_MAX_REQUESTS=10

# App
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
```

**Vantaggi pydantic-settings**:
- Validazione automatica all'avvio (fail-fast)
- Type hints per autocompletamento IDE
- No secrets hardcoded
- Facile override per testing
- Documentazione self-describing

[Fonte: `FastAPI-docs.md` L256-L433; `docs/qa/assessments/4.1-risk-20250930.md` R-4.1-3]

---

## 4. Endpoint Asincrono per Performance (R-4.1-4)

### Pattern async/await per I/O Non-Bloccanti

**Problema**: Operazioni I/O sincrone bloccano thread; performance degradation sotto carico.

**Soluzione**: FastAPI async con `httpx.AsyncClient` e LangChain `.ainvoke()`.

```python
from typing import Annotated
import asyncio
import time
from fastapi import Depends, HTTPException
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable


# ========== Pattern 1: Chiamata HTTP Asincrona ==========

@app.get("/api/v1/external-data")
async def fetch_external_data(
    url: str,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> dict:
    """
    Chiamata HTTP asincrona con timeout.
    
    Vantaggi async:
    - Non blocca thread durante I/O
    - Migliaia di richieste concorrenti gestibili
    - Timeout configurabile
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"}
            )
            response.raise_for_status()
            data = response.json()
            
        return {"status": "success", "data": data}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="External API timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"External API error: {str(e)}")


# ========== Pattern 2: LLM Generation Asincrona (Story 4.1) ==========

@app.post("/api/v1/admin/debug/query", response_model=DebugQueryResponse)
async def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> DebugQueryResponse:
    """
    Debug query con LLM generation asincrona.
    
    Performance:
    - Retrieval e generation paralleli (se possibile)
    - Non blocca altri endpoint durante generation
    """
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    start_time = time.time()
    
    try:
        # Retrieval timing
        retrieval_start = time.time()
        chunks = await retrieve_chunks_async(body.question)  # Async retrieval
        retrieval_time_ms = (time.time() - retrieval_start) * 1000
        
        # Generation timing
        generation_start = time.time()
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Sei un assistente di debug RAG."),
            ("user", "{question}")
        ])
        
        chain: Runnable = prompt | llm
        
        # Invocazione asincrona LLM (non blocca)
        result = await chain.ainvoke({"question": body.question})
        generation_time_ms = (time.time() - generation_start) * 1000
        
        return DebugQueryResponse(
            question=body.question,
            answer=result.content,
            chunks=chunks,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Debug query failed: {str(e)}"
        ) from e


# ========== Pattern 3: Operazioni Parallele con asyncio.gather ==========

async def fetch_chunk_async(chunk_id: str) -> DebugChunk:
    """Recupera chunk dal DB (async)."""
    # In produzione: async query a Supabase
    await asyncio.sleep(0.05)  # Simula I/O
    return DebugChunk(
        chunk_id=chunk_id,
        content=f"Content {chunk_id}",
        similarity_score=0.9,
        metadata=ChunkMetadata(
            document_id="doc_1",
            document_name="test.pdf",
            page_number=1,
            chunking_strategy="recursive"
        )
    )


async def retrieve_chunks_async(question: str) -> list[DebugChunk]:
    """
    Recupera multiple chunks in parallelo.
    
    Performance: 10 chunks in ~50ms invece di ~500ms sequenziale.
    """
    chunk_ids = ["chunk_1", "chunk_2", "chunk_3"]  # Da vector search
    
    # Esegui tutte le fetch in parallelo
    chunks = await asyncio.gather(
        *[fetch_chunk_async(cid) for cid in chunk_ids]
    )
    
    return chunks
```

**Quando Usare async/await**:
- ✅ Chiamate database (driver asincroni)
- ✅ Chiamate HTTP API esterne
- ✅ Invocazioni LLM (`.ainvoke()`)
- ✅ Operazioni parallelizzabili
- ❌ CPU-bound operations
- ❌ Librerie sync-only

**Performance Impact (R-4.1-4)**:
- Async endpoint debug non blocca endpoint studenti
- Throughput 10x+ con carico concorrente
- Latency ridotta con operazioni parallele

[Fonte: `FastAPI-docs.md` L444-L656; `docs/qa/assessments/4.1-risk-20250930.md` R-4.1-4]

---

## 5. Error Handling Centralizzato (R-4.1-6)

### Pattern per Gestione Errori Robusta

**Problema**: Errori non gestiti causano crash o leak informazioni sensibili.

**Soluzione**: Exception handlers globali + logging strutturato.

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import traceback

logger = logging.getLogger("fisiorag")


# ========== Custom Exceptions ==========

class RateLimitExceeded(Exception):
    """Eccezione per rate limit superato."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


class ExternalAPIError(Exception):
    """Eccezione per errori API esterne (OpenAI, embedding)."""
    def __init__(self, service: str, detail: str):
        self.service = service
        self.detail = detail
        super().__init__(f"{service} API error: {detail}")


# ========== Global Exception Handlers ==========

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handler specifico per rate limiting (R-4.1-3)."""
    logger.warning({
        "event": "rate_limit_exceeded",
        "path": request.url.path,
        "retry_after": exc.retry_after
    })
    
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(exc.retry_after)},
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please retry later.",
            "retry_after_seconds": exc.retry_after
        }
    )


@app.exception_handler(ExternalAPIError)
async def external_api_handler(request: Request, exc: ExternalAPIError):
    """Handler per errori API esterne (R-4.1-6)."""
    logger.error({
        "event": "external_api_error",
        "service": exc.service,
        "detail": exc.detail,
        "path": request.url.path
    })
    
    # Messaggio user-friendly senza leak dettagli interni
    return JSONResponse(
        status_code=502,
        content={
            "error": "external_service_error",
            "message": f"Errore comunicazione con {exc.service}. Riprova più tardi.",
            "service": exc.service
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler per HTTPException (4xx/5xx)."""
    logger.warning({
        "event": "http_exception",
        "status_code": exc.status_code,
        "detail": exc.detail,
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler globale per eccezioni non gestite (R-4.1-6).
    
    Security:
    - No stack trace in response (solo in logs)
    - Messaggio generico per evitare info leak
    - Request ID per troubleshooting
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error({
        "event": "unhandled_exception",
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "path": request.url.path,
        "request_id": request_id,
        "traceback": traceback.format_exc()  # Solo in logs
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Si è verificato un errore interno. Contatta l'amministratore.",
            "request_id": request_id  # Per troubleshooting
        }
    )


# ========== Utilizzo in Endpoint ==========

@app.post("/api/v1/admin/debug/query")
async def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
):
    """Endpoint con error handling robusto."""
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Rate limiting check
    if not check_rate_limit(payload.get("sub")):
        raise RateLimitExceeded(retry_after=3600)
    
    try:
        # LLM generation con error handling
        result = await generate_with_llm(body.question, settings)
        return result
    except httpx.TimeoutException:
        # Timeout OpenAI API
        raise ExternalAPIError(
            service="OpenAI",
            detail="Request timeout after 30s"
        )
    except Exception as e:
        # Catch-all per errori imprevisti
        logger.error(f"Unexpected error in debug query: {e}", exc_info=True)
        raise  # Propagato a global handler
```

**Error Handling Checklist**:
- ✅ Custom exceptions per scenari specifici
- ✅ Global handlers per catch-all
- ✅ Logging strutturato con context
- ✅ Messaggi user-friendly (no stack trace in response)
- ✅ Request ID per troubleshooting
- ✅ Status code appropriati (4xx client, 5xx server)

[Fonte: `FastAPI-docs.md` L694-L713; `docs/qa/assessments/4.1-test-design-20250930.md` TC-091-093]

---

## 6. Logging Strutturato per Audit (R-4.1-2)

### Pattern per Audit Trail e Troubleshooting

**Problema**: Logs non strutturati difficili da analizzare; rischio PII exposure.

**Soluzione**: JSON logging con sanitization automatica.

```python
import logging
import json
import hashlib
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Formatter per logging strutturato in JSON.
    
    Features:
    - Timestamp ISO 8601
    - Structured data (easy parsing)
    - Extra fields support
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Aggiungi dati extra se presenti
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'event'):
            log_data['event'] = record.event
            
        # Aggiungi exception info se presente
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


# ========== Setup Logging ==========

logger = logging.getLogger("fisiorag")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ========== Audit Logging per Story 4.1 (R-4.1-2) ==========

def log_admin_action(
    admin_id: str,
    action: str,
    resource: str,
    details: dict[str, Any] = None,
    sanitize_pii: bool = True
):
    """
    Log azione admin con sanitization PII automatica.
    
    Security (R-4.1-2):
    - No PII in logs (hash question, no chunk content)
    - Admin ID per accountability
    - Timestamp per audit trail
    - Action type per filtering
    
    Args:
        admin_id: ID admin (da JWT sub)
        action: Tipo azione (e.g., "debug_query")
        resource: Risorsa coinvolta (e.g., "knowledge_base")
        details: Metadati extra (sanitizzati se necessario)
        sanitize_pii: Se True, hash automatico campi sensibili
    """
    log_entry = {
        "event": "admin_action",
        "admin_id": admin_id,
        "action": action,
        "resource": resource,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if details:
        # Sanitize PII se richiesto
        if sanitize_pii:
            sanitized_details = {}
            for key, value in details.items():
                if key in ["question", "content", "message"]:
                    # Hash campi con potenziale PII
                    sanitized_details[f"{key}_hash"] = hashlib.sha256(
                        str(value).encode()
                    ).hexdigest()[:16]
                else:
                    sanitized_details[key] = value
            log_entry["details"] = sanitized_details
        else:
            log_entry["details"] = details
    
    logger.info(json.dumps(log_entry, ensure_ascii=False))


# ========== Request ID Middleware ==========

import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Aggiunge request_id unico per tracciamento.
    
    Troubleshooting:
    - Correla logs multiple dello stesso request
    - Include in error response per user report
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log inizio request
    logger.info({
        "event": "request_start",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None
    })
    
    response = await call_next(request)
    
    # Aggiungi request_id in response header
    response.headers["X-Request-ID"] = request_id
    
    # Log fine request
    logger.info({
        "event": "request_end",
        "request_id": request_id,
        "status_code": response.status_code
    })
    
    return response


# ========== Utilizzo in Endpoint Story 4.1 ==========

@app.post("/api/v1/admin/debug/query")
async def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)]
):
    """Endpoint con audit logging completo."""
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    admin_id = payload.get("sub")
    
    # Audit log (R-4.1-2): sanitizza automaticamente PII
    log_admin_action(
        admin_id=admin_id,
        action="debug_query",
        resource="knowledge_base",
        details={
            "question": body.question,  # Verrà hashato
            "chunk_count": 5,  # Non sensibile
            "retrieval_time_ms": 150  # Non sensibile
        },
        sanitize_pii=True  # Abilita sanitization
    )
    
    # Logica endpoint...
    return {"status": "ok"}
```

**Audit Logging Output Esempio**:
```json
{
  "event": "admin_action",
  "admin_id": "admin_123",
  "action": "debug_query",
  "resource": "knowledge_base",
  "timestamp": "2025-09-30T10:30:00Z",
  "details": {
    "question_hash": "a3f8d9e2c1b4567",
    "chunk_count": 5,
    "retrieval_time_ms": 150
  }
}
```

**Testing Requirements (R-4.1-2)**:
- TC-082: Verifica presenza audit log con admin_id
- TC-083: Verifica nessun PII in logs (question hashato)
- BT-050/051: Unit tests audit logging

[Fonte: `FastAPI-docs.md` L661-L731; `docs/qa/assessments/4.1-test-design-20250930.md` TC-082-083]

---

## 7. Rate Limiting Pattern (R-4.1-3)

### Implementazione Rate Limiting per Endpoint Admin

**Problema**: Admin può eseguire debug queries illimitate, generando costi API elevati.

**Soluzione**: Decorator rate limiting con storage in-memory (MVP) o Redis (production).

```python
from datetime import datetime, timedelta
from typing import Callable
from functools import wraps
import asyncio

# ========== In-Memory Rate Limiter (MVP) ==========

class RateLimiter:
    """
    Rate limiter in-memory per endpoint admin.
    
    Configuration (R-4.1-3):
    - 10 requests per admin per ora (configurable via Settings)
    - Scope isolato per tipo endpoint
    - Reset automatico dopo window
    """
    
    def __init__(self):
        # Structure: {scope: {user_id: [(timestamp, count)]}}
        self._requests: dict[str, dict[str, list[tuple[datetime, int]]]] = {}
        self._lock = asyncio.Lock()
    
    async def check_limit(
        self,
        user_id: str,
        scope: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Verifica rate limit per user_id in scope.
        
        Args:
            user_id: Identificatore utente (admin_id da JWT)
            scope: Scope rate limit (e.g., "admin_debug")
            max_requests: Max richieste nella finestra
            window_seconds: Durata finestra in secondi
            
        Returns:
            tuple[bool, int]: (allowed, retry_after_seconds)
        """
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            
            # Init scope e user se non esistono
            if scope not in self._requests:
                self._requests[scope] = {}
            if user_id not in self._requests[scope]:
                self._requests[scope][user_id] = []
            
            # Cleanup richieste fuori finestra
            user_requests = self._requests[scope][user_id]
            user_requests[:] = [
                (ts, count) for ts, count in user_requests 
                if ts > window_start
            ]
            
            # Conta richieste nella finestra
            total_requests = sum(count for _, count in user_requests)
            
            if total_requests >= max_requests:
                # Limit exceeded
                oldest_request = user_requests[0][0]
                retry_after = int((oldest_request + timedelta(seconds=window_seconds) - now).total_seconds())
                return False, max(retry_after, 1)
            
            # Aggiungi richiesta corrente
            user_requests.append((now, 1))
            return True, 0


# Global rate limiter instance
rate_limiter = RateLimiter()


# ========== Decorator per Rate Limiting ==========

def rate_limit(
    scope: str,
    max_requests: int = 10,
    window_hours: int = 1
):
    """
    Decorator per applicare rate limiting a endpoint.
    
    Usage:
        @rate_limit(scope="admin_debug", max_requests=10, window_hours=1)
        @app.post("/api/v1/admin/debug/query")
        async def debug_endpoint(...):
            ...
    
    Args:
        scope: Identificatore scope rate limit
        max_requests: Max richieste nella finestra
        window_hours: Durata finestra in ore
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Estrai payload JWT da kwargs (dependency injection)
            payload = kwargs.get("payload")
            if not payload:
                raise HTTPException(
                    status_code=500,
                    detail="Rate limiting requires authenticated user"
                )
            
            user_id = payload.get("sub")
            window_seconds = window_hours * 3600
            
            # Check rate limit
            allowed, retry_after = await rate_limiter.check_limit(
                user_id=user_id,
                scope=scope,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            if not allowed:
                logger.warning({
                    "event": "rate_limit_exceeded",
                    "user_id": user_id,
                    "scope": scope,
                    "retry_after": retry_after
                })
                raise RateLimitExceeded(retry_after=retry_after)
            
            # Proceed con endpoint
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ========== Utilizzo in Endpoint Story 4.1 ==========

@app.post("/api/v1/admin/debug/query", response_model=DebugQueryResponse)
@rate_limit(scope="admin_debug", max_requests=10, window_hours=1)  # R-4.1-3
async def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> DebugQueryResponse:
    """
    Endpoint debug con rate limiting.
    
    Rate Limit (R-4.1-3):
    - 10 queries per admin per ora
    - Scope isolato (non impatta altri endpoint)
    - 429 con retry-after se superato
    """
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Logica endpoint...
    return DebugQueryResponse(...)


# ========== Alternative: Dependency-Based Rate Limiting ==========

async def check_admin_debug_rate_limit(
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
):
    """
    Dependency per rate limiting admin debug.
    
    Vantaggi:
    - Testable con dependency override
    - Config da Settings
    - Reusable across endpoints
    """
    user_id = payload.get("sub")
    
    allowed, retry_after = await rate_limiter.check_limit(
        user_id=user_id,
        scope="admin_debug",
        max_requests=settings.admin_debug_rate_limit_max_requests,
        window_seconds=settings.admin_debug_rate_limit_window_hours * 3600
    )
    
    if not allowed:
        raise RateLimitExceeded(retry_after=retry_after)


@app.post("/api/v1/admin/debug/query")
async def admin_debug_query_v2(
    body: DebugQueryRequest,
    payload: Annotated[TokenPayload, Depends(verify_jwt_token)],
    _: Annotated[None, Depends(check_admin_debug_rate_limit)]  # Rate limit check
):
    """Endpoint con rate limiting via dependency."""
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Logica endpoint...
    return {"status": "ok"}
```

**Testing Requirements (R-4.1-3)**:
- TC-080: 11ª query in 1 ora → 429
- TC-081: Scope isolato (non impatta endpoint studenti)
- BT-010: Unit test rate limiting
- BT-011: Reset dopo finestra temporale

**Production Considerations**:
- In-memory OK per MVP (single instance)
- Production: usare Redis per multi-instance deployment
- Monitoring: log rate limit events per analytics

[Fonte: `docs/qa/assessments/4.1-risk-20250930.md` R-4.1-3; `docs/qa/assessments/4.1-test-design-20250930.md` TC-080-081]

---

## 8. Testing Patterns

### Dependency Override per Testing

```python
import pytest
from fastapi.testclient import TestClient


# ========== Mock Settings per Testing ==========

def get_test_settings() -> Settings:
    """Mock settings per test environment."""
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_service_key="test-key",
        supabase_jwt_secret="test-secret",
        openai_api_key="test-openai-key",
        environment="test",
        debug=True
    )


# ========== Mock JWT Verification per Testing ==========

def mock_verify_jwt_admin(role: str = "admin") -> dict:
    """Mock JWT payload per test."""
    return {
        "sub": "test_admin_123",
        "app_metadata": {"role": role},
        "exp": 9999999999,
        "iat": 1000000000
    }


# ========== Setup Test Client con Override ==========

@pytest.fixture
def client():
    """Test client con dependency override."""
    from main import app
    
    # Override dependencies
    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[verify_jwt_token] = lambda: mock_verify_jwt_admin("admin")
    
    yield TestClient(app)
    
    # Cleanup
    app.dependency_overrides.clear()


# ========== Test Caso: Auth Admin (TC-052) ==========

def test_admin_debug_query_with_valid_admin_jwt(client):
    """
    TC-052: JWT admin valido → 200 OK.
    
    Coverage:
    - Auth check passed
    - Admin role verified
    - Endpoint logic executed
    """
    response = client.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "chunks" in data


# ========== Test Caso: Auth Bypass (TC-051) ==========

def test_admin_debug_query_with_student_jwt_returns_403(client):
    """
    TC-051: JWT student role → 403 Forbidden.
    
    Coverage:
    - Auth check passed (JWT valid)
    - Admin role check FAILED
    - 403 returned
    """
    # Override con JWT student
    from main import app
    app.dependency_overrides[verify_jwt_token] = lambda: mock_verify_jwt_admin("student")
    
    response = client.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


# ========== Test Caso: Rate Limiting (TC-080) ==========

@pytest.mark.asyncio
async def test_rate_limiting_11th_request_returns_429(client):
    """
    TC-080: 11ª query in 1 ora → 429 Too Many Requests.
    
    Coverage:
    - Rate limiter enforced
    - 10 requests allowed
    - 11th request blocked
    - Retry-after header present
    """
    # Execute 10 requests (allowed)
    for i in range(10):
        response = client.post(
            "/api/v1/admin/debug/query",
            json={"question": f"Test query {i}"}
        )
        assert response.status_code == 200
    
    # 11th request (blocked)
    response = client.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query 11"}
    )
    
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0
```

---

## Checklist Implementazione Story 4.1

Utilizzare questo checklist per implementazione completa e sicura:

### Security (CRITICAL)
- [ ] JWT verification con `verify_jwt_token` dependency
- [ ] Admin role check esplicito con `_is_admin()`
- [ ] Rate limiting 10 queries/hour per admin
- [ ] Audit logging con PII sanitization
- [ ] Input validation Pydantic su `DebugQueryRequest`
- [ ] Output validation Pydantic su `DebugQueryResponse`
- [ ] Error handling con no stack trace in response
- [ ] HTTPS only (configurazione deployment)

### Performance
- [ ] Async endpoint con `async def`
- [ ] LLM invocation con `.ainvoke()`
- [ ] Parallel chunk retrieval con `asyncio.gather`
- [ ] Timing metrics accurati (`time.perf_counter()`)
- [ ] No performance impact endpoint studenti (verificare con load test)

### Error Handling
- [ ] Custom exceptions per scenari specifici
- [ ] Global exception handler configurato
- [ ] HTTPException con status code appropriati
- [ ] Logging strutturato per troubleshooting
- [ ] Request ID in response per support

### Testing
- [ ] Unit tests auth (BT-002/003/004): 100% coverage
- [ ] Unit tests rate limiting (BT-010/011)
- [ ] Integration tests end-to-end (BI-001/002)
- [ ] E2E tests Playwright (E2E-001/002/003)
- [ ] Security tests (auth bypass, XSS)

### Documentation
- [ ] Endpoint docstring completo
- [ ] OpenAPI schema auto-generated verificato
- [ ] Architecture docs aggiornati
- [ ] Risk mitigation verificata

---

## References

- **Story**: `docs/stories/4.1.admin-debug-view.md`
- **Risk Profile**: `docs/qa/assessments/4.1-risk-20250930.md`
- **Test Design**: `docs/qa/assessments/4.1-test-design-20250930.md`
- **FastAPI Official Docs**: FastAPI-docs.md (material source)
- **Existing Codebase**: `apps/api/api/main.py` (pattern reference)

---

**Revision History**:

| Date       | Version | Changes                                                                                      |
|------------|---------|----------------------------------------------------------------------------------------------|
| 2025-09-30 | 1.0     | Initial version - FastAPI best practices                                                     |
| 2025-10-08 | 1.1     | JWT validation RFC compliance: algoritmo whitelist, clock skew tolerance configurabile, OAuth 2.0 error codes standard (RFC 8725/7519/6749). Pattern riutilizzabile Story 1.3.1. |
