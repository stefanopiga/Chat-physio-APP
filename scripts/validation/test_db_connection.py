"""Test veloce connessione database per debug."""
import asyncio
import os
import sys

import asyncpg


async def test_connection():
    """Test rapido connessione."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL non configurato")
        sys.exit(1)
    
    print(f"🔄 Tentativo connessione a database...")
    print(f"   DSN: {dsn[:50]}...")
    
    try:
        # Timeout 5 secondi
        conn = await asyncio.wait_for(
            asyncpg.connect(dsn, statement_cache_size=0),
            timeout=5.0
        )
        print("✅ Connessione riuscita!")
        
        # Test query semplice
        result = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")
        print(f"✅ Query OK: {result} chunks totali")
        
        await conn.close()
        print("✅ Test completato con successo")
        
    except asyncio.TimeoutError:
        print("❌ TIMEOUT: connessione database non risponde entro 5 secondi")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERRORE: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_connection())

