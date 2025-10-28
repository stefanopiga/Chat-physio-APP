"""
Student Token router - CRUD management per student tokens.

Story: 1.3.1
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.student_tokens import (
    CreateStudentTokenRequest,
    CreateStudentTokenResponse,
    StudentTokenResponse,
)
from ..services.auth_service import generate_student_token
from ..services.rate_limit_service import rate_limit_service
from ..dependencies import verify_jwt_token, _is_admin, _get_supabase_client
from ..config import Settings, get_settings

router = APIRouter(prefix="/api/v1/admin/student-tokens", tags=["Student Tokens"])
logger = logging.getLogger("api")


@router.post("", response_model=CreateStudentTokenResponse, status_code=201)
def create_student_token(
    body: CreateStudentTokenRequest,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
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
    
    # Rate limiting
    rate_limit_service.enforce_rate_limit(
        key=admin_user_id,
        scope="admin_create_token",
        window_seconds=settings.admin_create_token_rate_limit_window_sec,
        max_requests=settings.admin_create_token_rate_limit_max_requests
    )
    
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
        supabase = _get_supabase_client(settings)
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


@router.get("", response_model=list[StudentTokenResponse])
def list_student_tokens(
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)],
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
        supabase = _get_supabase_client(settings)
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


@router.delete("/{token_id}", status_code=204)
def delete_student_token(
    token_id: str,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
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
        supabase = _get_supabase_client(settings)
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
