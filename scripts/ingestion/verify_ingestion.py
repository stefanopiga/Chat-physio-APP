#!/usr/bin/env python3
"""
Verify document ingestion in database.

Usage:
    python verify_ingestion.py <job_id>

Environment variables required:
    DATABASE_URL - PostgreSQL connection URL
"""
import os
import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

# Load environment
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")


def verify_ingestion(job_id: str, database_url: str) -> None:
    """Verify chunks for given job_id in database."""
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    # Count chunks
    cur.execute(
        "SELECT COUNT(*) FROM document_chunks WHERE document_id = %s", (job_id,)
    )
    chunk_count = cur.fetchone()[0]

    # Get document info
    cur.execute(
        """
        SELECT d.file_name, d.created_at
        FROM documents d
        WHERE d.id = %s
        """,
        (job_id,),
    )
    doc_info = cur.fetchone()

    print("=" * 80)
    print("INGESTION VERIFICATION")
    print("=" * 80)
    print()
    print(f"Job ID: {job_id}")
    print()

    if doc_info:
        document_name, created_at = doc_info
        print(f"Document: {document_name}")
        print(f"Created: {created_at}")
        print(f"Chunks: {chunk_count}")
        print()

        if chunk_count > 0:
            print("✓ Ingestion successful!")
        else:
            print("⚠ Warning: No chunks found")
    else:
        print("✗ Error: Document not found in database")

    print("=" * 80)

    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Verify document ingestion")
    parser.add_argument("job_id", help="Job ID from ingestion response")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL",
    )

    args = parser.parse_args()

    if not args.database_url:
        print("Error: DATABASE_URL not found", file=sys.stderr)
        return 1

    try:
        verify_ingestion(args.job_id, args.database_url)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

