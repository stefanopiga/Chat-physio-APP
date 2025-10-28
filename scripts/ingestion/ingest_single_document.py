#!/usr/bin/env python3
"""
Ingest a single document into FisioRAG knowledge base.

Usage:
    python ingest_single_document.py <document_path>

Environment variables required:
    SUPABASE_JWT_SECRET - For JWT generation
    API_BASE_URL - FisioRAG API base URL (default: http://localhost)
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

import requests
from docx import Document
from dotenv import load_dotenv

# Import JWT generation from admin script
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "admin"))
from generate_jwt import generate_admin_jwt

# Load environment
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from .docx file."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def prepare_payload(file_path: Path, document_text: str) -> Dict[str, Any]:
    """Prepare ingestion payload."""
    return {
        "document_text": document_text,
        "metadata": {
            "document_name": file_path.name,
            "source_path": str(file_path),
            "category": "fisioterapia",
            "topic": file_path.parent.name,
        },
    }


def ingest_document(
    api_base_url: str, jwt_token: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Call sync-jobs endpoint to ingest document."""
    url = f"{api_base_url}/api/v1/admin/knowledge-base/sync-jobs"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Ingest single document")
    parser.add_argument("document_path", type=Path, help="Path to document file")
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_BASE_URL", "http://localhost"),
        help="API base URL (default: http://localhost)",
    )
    parser.add_argument(
        "--admin-email",
        default=os.getenv("ADMIN_EMAIL", "admin@fisiorag.local"),
        help="Admin email for JWT",
    )

    args = parser.parse_args()

    if not args.document_path.exists():
        print(f"Error: File not found: {args.document_path}", file=sys.stderr)
        return 1

    try:
        print("=" * 80)
        print(f"INGESTING DOCUMENT: {args.document_path.name}")
        print("=" * 80)
        print()

        # Extract text
        print("1. Extracting text...")
        if args.document_path.suffix.lower() == ".docx":
            document_text = extract_text_from_docx(args.document_path)
        else:
            document_text = args.document_path.read_text(encoding="utf-8")

        print(f"   ✓ Extracted {len(document_text)} characters")
        print()

        # Generate JWT
        print("2. Generating admin JWT...")
        jwt_token = generate_admin_jwt(args.admin_email, expires_days=1)
        print("   ✓ JWT generated")
        print()

        # Prepare payload
        print("3. Preparing payload...")
        payload = prepare_payload(args.document_path, document_text)
        print(f"   ✓ Payload ready (document: {payload['metadata']['document_name']})")
        print()

        # Call API
        print("4. Calling ingestion endpoint...")
        result = ingest_document(args.api_url, jwt_token, payload)
        print(f"   ✓ HTTP 200 OK")
        print()

        # Display result
        print("=" * 80)
        print("INGESTION RESULT:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()

        job_id = result.get("job_id")
        if job_id:
            print("✓ Ingestion job started successfully!")
            print(f"  Job ID: {job_id}")
            print()
            print("Monitor progress:")
            print(f"  docker logs fisio-rag-celery-worker --tail 50 -f")
            print()
            print("Verify in database:")
            print(f"  SELECT COUNT(*) FROM document_chunks WHERE document_id = '{job_id}';")
        else:
            print("⚠ Warning: No job_id returned")

        print("=" * 80)
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

