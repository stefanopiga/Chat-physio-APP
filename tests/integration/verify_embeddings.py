import asyncio
import asyncpg
import os

async def verify():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    
    try:
        # Verifica embeddings esistono
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) AS total_chunks,
                COUNT(embedding) AS with_embeddings,
                COUNT(*) - COUNT(embedding) AS without_embeddings,
                ROUND(
                    (COUNT(embedding)::numeric / NULLIF(COUNT(*), 0)) * 100, 
                    2
                ) AS coverage_percent
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'completed'
        """)
        
        print("\n✅ EMBEDDING COVERAGE:")
        print(f"  Total chunks: {result['total_chunks']}")
        print(f"  With embeddings: {result['with_embeddings']}")
        print(f"  Without embeddings: {result['without_embeddings']}")
        status_emoji = "✅" if result['coverage_percent'] == 100.0 else "⚠️"
        print(f"  {status_emoji} Coverage: {result['coverage_percent']}%")
        
        # Verifica metadata chunks
        print("\n📊 SAMPLE CHUNK METADATA:")
        samples = await conn.fetch("""
            SELECT 
                dc.id,
                LEFT(dc.content, 50) AS content_preview,
                dc.metadata,
                CASE 
                    WHEN dc.embedding IS NOT NULL THEN 'YES'
                    ELSE 'NO'
                END AS has_embedding
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'completed'
            LIMIT 3
        """)
        
        for sample in samples:
            print(f"\n  Chunk ID: {sample['id']}")
            print(f"  Content: {sample['content_preview']}...")
            print(f"  Has embedding: {sample['has_embedding']}")
            print(f"  Metadata: {sample['metadata']}")
        
        # Verifica documento metadata
        print("\n📄 DOCUMENTS METADATA:")
        docs = await conn.fetch("""
            SELECT 
                d.file_name,
                d.metadata,
                COUNT(dc.id) AS chunk_count,
                COUNT(dc.embedding) AS chunks_with_emb
            FROM documents d
            LEFT JOIN document_chunks dc ON d.id = dc.document_id
            WHERE d.status = 'completed'
            GROUP BY d.id, d.file_name, d.metadata
        """)
        
        for doc in docs:
            print(f"\n  📁 {doc['file_name']}")
            print(f"     Chunks: {doc['chunk_count']} (embeddings: {doc['chunks_with_emb']})")
            print(f"     Metadata: {doc['metadata']}")
        
    finally:
        await conn.close()

asyncio.run(verify())


