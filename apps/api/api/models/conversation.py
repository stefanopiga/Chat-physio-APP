"""
Conversation Models (Story 7.1).

Pydantic models per gestione conversational memory:
- ConversationMessage: singolo messaggio user/assistant
- ChatContextWindow: sliding window ultimi 3 turni (6 messaggi)

Features:
- Token counting per budget enforcement
- Message compacting per messaggi più vecchi
- Timestamp tracking per analytics
"""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """
    Singolo messaggio conversazionale (user o assistant).
    
    Story 7.1 AC3: Rappresenta un turno in conversazione multi-turno.
    """
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Ruolo mittente messaggio",
    )
    content: str = Field(
        ...,
        description="Contenuto testuale messaggio",
        min_length=1,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp creazione messaggio (UTC)",
    )
    chunk_ids: Optional[List[str]] = Field(
        default=None,
        description="IDs chunk citati nella risposta (se assistant message)",
    )
    
    def to_compact_format(self, max_length: int = 150) -> str:
        """
        Compatta messaggio per inclusion in context window (messaggi più vecchi).
        
        Args:
            max_length: Lunghezza massima contenuto compattato
        
        Returns:
            Stringa formato "ROLE: content..." (troncato se necessario)
        """
        role_label = "STUDENTE" if self.role == "user" else "TUTOR"
        content = self.content.strip()
        
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return f"{role_label}: {content}"


class ChatContextWindow(BaseModel):
    """
    Context window per conversational memory (Story 7.1 AC3).
    
    Sliding window ultimi 3 turni (6 messaggi: 3 user + 3 assistant).
    Enforces token budget (max 2000 token default).
    """
    session_id: str = Field(
        ...,
        description="Session identifier",
        min_length=1,
    )
    messages: List[ConversationMessage] = Field(
        default_factory=list,
        description="Lista messaggi nel context window (max 6: ultimi 3 turni)",
        max_length=6,
    )
    total_tokens: int = Field(
        default=0,
        description="Token count totale per tutti i messaggi nel window",
        ge=0,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp creazione context window",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp ultimo aggiornamento",
    )
    
    def get_last_n_messages(self, n: int) -> List[ConversationMessage]:
        """
        Recupera ultimi N messaggi dal context window.
        
        Args:
            n: Numero messaggi da recuperare
        
        Returns:
            Lista ultimi N messaggi (ordine cronologico)
        """
        if n <= 0:
            return []
        return self.messages[-n:]
    
    def format_for_display(self) -> str:
        """
        Formatta context window per display/debugging.
        
        Returns:
            Stringa multi-line con messaggi formattati
        """
        if not self.messages:
            return "[CONTEXT WINDOW VUOTO]"
        
        lines = []
        for idx, msg in enumerate(self.messages):
            role_label = "STUDENTE" if msg.role == "user" else "TUTOR"
            timestamp_str = msg.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{idx+1}] {timestamp_str} {role_label}: {msg.content[:100]}...")
        
        return "\n".join(lines)

