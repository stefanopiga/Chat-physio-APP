"""
Conversation Manager Service (Story 7.1).

Gestisce conversational memory con sliding window (ultimi 3 turni).

Features:
- Load/save conversation context da chat_messages_store
- Token counting (tiktoken con fallback)
- Token budget enforcement (max 2000 token)
- Message compacting per messaggi più vecchi
- Sliding window (keep last 6 messages)

Reference: docs/architecture/addendum-conversational-memory-patterns.md
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from ..models.conversation import ConversationMessage, ChatContextWindow
from ..stores import chat_messages_store

logger = logging.getLogger("api")

# Try import tiktoken for token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning({
        "event": "tiktoken_unavailable",
        "fallback": "approximate_token_counting",
    })


class ConversationManager:
    """
    Gestisce conversational memory per RAG system.
    
    Story 7.1 AC3, AC4: Sliding window context (3 turni), token budget enforcement.
    """
    
    # Configuration (default values, overridable via Settings)
    MAX_TURNS = 3  # 3 turni = 6 messaggi totali
    MAX_CONTEXT_TOKENS = 2000  # Token budget per context window
    COMPACT_MESSAGE_LENGTH = 150  # Lunghezza compattata per messaggi vecchi
    
    def __init__(
        self,
        max_turns: int = MAX_TURNS,
        max_tokens: int = MAX_CONTEXT_TOKENS,
        compact_length: int = COMPACT_MESSAGE_LENGTH,
    ):
        """
        Inizializza ConversationManager.
        
        Args:
            max_turns: Numero massimo turni da mantenere (default 3)
            max_tokens: Token budget massimo per context (default 2000)
            compact_length: Lunghezza massima messaggi compattati (default 150)
        """
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.compact_length = compact_length
        
        # Lazy init tiktoken encoder
        self.tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception as exc:
                logger.warning({
                    "event": "tiktoken_init_failed",
                    "error": str(exc),
                    "fallback": "approximate_counting",
                })
    
    def get_context_window(self, session_id: str) -> ChatContextWindow:
        """
        Recupera context window per sessione specificata.
        
        Story 7.1 AC3: Load ultimi 3 turni (6 messaggi) da chat_messages_store,
        calcola token count, applica truncation se necessario.
        
        Args:
            session_id: Session identifier
        
        Returns:
            ChatContextWindow con ultimi N turni, token count aggiornato
        """
        # Load messages from store
        stored_messages = chat_messages_store.get(session_id, [])
        if not stored_messages:
            return ChatContextWindow(
                session_id=session_id,
                messages=[],
                total_tokens=0,
            )
        
        # Convert stored dict to ConversationMessage
        conversation_messages: List[ConversationMessage] = []
        for msg_dict in stored_messages:
            try:
                # Extract fields from stored dict
                role = msg_dict.get("role", "assistant")
                content = msg_dict.get("content", "")
                
                # Parse timestamp
                timestamp_str = msg_dict.get("created_at")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except Exception:
                        timestamp = datetime.now(timezone.utc)
                else:
                    timestamp = datetime.now(timezone.utc)
                
                # Extract chunk_ids if assistant message
                chunk_ids = None
                if role == "assistant":
                    citations = msg_dict.get("citations", [])
                    if citations:
                        chunk_ids = [c.get("chunk_id") for c in citations if c.get("chunk_id")]
                
                conversation_messages.append(
                    ConversationMessage(
                        role=role,
                        content=content,
                        timestamp=timestamp,
                        chunk_ids=chunk_ids,
                    )
                )
            except Exception as exc:
                logger.debug({
                    "event": "message_parse_skip",
                    "session_id": session_id,
                    "error": str(exc),
                })
                continue
        
        # Keep only last MAX_TURNS * 2 messages (sliding window)
        max_messages = self.max_turns * 2  # 2 messages per turn (user + assistant)
        if len(conversation_messages) > max_messages:
            conversation_messages = conversation_messages[-max_messages:]
        
        # Calculate token count
        total_tokens = self._count_tokens(conversation_messages)
        
        # Truncate if exceeds budget
        if total_tokens > self.max_tokens:
            conversation_messages = self._truncate_to_budget(conversation_messages)
            total_tokens = self._count_tokens(conversation_messages)
        
        logger.debug({
            "event": "context_window_loaded",
            "session_id": session_id,
            "messages_count": len(conversation_messages),
            "total_tokens": total_tokens,
            "truncated": total_tokens > self.max_tokens,
        })
        
        return ChatContextWindow(
            session_id=session_id,
            messages=conversation_messages,
            total_tokens=total_tokens,
            updated_at=datetime.now(timezone.utc),
        )
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        chunk_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Aggiunge un nuovo turno conversazionale (user + assistant message).
        
        Story 7.1 AC3: Persiste in chat_messages_store con timestamp e chunk_ids.
        
        Args:
            session_id: Session identifier
            user_message: Messaggio utente
            assistant_message: Risposta assistant
            chunk_ids: IDs chunk citati nella risposta (opzionale)
        """
        timestamp_now = datetime.now(timezone.utc).isoformat()
        
        # User message
        user_msg_dict = {
            "id": f"user_{session_id}_{timestamp_now}",
            "session_id": session_id,
            "role": "user",
            "content": user_message,
            "created_at": timestamp_now,
        }
        
        # Assistant message
        assistant_msg_dict = {
            "id": f"assistant_{session_id}_{timestamp_now}",
            "session_id": session_id,
            "role": "assistant",
            "content": assistant_message,
            "citations": [{"chunk_id": cid} for cid in (chunk_ids or [])],
            "created_at": timestamp_now,
        }
        
        # Append to store
        stored_messages = chat_messages_store.get(session_id, [])
        stored_messages.extend([user_msg_dict, assistant_msg_dict])
        chat_messages_store[session_id] = stored_messages
        
        logger.info({
            "event": "conversation_turn_added",
            "session_id": session_id,
            "turn_number": len(stored_messages) // 2,
            "user_msg_length": len(user_message),
            "assistant_msg_length": len(assistant_message),
            "chunks_cited": len(chunk_ids) if chunk_ids else 0,
        })
    
    def format_for_prompt(self, context_window: ChatContextWindow) -> str:
        """
        Formatta context window per inclusion nel prompt LLM.
        
        Story 7.1 AC4: Formato "STUDENTE: ...\nTUTOR: ...\n"
        Messaggi più vecchi vengono compattati.
        
        Args:
            context_window: ChatContextWindow da formattare
        
        Returns:
            Stringa formattata pronta per inclusion in prompt
        """
        if not context_window.messages:
            return "\n=== PRIMA INTERAZIONE (nessuna cronologia) ===\n"
        
        formatted_lines = []
        messages = context_window.messages
        
        for idx, msg in enumerate(messages):
            # Keep last 2 messages full, compact older ones
            is_recent = idx >= len(messages) - 2
            
            if is_recent:
                role_label = "STUDENTE" if msg.role == "user" else "TUTOR"
                formatted_lines.append(f"{role_label}: {msg.content}")
            else:
                # Use compact format for older messages
                formatted_lines.append(msg.to_compact_format(self.compact_length))
        
        formatted_history = "\n\n".join(formatted_lines)
        
        return f"""
=== CRONOLOGIA CONVERSAZIONE ===

{formatted_history}

ISTRUZIONI CONTESTUALI:
- Se la domanda corrente si riferisce alla conversazione precedente 
  (es. "approfondisci", "come prima", "il punto 2"), usa la cronologia per contestualizzare
- Mantieni coerenza e consistenza con risposte precedenti
- Se necessario, fai riferimento esplicito a concetti già discussi
"""
    
    def _count_tokens(self, messages: List[ConversationMessage]) -> int:
        """
        Conta token per lista messaggi.
        
        Story 7.1: Usa tiktoken se disponibile, altrimenti fallback approximation.
        
        Args:
            messages: Lista ConversationMessage
        
        Returns:
            Token count totale
        """
        if not messages:
            return 0
        
        # Concatenate all message contents
        text = " ".join([msg.content for msg in messages])
        
        # Try tiktoken
        if self.tokenizer:
            try:
                tokens = self.tokenizer.encode(text)
                return len(tokens)
            except Exception as exc:
                logger.debug({
                    "event": "tiktoken_counting_failed",
                    "error": str(exc),
                    "fallback": "approximate",
                })
        
        # Fallback: approximate 1 token ≈ 4 characters
        return len(text) // 4
    
    def _truncate_to_budget(
        self,
        messages: List[ConversationMessage],
    ) -> List[ConversationMessage]:
        """
        Truncate messaggi più vecchi fino a rientrare nel token budget.
        
        Story 7.1: Remove oldest messages fino a < MAX_CONTEXT_TOKENS.
        Mantiene sempre almeno ultimo turno (2 messaggi).
        
        Args:
            messages: Lista ConversationMessage (ordinati cronologicamente)
        
        Returns:
            Lista messaggi troncata
        """
        if len(messages) <= 2:
            # Keep at least last turn
            return messages
        
        # Remove oldest messages until budget satisfied
        truncated = messages[:]
        while len(truncated) > 2:
            token_count = self._count_tokens(truncated)
            if token_count <= self.max_tokens:
                break
            # Remove oldest message
            truncated = truncated[1:]
        
        if len(truncated) < len(messages):
            logger.info({
                "event": "context_window_truncated",
                "original_count": len(messages),
                "truncated_count": len(truncated),
                "removed_count": len(messages) - len(truncated),
            })
        
        return truncated


# Singleton instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager(
    max_turns: int = ConversationManager.MAX_TURNS,
    max_tokens: int = ConversationManager.MAX_CONTEXT_TOKENS,
    compact_length: int = ConversationManager.COMPACT_MESSAGE_LENGTH,
) -> ConversationManager:
    """
    Dependency per ottenere ConversationManager (singleton pattern).
    
    Story 7.1: Configuration via Settings (passed from endpoint).
    
    Args:
        max_turns: Maximum conversation turns to keep
        max_tokens: Token budget per context window
        compact_length: Max length for compacted messages
    
    Returns:
        ConversationManager instance
    """
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(
            max_turns=max_turns,
            max_tokens=max_tokens,
            compact_length=compact_length,
        )
    return _conversation_manager


def reset_conversation_manager() -> None:
    """
    Reset conversation manager singleton (per testing).
    
    Story 7.1: Utility per test che modificano configurazione.
    """
    global _conversation_manager
    _conversation_manager = None

