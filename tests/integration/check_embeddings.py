import asyncio
import asyncpg
import os
import sys

async def check():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    
    try:
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) AS total,
                COUNT(embedding) AS with_emb,
                COUNT(*) - COUNT(embedding) AS without_emb
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'completed'
        """)
        
        print(f"\nEmbedding Coverage:")
        print(f"  Total chunks: {result['total']}")
        print(f"  With embeddings: {result['with_emb']}")
        print(f"  Without embeddings: {result['without_emb']}")
        
        if result['without_emb'] == 0:
            print(f"  ✅ Coverage: 100%\n")
        else:
            pct = (result['with_emb'] / result['total'] * 100) if result['total'] > 0 else 0
            print(f"  ⚠️  Coverage: {pct:.1f}%\n")
            
    finally:
        await conn.close()

asyncio.run(check())

