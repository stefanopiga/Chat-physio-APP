"""Test utilities shared across API test modules."""
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple, Union


class InMemoryRedis:
    """Minimal Redis-like store for unit tests."""

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[bytes, Optional[float]]] = {}

    def setex(self, key: str, ttl: int, value: Union[str, bytes]) -> None:
        expires_at: Optional[float] = None
        if ttl:
            expires_at = time.time() + ttl
        payload = value if isinstance(value, bytes) else value.encode("utf-8")
        self._store[key] = (payload, expires_at)

    def get(self, key: str) -> Optional[bytes]:
        record = self._store.get(key)
        if not record:
            return None
        payload, expires_at = record
        if expires_at is not None and expires_at < time.time():
            self._store.pop(key, None)
            return None
        return payload

    def delete(self, *keys: Union[str, bytes]) -> int:
        if not keys:
            return 0
        removed = 0
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            if self._store.pop(key_str, None):
                removed += 1
        return removed

    def scan_iter(self, match: str):
        prefix = match.replace("*", "")
        for key in list(self._store.keys()):
            if key.startswith(prefix):
                yield key
