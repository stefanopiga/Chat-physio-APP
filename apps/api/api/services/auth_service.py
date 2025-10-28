"""
Authentication service - Business logic per JWT e token management.

Story: 1.3, 1.3.1
"""
import jwt
from datetime import datetime, timedelta, timezone
from ..utils.security import generate_student_token, generate_refresh_token, generate_access_code


# Re-export utilities per backwards compatibility
__all__ = ["generate_student_token", "generate_refresh_token", "generate_access_code", "generate_temp_jwt"]


def generate_temp_jwt(
    subject: str,
    session_id: str,
    jwt_secret: str,
    jwt_issuer: str,
    expires_minutes: int = 15
) -> str:
    """
    Genera JWT temporaneo.
    
    Args:
        subject: User ID per sub claim
        session_id: Session identifier
        jwt_secret: Signing secret
        jwt_issuer: Issuer claim
        expires_minutes: Token duration
        
    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    payload = {
        "iss": jwt_issuer,
        "aud": "authenticated",
        "sub": subject,
        "role": "authenticated",
        "session_id": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")
