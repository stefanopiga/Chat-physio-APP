"""
Rate Limiting service - Business logic per rate limiting enforcement.

Story: 1.3, 1.3.1, 4.1, 5.4
"""
import time
import os
from typing import Dict
from fastapi import HTTPException, status
from ..stores import _rate_limit_store


class RateLimitService:
    """
    Rate limiter in-memory per endpoint.
    
    Configuration:
    - Scope isolato per tipo endpoint
    - Reset automatico dopo window
    """
    
    def __init__(self, store: Dict[str, Dict[str, list[float]]] = None):
        # Use shared store or create isolated one
        self._store = store if store is not None else _rate_limit_store
    
    def enforce_rate_limit(
        self,
        key: str,
        scope: str,
        window_seconds: int,
        max_requests: int
    ) -> None:
        """
        Enforce rate limit per key in scope.
        
        Args:
            key: Identifier (IP, admin_id, etc.)
            scope: Scope rate limit (e.g., "exchange_code", "admin_debug")
            window_seconds: Durata finestra in secondi
            max_requests: Max richieste nella finestra
            
        Raises:
            HTTPException: 429 se limit superato
            
        Story 5.4 Task 1.4: Bypass rate limiting in test environment
        """
        # Story 5.4: Bypass se test environment
        if os.getenv("TESTING") == "true" or os.getenv("RATE_LIMITING_ENABLED") == "false":
            return
        
        if not key:
            return
        
        now_ts = time.time()
        window_start = now_ts - window_seconds
        
        # Init scope se non esiste
        if scope not in self._store:
            self._store[scope] = {}
        
        # Get timestamps per key
        timestamps = self._store[scope].get(key, [])
        
        # Cleanup timestamps fuori finestra
        timestamps = [t for t in timestamps if t > window_start]
        
        # Check limit
        if len(timestamps) >= max_requests:
            self._store[scope][key] = timestamps
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limited"
            )
        
        # Add current request
        timestamps.append(now_ts)
        self._store[scope][key] = timestamps


# Global rate limiter instance
rate_limit_service = RateLimitService()
