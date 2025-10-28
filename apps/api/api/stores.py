"""
In-memory stores per MVP (Tech Debt).

Note: In produzione questi store dovrebbero essere sostituiti con persistenza DB.

Stores:
- chat_messages_store: Messaggi chat per sessione (Story 3.2)
- feedback_store: Feedback utente per messaggi (Story 3.4)
- sync_jobs_store: Status sync jobs KB (Story 2.4)
- _rate_limit_store: Rate limiting tracking (Story 1.3.1)
"""
from typing import Dict, Any

# Store in-memory per messaggi chat per sessione (Story 3.2)
chat_messages_store: Dict[str, list[Dict[str, Any]]] = {}

# Store in-memory per feedback dei messaggi (Story 3.4)
feedback_store: Dict[str, Dict[str, Any]] = {}

# Store in-memory per job di indicizzazione (Story 2.4)
sync_jobs_store: Dict[str, Dict[str, Any]] = {}

# Store in-memory per rate limiting (Story 1.3.1)
_rate_limit_store: Dict[str, Dict[str, Any]] = {}

