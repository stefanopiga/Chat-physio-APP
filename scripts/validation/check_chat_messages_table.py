"""Verifica se tabella chat_messages e indici esistono."""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)

DATABASE_URL = os.getenv("DATABASE_URL")

async def check_table():
    conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
    
    # Check table
    table_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'chat_messages'
        );
    """)
    
    print(f"Table chat_messages exists: {table_exists}")
    
    if table_exists:
        # Check indices
        indices = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'chat_messages' 
            AND schemaname = 'public'
            ORDER BY indexname;
        """)
        
        print(f"\nIndices found ({len(indices)}):")
        for idx in indices:
            print(f"  - {idx['indexname']}")
        
        # Check required indices
        required = [
            "idx_chat_messages_idempotency_key",
            "idx_chat_messages_session_created",
            "idx_chat_messages_created_at",
            "idx_chat_messages_content_fts",
            "idx_chat_messages_metadata_archived",
        ]
        
        found = [idx['indexname'] for idx in indices]
        print(f"\nRequired indices check:")
        for req in required:
            status = "✓" if req in found else "✗"
            print(f"  {status} {req}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_table())

