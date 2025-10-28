"""
Test suite per Auth Service.

Coverage:
- generate_student_token()
- generate_refresh_token()
- generate_access_code()
- generate_temp_jwt()
"""
import pytest
import secrets
import string
from datetime import datetime, timezone, timedelta


def test_generate_student_token_uniqueness():
    """Test: student token generation produces unique tokens (256-bit entropy)."""
    from api.services.auth_service import generate_student_token
    
    tokens = set()
    
    for _ in range(1000):
        token = generate_student_token()
        tokens.add(token)
    
    assert len(tokens) == 1000
    
    for token in tokens:
        assert len(token) >= 32


def test_generate_refresh_token_uniqueness():
    """Test: refresh token generation produces unique tokens (512-bit entropy)."""
    from api.services.auth_service import generate_refresh_token
    
    tokens = set()
    
    for _ in range(1000):
        token = generate_refresh_token()
        tokens.add(token)
    
    assert len(tokens) == 1000
    
    for token in tokens:
        assert len(token) >= 64


def test_generate_access_code_format():
    """Test: access code generation produces alphanumeric codes."""
    from api.services.auth_service import generate_access_code
    
    codes = set()
    
    for _ in range(100):
        code = generate_access_code(length=8)
        codes.add(code)
        
        # Verifica formato: uppercase + digits
        assert len(code) == 8
        assert code.isupper()
        assert all(c in string.ascii_uppercase + string.digits for c in code)
    
    # Verifica unicità
    assert len(codes) > 95  # Almeno 95% unici


def test_generate_temp_jwt_structure():
    """Test: JWT temporaneo contiene claims corretti."""
    from api.services.auth_service import generate_temp_jwt
    import jwt
    
    jwt_secret = "test_secret_key_for_unit_testing"
    jwt_issuer = "test_issuer"
    
    token = generate_temp_jwt(
        subject="user_123",
        session_id="session_abc",
        expires_minutes=15,
        jwt_secret=jwt_secret,
        jwt_issuer=jwt_issuer
    )
    
    # Decode senza verifica exp per test (Story 5.4.1 Phase 5: fix audience)
    decoded = jwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",  # Must match payload["aud"]
        options={"verify_exp": False}
    )
    
    # Verifica claims
    assert decoded["sub"] == "user_123"
    assert decoded["session_id"] == "session_abc"
    assert decoded["iss"] == jwt_issuer
    assert decoded["aud"] == "authenticated"
    assert decoded["role"] == "authenticated"
    assert "iat" in decoded
    assert "exp" in decoded
    
    # Verifica durata
    exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
    duration_minutes = (exp_time - iat_time).total_seconds() / 60
    assert 14.9 <= duration_minutes <= 15.1


def test_generate_temp_jwt_different_subjects_unique():
    """Test: JWT con subject diversi producono token diversi."""
    from api.services.auth_service import generate_temp_jwt
    
    jwt_secret = "test_secret_key"
    jwt_issuer = "test_issuer"
    
    token1 = generate_temp_jwt("user_1", "session_1", jwt_secret, jwt_issuer, expires_minutes=15)
    token2 = generate_temp_jwt("user_2", "session_2", jwt_secret, jwt_issuer, expires_minutes=15)
    
    assert token1 != token2

