#!/usr/bin/env python3
"""
Generate admin JWT token for FisioRAG API.

Usage:
    python generate_jwt.py [--email EMAIL] [--expires-days DAYS]

Environment variables required:
    SUPABASE_JWT_SECRET - JWT signing secret from Supabase project settings
"""
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
load_dotenv(env_path)


def generate_admin_jwt(email: str, expires_days: int = 365) -> str:
    """
    Generate an admin JWT token.
    
    Args:
        email: Email for JWT subject (sub claim)
        expires_days: Token expiration in days
        
    Returns:
        Encoded JWT token string
        
    Raises:
        ValueError: If SUPABASE_JWT_SECRET not found in environment
    """
    secret_key = os.getenv("SUPABASE_JWT_SECRET")
    if not secret_key:
        raise ValueError(
            "SUPABASE_JWT_SECRET not found in environment variables.\n"
            "Please set it in your .env file or environment."
        )

    payload = {
        "sub": email,
        "role": "admin",
        "is_admin": True,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def main():
    parser = argparse.ArgumentParser(
        description="Generate admin JWT token for FisioRAG API"
    )
    parser.add_argument(
        "--email",
        default=os.getenv("ADMIN_EMAIL", "admin@fisiorag.local"),
        help="Admin email for JWT subject (default: from ADMIN_EMAIL env or admin@fisiorag.local)",
    )
    parser.add_argument(
        "--expires-days",
        type=int,
        default=365,
        help="Token expiration in days (default: 365)",
    )

    args = parser.parse_args()

    try:
        token = generate_admin_jwt(args.email, args.expires_days)

        print("=" * 80)
        print("JWT ADMIN TOKEN GENERATED:")
        print("=" * 80)
        print(token)
        print("=" * 80)
        print("\nExport as environment variable:")
        print(f'export ADMIN_JWT="{token}"')
        print("\nOr in PowerShell:")
        print(f'$env:ADMIN_JWT="{token}"')
        print("=" * 80)

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

