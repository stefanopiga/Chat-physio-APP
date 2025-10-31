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

# DEPRECATED: feedback_store in-memory rimosso in Story 4.2.4
# Feedback ora persistito su Supabase tabella public.feedback
# Vedere: apps/api/api/repositories/feedback_repository.py
# Endpoint aggiornati:
#   - POST /api/v1/chat/messages/{messageId}/feedback (apps/api/api/routers/chat.py)
#   - GET /api/v1/admin/analytics (apps/api/api/routers/admin.py)
# feedback_store: Dict[str, Dict[str, Any]] = {}  # NO LONGER USED

# Store in-memory per job di indicizzazione (Story 2.4)
sync_jobs_store: Dict[str, Dict[str, Any]] = {}

# Store in-memory per rate limiting (Story 1.3.1)
_rate_limit_store: Dict[str, Dict[str, Any]] = {}

