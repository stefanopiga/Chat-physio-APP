import os
import asyncpg
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Pool globale (inizializzato all'avvio dell'app)
db_pool: asyncpg.Pool | None = None


async def init_db_pool():
    """
    Inizializza il connection pool all'avvio di FastAPI.
    
    Configuration:
    - DATABASE_URL: postgresql://user:pass@host:port/dbname
    - min_size: Connessioni minime mantenute nel pool
    - max_size: Connessioni massime nel pool
    - command_timeout: Timeout query in secondi
    - max_inactive_connection_lifetime: Riconnessione dopo inattività (secondi)
    """
    global db_pool
    
    import logging
    logger = logging.getLogger("database")
    
    database_url = os.getenv("DATABASE_URL")
    logger.info(f"[database.py] DATABASE_URL configured: {bool(database_url)}")
    
    if not database_url:
        raise RuntimeError("DATABASE_URL non impostata in .env")
    
    logger.info(f"[database.py] Creating pool... (host: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'unknown'})")
    
    try:
        pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            statement_cache_size=0,  # Disabilita prepared statements per pgbouncer compatibility
        )
        logger.info(f"[database.py] Pool created: {pool is not None}")
        db_pool = pool
        logger.info(f"[database.py] db_pool assigned: {db_pool is not None}")
    except Exception as e:
        logger.error(f"[database.py] Pool creation failed: {e}", exc_info=True)
        raise
    

async def close_db_pool():
    """Chiude il connection pool allo shutdown di FastAPI."""
    global db_pool
    if db_pool:
        pool = db_pool
        db_pool = None
        try:
            await asyncio.wait_for(pool.close(), timeout=5)
        except (asyncio.TimeoutError, TimeoutError):  # fallback se chiusura pool resta bloccata
            pool.terminate()


@asynccontextmanager
async def lifespan(app):
    """
    Context manager per lifecycle events di FastAPI.
    
    Gestisce:
    - Startup: inizializzazione connection pool
    - Shutdown: chiusura pool e cleanup risorse
    """
    await init_db_pool()
    yield
    await close_db_pool()


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency per ottenere una connessione dal pool.
    
    Context manager garantisce rilascio connessione anche in caso di eccezione.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(conn: Annotated[asyncpg.Connection, Depends(get_db_connection)]):
            ...
    
    Raises:
        RuntimeError: Se il pool non è stato inizializzato
    """
    if not db_pool:
        raise RuntimeError("Database pool non inizializzato. Verificare lifespan setup.")
    
    async with db_pool.acquire() as connection:
        yield connection
