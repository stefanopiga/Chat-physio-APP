"""
Security utilities per token generation e hashing.
"""
import secrets
import string
import hashlib


def generate_student_token() -> str:
    """Genera student token sicuro 32 char (256-bit entropy)."""
    return secrets.token_urlsafe(32)


def generate_refresh_token() -> str:
    """Genera refresh token sicuro 64 char (512-bit entropy)."""
    return secrets.token_urlsafe(64)


def generate_access_code(length: int = 8) -> str:
    """Genera access code alfanumerico."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_pii(text: str) -> str:
    """
    Hash PII per audit logging.
    
    Args:
        text: Testo da hashare
        
    Returns:
        SHA256 hash (primi 16 caratteri)
    """
    return hashlib.sha256(text.encode()).hexdigest()[:16]
