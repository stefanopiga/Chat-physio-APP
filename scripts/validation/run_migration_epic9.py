"""
Script per eseguire migration Epic 9 Story 9.1.

Esegue migration SQL per creare tabella chat_messages e indici.
"""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non configurata in .env")

# Path to migration SQL file
migration_file = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "20251106000000_epic9_conversational_memory_indices.sql"

if not migration_file.exists():
    raise FileNotFoundError(f"Migration file non trovato: {migration_file}")

async def run_migration():
    """Esegui migration SQL."""
    print(f"[INFO] Connecting to database...")
    
    try:
        # Connect to database (disable prepared statements per pgbouncer)
        conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        print("[OK] Database connection established")
        
        # Read migration SQL
        migration_sql = migration_file.read_text(encoding="utf-8")
        print(f"[INFO] Loaded migration SQL ({len(migration_sql)} chars)")
        
        # Execute migration
        print("[INFO] Executing migration...")
        await conn.execute(migration_sql)
        print("[OK] Migration executed successfully")
        
        # Verify table exists
        table_check = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'chat_messages'
            );
        """)
        
        if table_check:
            print("[OK] Table 'chat_messages' exists")
        else:
            print("[ERROR] Table 'chat_messages' NOT found")
        
        # Verify indices
        indices = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'chat_messages' 
            AND schemaname = 'public';
        """)
        
        print(f"[INFO] Found {len(indices)} indices on chat_messages:")
        for idx in indices:
            print(f"  - {idx['indexname']}")
        
        # Check for required indices
        required_indices = [
            "idx_chat_messages_idempotency_key",
            "idx_chat_messages_session_created",
            "idx_chat_messages_created_at",
            "idx_chat_messages_content_fts",
            "idx_chat_messages_metadata_archived",
        ]
        
        found_indices = [idx['indexname'] for idx in indices]
        for req_idx in required_indices:
            if req_idx in found_indices:
                print(f"[OK] Index '{req_idx}' found")
            else:
                print(f"[WARN] Index '{req_idx}' NOT found")
        
        await conn.close()
        print("[OK] Migration completed successfully")
        
    except Exception as exc:
        print(f"[ERROR] Migration failed: {exc}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())

