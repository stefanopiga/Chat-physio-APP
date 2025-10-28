import asyncio
import asyncpg
import os

async def check():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        # Breakdown per documento
        docs = await conn.fetch("""
            SELECT 
                d.id,
                d.file_name,
                d.status,
                d.created_at,
                COUNT(dc.id) AS total_chunks,
                COUNT(dc.embedding) AS with_emb
            FROM documents d
            LEFT JOIN document_chunks dc ON d.id = dc.document_id
            GROUP BY d.id, d.file_name, d.status, d.created_at
            ORDER BY d.created_at DESC
        """)
        
        print("\nDocumenti nel DB:")
        for doc in docs:
            print(f"\n  {doc['file_name']}")
            print(f"    ID: {doc['id']}")
            print(f"    Status: {doc['status']}")
            print(f"    Created: {doc['created_at']}")
            print(f"    Chunks: {doc['total_chunks']} (con emb: {doc['with_emb']})")
            
    finally:
        await conn.close()

asyncio.run(check())

