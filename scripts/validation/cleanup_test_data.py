#!/usr/bin/env python3
"""
Cleanup Test Data Script - Story 2.6

Elimina tutti chunks e documenti esistenti per test fresh pipeline validation.
Usa DATABASE_URL da .env file root.

Usage (PowerShell):
    # Con Poetry (da apps/api)
    cd apps/api
    poetry run python ../../scripts/validation/cleanup_test_data.py --confirm
    
    # Python standalone (da project root)
    python scripts/validation/cleanup_test_data.py --confirm
    python scripts/validation/cleanup_test_data.py --confirm --verbose

Requirements:
    - Con Poetry: dependencies già in apps/api/pyproject.toml
    - Senza Poetry: pip install -r scripts/requirements.txt
"""
import os
import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

# Load environment da .env root
project_root = Path(__file__).resolve().parents[2]
env_file = project_root / ".env"
load_dotenv(env_file)


def cleanup_database(database_url: str, verbose: bool = False) -> dict:
    """
    Elimina tutti record da document_chunks e documents tables.
    
    Returns:
        dict con conteggi eliminati: {"chunks_deleted": int, "documents_deleted": int}
    """
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    cur = conn.cursor()
    
    try:
        # Count prima di cleanup
        cur.execute("SELECT COUNT(*) FROM document_chunks")
        chunks_before = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM documents")
        docs_before = cur.fetchone()[0]
        
        if verbose:
            print(f"Before cleanup: {chunks_before} chunks, {docs_before} documents")
        
        # DELETE chunks (foreign key ON DELETE CASCADE eliminerà automaticamente)
        # Ma delete esplicito per chunks prima
        cur.execute("DELETE FROM document_chunks")
        chunks_deleted = cur.rowcount
        
        # DELETE documents
        cur.execute("DELETE FROM documents")
        docs_deleted = cur.rowcount
        
        # Commit transaction
        conn.commit()
        
        if verbose:
            print(f"Deleted: {chunks_deleted} chunks, {docs_deleted} documents")
        
        return {
            "chunks_deleted": chunks_deleted,
            "documents_deleted": docs_deleted,
            "chunks_before": chunks_before,
            "documents_before": docs_before
        }
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup test data: DELETE chunks e documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validation/cleanup_test_data.py
  python scripts/validation/cleanup_test_data.py --confirm
  python scripts/validation/cleanup_test_data.py --confirm --verbose

Note:
  - Script legge DATABASE_URL da .env file root
  - Operazione irreversibile (DELETE, non TRUNCATE)
  - Flag --confirm richiesto per safety
        """
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Conferma operazione cleanup (richiesto per esecuzione)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Output verbose con conteggi"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL (default: da .env DATABASE_URL)"
    )
    
    args = parser.parse_args()
    
    # Validation
    if not args.database_url:
        print("Error: DATABASE_URL non trovato in .env file", file=sys.stderr)
        print(f"Verificare file: {project_root / '.env'}", file=sys.stderr)
        return 1
    
    if not args.confirm:
        print("⚠️  WARNING: Operazione eliminerà tutti chunks e documenti dal database")
        print()
        print("Per procedere, eseguire con flag --confirm:")
        print("  python scripts/validation/cleanup_test_data.py --confirm")
        return 0
    
    # Execute cleanup
    try:
        if args.verbose:
            print("=" * 80)
            print("DATABASE CLEANUP - Story 2.6")
            print("=" * 80)
            print()
            print(f"Database: {args.database_url[:50]}...")
            print()
        
        result = cleanup_database(args.database_url, verbose=args.verbose)
        
        # Summary
        print()
        print("✅ Cleanup completato")
        print(f"   Chunks eliminati: {result['chunks_deleted']}")
        print(f"   Documents eliminati: {result['documents_deleted']}")
        print()
        
        if args.verbose:
            print("Database ora vuoto, pronto per test ingestion fresh")
            print("=" * 80)
        
        return 0
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

