"""
Watcher Runner Async - Entry point for DB-first watcher pipeline.

Story 6.3: Async refactoring con DB-first storage.

Usage:
    poetry --directory apps/api run python scripts/watcher_runner.py

Requirements:
    - DATABASE_URL configured in .env
    - asyncpg pool initialization
    - Least-privilege DB role (read/write on documents, document_chunks)

Exit Codes:
    0: Success - all documents processed
    1: Error - configuration or runtime error
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add api module to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import get_settings
from api import database  # Import module for global db_pool access
from api.database import init_db_pool, close_db_pool
from api.ingestion.config import IngestionConfig
from api.ingestion.watcher import scan_once

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("watcher_runner")


async def run_watcher_once():
    """
    Execute single watcher scan with DB-first integration.
    
    Workflow:
    1. Initialize asyncpg pool (with retry logic for transient failures)
    2. Acquire connection from pool
    3. Execute scan_once() async with connection
    4. Close pool on completion or error
    
    Returns:
        int: Exit code (0=success, 1=error)
    """
    exit_code = 0
    max_retries = 3
    base_delay = 2  # seconds
    
    try:
        # Initialize DB pool with exponential backoff retry
        logger.info({"event": "watcher_runner_init", "status": "starting"})
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info({
                    "event": "watcher_runner_pool_attempt",
                    "attempt": attempt,
                    "max_retries": max_retries
                })
                await init_db_pool()
                
                # CRITICAL: Access db_pool through module reference (Story 6.3 fix)
                if database.db_pool:
                    logger.info({
                        "event": "watcher_runner_pool_connected",
                        "attempt": attempt
                    })
                    break
                else:
                    logger.warning({
                        "event": "watcher_runner_pool_none_after_init",
                        "attempt": attempt
                    })
                    
            except Exception as e:
                logger.warning({
                    "event": "watcher_runner_pool_exception",
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                if attempt == max_retries:
                    raise  # Re-raise on final attempt
                
                delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff: 2s, 4s, 8s
                logger.info({
                    "event": "watcher_runner_pool_retry_wait",
                    "retry_delay_seconds": delay
                })
                await asyncio.sleep(delay)
        
        if not database.db_pool:
            logger.error({"event": "watcher_runner_pool_init_failed"})
            return 1
        
        # Load configuration
        cfg = IngestionConfig.from_env()
        settings = get_settings()
        inventory = {}  # Fresh inventory for each run
        
        # Acquire connection and run watcher scan
        async with database.db_pool.acquire() as conn:
            logger.info(
                {
                    "event": "watcher_runner_scan_start",
                    "watch_dir": str(cfg.watch_dir),
                }
            )
            
            documents = await scan_once(cfg, inventory, settings, conn=conn)
            
            logger.info(
                {
                    "event": "watcher_async_scan_complete",
                    "documents_processed": len(documents),
                    "status": "success",
                }
            )
            
            # Log summary per document status
            status_counts = {}
            for doc in documents:
                status = doc.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            logger.info(
                {
                    "event": "watcher_runner_summary",
                    "status_breakdown": status_counts,
                }
            )
        
    except Exception as exc:
        logger.error(
            {
                "event": "watcher_runner_error",
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        exit_code = 1
    
    finally:
        # Always close pool
        logger.info({"event": "watcher_runner_cleanup", "status": "closing_pool"})
        await close_db_pool()
    
    return exit_code


def main():
    """
    Main entry point for watcher runner.
    
    Runs async event loop and returns appropriate exit code.
    """
    logger.info(
        {
            "event": "watcher_runner_start",
            "python_version": sys.version,
            "database_url_configured": "DATABASE_URL" in os.environ,
        }
    )
    
    exit_code = asyncio.run(run_watcher_once())
    
    logger.info(
        {
            "event": "watcher_runner_complete",
            "exit_code": exit_code,
        }
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

