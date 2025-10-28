"""
Student Token schemas - Request/Response models per student token management.

Story: 1.3.1
"""
from pydantic import BaseModel, Field


class CreateStudentTokenRequest(BaseModel):
    """Request per creare student token."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class CreateStudentTokenResponse(BaseModel):
    """Response per student token creato."""
    id: str
    token: str
    first_name: str
    last_name: str
    expires_at: str


class StudentTokenResponse(BaseModel):
    """Response completa per student token con metadati."""
    id: str
    first_name: str
    last_name: str
    token: str
    is_active: bool
    expires_at: str
    created_at: str
    updated_at: str
