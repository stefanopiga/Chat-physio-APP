"""
FastAPI dependencies per dependency injection.

Fornisce:
- JWT verification
- Settings access
- Admin role check
- Database connections
"""
import inspect
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError
import asyncpg

from .config import Settings, get_settings
from .database import get_db_connection

# Type aliases
TokenPayload = dict

# Security
security = HTTPBearer(auto_error=False)


def verify_jwt_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> dict:
    """
    Verifica JWT Bearer token (RFC 8725 compliant).
    
    Args:
        credentials: HTTP Authorization header
        settings: Application settings
        
    Returns:
        JWT payload decodificato
        
    Raises:
        HTTPException: 401 se token mancante o invalido
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={
                "require": ["exp", "iat"],
                "leeway": settings.clock_skew_leeway_seconds
            }
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_grant",
                "error_description": "Token expired"
            },
            headers={"WWW-Authenticate": "Bearer"}
        ) from e
    except jwt.InvalidAudienceError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_grant",
                "error_description": "Invalid token audience"
            },
            headers={"WWW-Authenticate": "Bearer"}
        ) from e
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_grant",
                "error_description": f"Invalid token: {str(e)}"
            },
            headers={"WWW-Authenticate": "Bearer"}
        ) from e


def _is_admin(payload: dict) -> bool:
    """
    Verifica role admin da JWT payload.
    
    Args:
        payload: JWT payload decodificato
        
    Returns:
        True se admin, False altrimenti
    """
    if payload.get("role") == "admin":
        return True
    app_meta = payload.get("app_metadata") or {}
    return app_meta.get("role") == "admin"


def _get_supabase_client(
    settings: Annotated[Settings, Depends(get_settings)]
):
    """
    Dependency per ottenere Supabase client.
    
    Returns:
        Supabase client instance
    """
    from supabase import create_client, Client
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _verify_jwt_token_runtime(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
):
    """
    Bridge runtime per consentire monkeypatch nei test.
    
    Se `verify_jwt_token` è monkeypatchato a callable senza argomenti,
    invocalo senza passare `credentials`. Altrimenti passa `credentials`.
    """
    from . import dependencies
    func = getattr(dependencies, "verify_jwt_token", None)
    if func is None:
        raise HTTPException(status_code=500, detail="auth_dependency_missing")
    try:
        sig = inspect.signature(func)
        if len(sig.parameters) == 0:
            return func()
        # Se ha parametri, dobbiamo passare anche settings
        from .config import get_settings
        settings = get_settings()
        return func(credentials, settings)
    except TypeError:
        return func()


def _auth_bridge(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
):
    """
    Wrapper che richiama il bridge runtime.
    
    Consente ai test di monkeypatchare `api.dependencies._auth_bridge` e influenzare
    le dipendenze dei route anche se il callable è stato catturato alla definizione.
    """
    return _verify_jwt_token_runtime(credentials)
