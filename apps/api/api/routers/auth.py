"""
Authentication router - Gestisce login, token exchange, refresh.

Story: 1.3, 1.3.1
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..schemas.auth import (
    GenerateCodeRequest,
    GeneratedCodeResponse,
    ExchangeCodeRequest,
    ExchangeCodeResponse,
    RefreshTokenResponse,
)
from ..services.auth_service import generate_temp_jwt, generate_refresh_token
from ..services.rate_limit_service import rate_limit_service
from ..dependencies import verify_jwt_token, _is_admin, _get_supabase_client
from ..config import Settings, get_settings
from ..utils.security import generate_access_code

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
logger = logging.getLogger("api")

# Store in-memory per access codes (Story 1.3 - legacy, mono-uso)
access_codes_store: Dict[str, Dict[str, Any]] = {}


@router.post("/admin/access-codes/generate", response_model=GeneratedCodeResponse)
def generate_access_code_admin(
    body: GenerateCodeRequest,
    payload: Annotated[dict, Depends(verify_jwt_token)],
):
    """
    Genera access code temporaneo admin (Story 1.3 - legacy).
    
    - Code mono-uso con durata configurabile
    - Stored in-memory (non persistente)
    - Admin-only access (Story 1.3)
    """
    if not _is_admin(payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")

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


@router.post("/exchange-code", response_model=ExchangeCodeResponse)
def exchange_code(
    body: ExchangeCodeRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)]
):
    """
    Exchange access code o student token per JWT (Story 1.3 + 1.3.1).
    
    Supports:
    - Legacy access codes (15 min, single-use, in-memory)
    - Student tokens (persistent, refresh token pattern, DB)
    
    Rate limiting: 10 req/min per IP
    """
    client_ip = request.client.host if request.client else None
    
    # Enforce rate limit per IP
    rate_limit_service.enforce_rate_limit(
        key=client_ip,
        scope="exchange_code",
        window_seconds=settings.exchange_code_rate_limit_window_sec,
        max_requests=settings.exchange_code_rate_limit_max_requests
    )

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
        if record.get("usage_count", 0) > 0:
            logger.info({
                "event": "exchange_code_result",
                "result": "code_already_used",
                "client_ip": client_ip,
                "code_id": record.get("id"),
            })
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="code_already_used")

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
        token = generate_temp_jwt(
            subject=subject,
            session_id=session_id,
            jwt_secret=settings.supabase_jwt_secret,
            jwt_issuer=settings.jwt_issuer,
            expires_minutes=settings.temp_jwt_expires_minutes
        )

        logger.info({
            "event": "exchange_code_result",
            "result": "success",
            "type": "access_code",
            "client_ip": client_ip,
            "code_id": record.get("id"),
            "session_id": session_id,
            "expires_in_sec": settings.temp_jwt_expires_minutes * 60,
        })

        return ExchangeCodeResponse(
            token=token,
            token_type="bearer",
            expires_in=settings.temp_jwt_expires_minutes * 60,
        )
    
    # 2. Cerca in student_tokens (DB) - Refresh Token Pattern (Story 1.3.1)
    try:
        supabase = _get_supabase_client(settings)
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
                jwt_secret=settings.supabase_jwt_secret,
                jwt_issuer=settings.jwt_issuer,
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


@router.post("/refresh-token", response_model=RefreshTokenResponse)
def refresh_access_token(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)]
):
    """
    Rinnova access token usando refresh token (Story 1.3.1).
    
    - Legge refresh token da cookie HttpOnly
    - Verifica validità in DB (non revocato, non scaduto)
    - Genera nuovo access token JWT 15 min
    - Aggiorna last_used_at per audit
    - Rate limiting 60 req/ora (OWASP)
    """
    client_ip = request.client.host if request.client else None
    
    # Rate limiting
    rate_limit_service.enforce_rate_limit(
        key=client_ip,
        scope="refresh_token",
        window_seconds=settings.refresh_token_rate_limit_window_sec,
        max_requests=settings.refresh_token_rate_limit_max_requests
    )
    
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
        supabase = _get_supabase_client(settings)
        
        # Verifica refresh token in DB con join a student_tokens
        # CRITICAL: Non usare .single() perché solleva exception se 0 rows
        result = supabase.table("refresh_tokens")\
            .select("*, student_tokens!inner(*)")\
            .eq("token", refresh_token)\
            .eq("is_revoked", False)\
            .execute()
        
        # Handle caso "token not found" o "is_revoked=True" (filtrato da query)
        if not result.data or len(result.data) == 0:
            logger.warning({
                "event": "refresh_token_invalid",
                "reason": "not_found_or_revoked",
                "client_ip": client_ip,
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Ottieni primo (e unico) record dalla query
        refresh_record = result.data[0]
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
        if not student_token.get("is_active", False):
            logger.warning({
                "event": "refresh_token_rejected",
                "reason": "student_token_revoked",
                "student_token_id": student_token["id"],
                "client_ip": client_ip,
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Student token has been revoked"
            )
        
        # Genera nuovo Access Token
        session_id = str(uuid4())
        subject = f"student:{student_token['id']}"
        access_token = generate_temp_jwt(
            subject=subject,
            session_id=session_id,
            jwt_secret=settings.supabase_jwt_secret,
            jwt_issuer=settings.jwt_issuer,
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
        # Re-raise HTTP exceptions (401, 410, etc.) con status code corretto
        raise
    except Exception as exc:
        # Log errore ma non esporre dettagli in produzione
        logger.error({
            "event": "refresh_token_failed",
            "error": str(exc),
            "client_ip": client_ip,
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
