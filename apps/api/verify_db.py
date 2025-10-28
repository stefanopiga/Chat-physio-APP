"""Quick DB verification script"""
import asyncio
import asyncpg
import os

async def verify():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    try:
        docs = await conn.fetchval("SELECT COUNT(*) FROM documents")
        chunks = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")
        print(f"✅ Documents: {docs}")
        print(f"✅ Chunks: {chunks}")
        
        recent = await conn.fetch("SELECT file_name, status FROM documents ORDER BY created_at DESC LIMIT 5")
        print("\n📄 Recent documents:")
        for row in recent:
            print(f"  - {row['file_name']}: {row['status']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify())

