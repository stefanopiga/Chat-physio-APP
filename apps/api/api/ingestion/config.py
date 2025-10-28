import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from pydantic import BaseModel

from api.config import Settings, get_settings

logger = logging.getLogger("api")

# Story 6.2 Fix: Root progetto per path relativi (ingestion/watch)
# Supporta `poetry --directory apps/api` eseguito da APPLICAZIONE/
# From: apps/api/api/ingestion/config.py -> APPLICAZIONE/ (5 parent)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


class IngestionConfig(BaseModel):
    watch_dir: Path
    temp_dir: Path

    @classmethod
    def from_env(
        cls,
        settings: Optional[Settings] = None,
    ) -> "IngestionConfig":
        """
        Resolve ingestion configuration using Settings > env vars > defaults.
        """
        resolved_settings = settings or get_settings()

        watch_dir, watch_source = cls._resolve_path(
            settings_value=resolved_settings.ingestion_watch_dir,
            env_key="INGESTION_WATCH_DIR",
            default_path="ingestion/watch",
        )
        temp_dir, temp_source = cls._resolve_path(
            settings_value=resolved_settings.ingestion_temp_dir,
            env_key="INGESTION_TEMP_DIR",
            default_path="ingestion/temp",
        )

        cls._ensure_directory(watch_dir)
        cls._ensure_directory(temp_dir)

        logger.info(
            {
                "event": "ingestion_paths_resolved",
                "watch_dir": str(watch_dir),
                "watch_dir_source": watch_source,
                "temp_dir": str(temp_dir),
                "temp_dir_source": temp_source,
            }
        )

        return cls(watch_dir=watch_dir, temp_dir=temp_dir)

    @staticmethod
    def _resolve_path(
        settings_value: Optional[str],
        env_key: str,
        default_path: str,
    ) -> Tuple[Path, str]:
        """
        Resolve a path according to precedence and return with its source label.
        
        Story 6.2 Fix: Path relativi risolti da PROJECT_ROOT, non da cwd.
        Supporta `poetry --directory apps/api` eseguito da root APPLICAZIONE.
        """
        if settings_value:
            path = Path(settings_value).expanduser()
            # Se relativo, base è PROJECT_ROOT
            if not path.is_absolute():
                path = _PROJECT_ROOT / path
            return path.resolve(), "settings"

        env_value = os.getenv(env_key)
        if env_value:
            path = Path(env_value).expanduser()
            # Se relativo, base è PROJECT_ROOT
            if not path.is_absolute():
                path = _PROJECT_ROOT / path
            return path.resolve(), "env"

        # Path default sempre relativo a PROJECT_ROOT
        default = _PROJECT_ROOT / default_path
        return default.resolve(), "default"

    @staticmethod
    def _ensure_directory(path: Path) -> None:
        """
        Ensure the target directory exists and is writable.
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            logger.error(
                {
                    "event": "ingestion_directory_permission_error",
                    "path": str(path),
                    "error": str(exc),
                }
            )
            raise
        if not os.access(path, os.W_OK):
            logger.error(
                {
                    "event": "ingestion_directory_not_writable",
                    "path": str(path),
                }
            )
            raise PermissionError(f"Directory {path} is not writable")
