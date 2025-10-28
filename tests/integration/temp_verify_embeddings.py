#!/usr/bin/env python3
"""Script temporaneo per verificare coverage embeddings post-batch."""
import asyncio
import asyncpg
import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api"))

from api.config import Settings

async def verify():
    settings = Settings()
    conn = await asyncpg.connect(settings.database_uri)
    
    try:
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) AS total_chunks,
                COUNT(embedding) AS with_embeddings,
                COUNT(*) - COUNT(embedding) AS without_embeddings,
                ROUND((COUNT(embedding)::float / NULLIF(COUNT(*), 0)) * 100, 2) AS coverage_percent
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'completed'
        """)
        
        print(f"\n📊 Embedding Coverage:")
        print(f"  Total chunks: {result['total_chunks']}")
        print(f"  With embeddings: {result['with_embeddings']}")
        print(f"  Without embeddings: {result['without_embeddings']}")
        print(f"  Coverage: {result['coverage_percent']}%\n")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify())

