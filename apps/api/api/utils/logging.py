"""
Logging utilities per structured logging.

Fornisce JSONFormatter per log strutturati.
"""
import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formatter per logging strutturato in JSON.
    
    Features:
    - Timestamp ISO 8601
    - Structured data
    - Extra fields support
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        base: dict = {}
        
        # Se il messaggio è già un dict, usalo direttamente
        if isinstance(record.msg, dict):
            base.update(record.msg)
        else:
            base["message"] = record.getMessage()
        
        base.setdefault("level", record.levelname)
        base.setdefault("logger", record.name)
        base.setdefault("time", datetime.now(timezone.utc).isoformat())
        
        return json.dumps(base, ensure_ascii=False)


def setup_logging():
    """Setup application logging con JSONFormatter."""
    logger = logging.getLogger("api")
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
