"""
Authentication schemas - Request/Response models per autenticazione.

Story: 1.3, 1.3.1
"""
from typing import Optional
from pydantic import BaseModel, Field


class GenerateCodeRequest(BaseModel):
    """Request per generare access code admin."""
    expires_in_minutes: Optional[int] = Field(
        default=None,
        description="Durata code in minuti (opzionale)"
    )


class GeneratedCodeResponse(BaseModel):
    """Response per access code generato."""
    id: str
    code: str
    expires_at: Optional[str] = None


class ExchangeCodeRequest(BaseModel):
    """Request per exchange access code o student token."""
    access_code: str = Field(..., description="Access code o student token")


class ExchangeCodeResponse(BaseModel):
    """Response JWT per access code exchange."""
    token: str
    token_type: str
    expires_in: int


class RefreshTokenResponse(BaseModel):
    """Response per refresh token endpoint."""
    access_token: str
    token_type: str
    expires_in: int
