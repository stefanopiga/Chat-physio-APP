#!/usr/bin/env python3
"""Generate fresh JWT tokens for performance testing."""
import os
import jwt
from datetime import datetime, timedelta, timezone

def main():
    """Generate tokens for admin and student users."""
    # JWT configuration from environment
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if jwt_secret:
        jwt_secret = jwt_secret.strip()
    if not jwt_secret:
        print("ERROR: SUPABASE_JWT_SECRET not set in environment")
        print("Load .env file first: Get-Content .env | ForEach-Object { if ($_ -match '^(.+?)=(.+)$') { $env:($matches[1])=$matches[2] } }")
        return 1
    
    jwt_issuer = os.getenv("SUPABASE_JWT_ISSUER").strip()
    
    # Admin credentials
    admin_email = "quando vedi l'errore nel test, apri questo file e aggiungi la mail di un admin registrato nel DB"
    admin_uid = "aede4bdb-9c4c-4b5c-abdc-8a07f1c18356"
    
    # Student credentials
    student_email = "student_perf@test.com"
    student_uid = "76a41b8c-7646-4c53-8d4b-48e4fbe70d38"
    
    now = datetime.now(timezone.utc)
    exp_time = now + timedelta(hours=2)
    
    # Admin token payload
    admin_payload = {
        "iss": jwt_issuer,
        "sub": admin_uid,
        "aud": "authenticated",
        "exp": int(exp_time.timestamp()),
        "iat": int(now.timestamp()),
        "email": admin_email,
        "phone": "",
        "app_metadata": {
            "provider": "email",
            "providers": ["email"],
            "role": "admin"
        },
        "user_metadata": {
            "email_verified": True
        },
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": "perf-test-admin-session",
        "is_anonymous": False
    }
    
    # Student token payload  
    student_payload = {
        "iss": jwt_issuer,
        "sub": student_uid,
        "aud": "authenticated",
        "exp": int(exp_time.timestamp()),
        "iat": int(now.timestamp()),
        "email": student_email,
        "phone": "",
        "app_metadata": {
            "provider": "email",
            "providers": ["email"],
            "role": "student"
        },
        "user_metadata": {
            "email_verified": True
        },
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": "perf-test-student-session",
        "is_anonymous": False
    }
    
    admin_token = jwt.encode(admin_payload, jwt_secret, algorithm="HS256")
    student_token = jwt.encode(student_payload, jwt_secret, algorithm="HS256")
    
    print("Generated fresh tokens (valid for 2 hours):\n")
    print(f"ADMIN_BEARER=Bearer {admin_token}")
    print(f"CHAT_BEARER=Bearer {student_token}")
    print("\nUpdate scripts/perf/.env.staging.local with these tokens")
    return 0

if __name__ == "__main__":
    exit(main())
