from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from dotenv import dotenv_values

from api.config import Settings

logger = logging.getLogger("api")

CRITICAL_ENV_KEYS = {
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_PROJECT",
    "CLASSIFICATION_TIMEOUT_SECONDS",
    "WATCHER_ENABLE_CLASSIFICATION",
    "INGESTION_WATCH_DIR",
    "INGESTION_TEMP_DIR",
    "CLASSIFICATION_CACHE_ENABLED",
    "REDIS_URL",
}


def _mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 6:
        return "***"
    return f"{value[:4]}...{value[-2:]}"


SENSITIVE_REDACTORS: Dict[str, Callable[[Optional[str]], Optional[str]]] = {
    "openai_api_key": _mask_secret,
    "supabase_service_role_key": _mask_secret,
    "supabase_jwt_secret": _mask_secret,
}


def _discover_env_values() -> Dict[str, str]:
    """
    Aggregate dotenv values from candidate project roots.
    """
    values: Dict[str, str] = {}
    seen_files: set[Path] = set()
    candidates: Iterable[Path] = list(Path(__file__).resolve().parents)[::-1]
    candidates = list(candidates) + [Path.cwd()]
    for root in candidates:
        candidate = root / ".env"
        if candidate in seen_files or not candidate.exists():
            continue
        seen_files.add(candidate)
        file_values = {
            key: val
            for key, val in dotenv_values(candidate).items()
            if val is not None
        }
        if file_values:
            values.update(file_values)
    return values


def _redact_field(field: str, value: Any) -> Any:
    redactor = SENSITIVE_REDACTORS.get(field)
    if redactor and isinstance(value, str):
        return redactor(value)
    return value


def _field_to_env(field: str) -> str:
    return field.upper()


def main() -> None:
    settings = Settings()
    env_values = _discover_env_values()
    settings_data = settings.model_dump(mode="python")

    if settings.debug:
        _log_overrides(settings, env_values)

    redacted = {
        field: _redact_field(field, value)
        for field, value in settings_data.items()
    }

    print(json.dumps(redacted, indent=2, sort_keys=True, default=str))


def _log_overrides(settings: Settings, env_values: Dict[str, str]) -> None:
    for env_key in CRITICAL_ENV_KEYS:
        process_value = os.getenv(env_key)
        if process_value is None:
            continue
        env_file_value = env_values.get(env_key)
        if env_file_value is None:
            continue
        if process_value == env_file_value:
            continue

        logger.warning(
            {
                "event": "settings_override_detected",
                "key": env_key,
                "process_value": _mask_secret(process_value),
                "env_file_value": _mask_secret(env_file_value),
                "debug_mode": settings.debug,
            }
        )


if __name__ == "__main__":
    main()
