"""Check if chunks were written to database."""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

async def check_chunks():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("[!] DATABASE_URL not found in environment")
        return
    
    print("[+] Connecting to database...")
    print(f"    DSN: {dsn[:50]}...")
    
    try:
        conn = await asyncpg.connect(dsn, statement_cache_size=0, timeout=10.0)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}")
        return
    
    try:
        # Check documents
        docs = await conn.fetch("SELECT id, title, created_at FROM documents ORDER BY created_at DESC LIMIT 5;")
        print(f"\n[+] Recent documents: {len(docs)}")
        for doc in docs:
            print(f"    - {doc['id']}: {doc['title'][:50]}")
        
        # Check chunks
        chunks_count = await conn.fetchval("SELECT COUNT(*) FROM document_chunks;")
        print(f"\n[+] Total chunks in DB: {chunks_count}")
        
        if chunks_count > 0:
            recent_chunks = await conn.fetch(
                "SELECT id, document_id, chunk_index, LENGTH(content) as len "
                "FROM document_chunks ORDER BY created_at DESC LIMIT 5;"
            )
            print("\n[+] Recent chunks:")
            for chunk in recent_chunks:
                print(f"    - Chunk {chunk['chunk_index']} (doc {chunk['document_id'][:8]}...) - {chunk['len']} chars")
        else:
            print("\n[!] No chunks found in database!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_chunks())

