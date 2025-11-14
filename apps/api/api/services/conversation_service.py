"""
Conversation Manager Service (Story 7.1, 9.1).

Gestisce conversational memory con sliding window (ultimi 3 turni).

Features:
- Load/save conversation context da chat_messages_store
- Token counting (tiktoken con fallback)
- Token budget enforcement (max 2000 token)
- Message compacting per messaggi più vecchi
- Sliding window (keep last 6 messages)
- Story 9.1: Hybrid Memory Architecture con L1 cache + L2 DB persistence

Reference: docs/architecture/addendum-conversational-memory-patterns.md
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

from ..models.conversation import ConversationMessage, ChatContextWindow
from ..stores import chat_messages_store
from ..utils.metrics import metrics
from .outbox_queue import OutboxPersistenceQueue
from .persistence_service import ConversationPersistenceService

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
            metrics.increment("cache_misses")
            return ChatContextWindow(
                session_id=session_id,
                messages=[],
                total_tokens=0,
            )
        
        metrics.increment("cache_hits")
        
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
        
        # Story 9.1 AC7: Track active sessions count
        metrics.gauge("active_sessions_count", len(chat_messages_store))
        
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
    enable_persistence: bool = False,
) -> ConversationManager:
    """
    Dependency per ottenere ConversationManager (singleton pattern).
    
    Story 7.1: Configuration via Settings (passed from endpoint).
    Story 9.1 AC3, Task 4: Feature flag controlled initialization.
    
    Args:
        max_turns: Maximum conversation turns to keep
        max_tokens: Token budget per context window
        compact_length: Max length for compacted messages
        enable_persistence: Feature flag per L2 persistence (Story 9.1)
    
    Returns:
        ConversationManager or HybridConversationManager instance
    
    Notes:
        - Se enable_persistence=True e db_pool disponibile → HybridConversationManager
        - Altrimenti → ConversationManager standard (L1 only)
    """
    global _conversation_manager
    if _conversation_manager is None:
        if enable_persistence:
            # Story 9.1: Initialize HybridConversationManager con persistence
            # CRITICAL FIX: Import module (not variable) per accedere db_pool post-lifespan
            from .. import database
            
            if database.db_pool:
                persistence_service = ConversationPersistenceService(database.db_pool)
                outbox_queue = OutboxPersistenceQueue()  # Story 9.1 AC9
                _conversation_manager = HybridConversationManager(
                    persistence_service=persistence_service,
                    enable_persistence=True,
                    outbox_queue=outbox_queue,
                    max_turns=max_turns,
                    max_tokens=max_tokens,
                    compact_length=compact_length,
                )
                logger.info({
                    "event": "hybrid_conversation_manager_initialized",
                    "persistence_enabled": True,
                    "outbox_enabled": True,
                    "db_pool_available": True,
                })
            else:
                logger.warning({
                    "event": "persistence_disabled_no_db_pool",
                    "reason": "db_pool unavailable, fallback to L1 only",
                })
                _conversation_manager = ConversationManager(
                    max_turns=max_turns,
                    max_tokens=max_tokens,
                    compact_length=compact_length,
                )
        else:
            # Story 7.1: Standard ConversationManager (L1 only)
            logger.info({
                "event": "conversation_manager_initialized",
                "persistence_enabled": False,
                "type": "standard",
            })
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


async def flush_pending_writes() -> None:
    """
    Await tutti i pending DB write tasks prima dello shutdown.
    
    CRITICAL per garantire persistenza messaggi durante riavvio Docker.
    Chiamato da lifespan shutdown per graceful shutdown.
    """
    global _conversation_manager
    
    if not _conversation_manager:
        return
    
    # Solo HybridConversationManager ha pending write tasks
    if not isinstance(_conversation_manager, HybridConversationManager):
        return
    
    pending_tasks = _conversation_manager._write_tasks
    if not pending_tasks:
        logger.info({"event": "flush_pending_writes_no_tasks"})
        return
    
    logger.info({
        "event": "flush_pending_writes_started",
        "pending_tasks_count": len(pending_tasks),
    })
    
    # Await all pending tasks con timeout 10s
    try:
        await asyncio.wait_for(
            asyncio.gather(*pending_tasks, return_exceptions=True),
            timeout=10.0
        )
        logger.info({
            "event": "flush_pending_writes_success",
            "flushed_count": len(pending_tasks),
        })
    except asyncio.TimeoutError:
        logger.warning({
            "event": "flush_pending_writes_timeout",
            "pending_count": len(pending_tasks),
        })
    except Exception as exc:
        logger.error({
            "event": "flush_pending_writes_error",
            "error": str(exc),
        })


# ============================================
# Story 9.1: Hybrid Memory Architecture
# ============================================


class CircuitBreakerOpenError(Exception):
    """Raised quando circuit breaker è OPEN e calls vengono rejected."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker pattern per proteggere DB da cascading failures.
    
    Story 9.1 AC2, Task 3.9-3.10: Protegge DB durante overload con
    state machine (CLOSED → OPEN → HALF_OPEN).
    
    States:
    - CLOSED: Normal operation, chiamate passano
    - OPEN: Failures >= threshold, tutte le chiamate fail fast
    - HALF_OPEN: Testing se service recuperato
    
    Transitions:
    - CLOSED → OPEN: failures >= threshold (default 3)
    - OPEN → HALF_OPEN: timeout scaduto (default 30s)
    - HALF_OPEN → CLOSED: chiamata succeeds
    - HALF_OPEN → OPEN: chiamata fails
    """
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 30):
        """
        Inizializza CircuitBreaker.
        
        Args:
            failure_threshold: Failures consecutivi prima OPEN (default 3)
            timeout: Secondi in OPEN state prima HALF_OPEN (default 30)
        """
        self.state = "CLOSED"
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.open_until: Optional[float] = None
    
    async def call(self, func, *args, **kwargs):
        """
        Esegui function attraverso circuit breaker.
        
        Args:
            func: Async function da eseguire
            *args, **kwargs: Arguments per func
        
        Returns:
            Result di func se success
        
        Raises:
            CircuitBreakerOpenError: Se circuit è OPEN
            Exception: Se func raises (e circuit transita a OPEN se threshold)
        """
        if self.state == "OPEN":
            if time.time() < self.open_until:
                # Circuit ancora OPEN, fail fast
                metrics.gauge("circuit_breaker_open", 1)
                raise CircuitBreakerOpenError("Circuit breaker OPEN, failing fast")
            else:
                # Timeout expired, prova HALF_OPEN
                self.state = "HALF_OPEN"
                logger.info({"event": "circuit_breaker_half_open"})
        
        try:
            result = await func(*args, **kwargs)
            
            # Success: reset o close circuit
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
                metrics.gauge("circuit_breaker_open", 0)
                logger.info({"event": "circuit_breaker_closed_after_recovery"})
            
            return result
        
        except Exception as exc:
            self.failures += 1
            logger.error({
                "event": "circuit_breaker_failure",
                "failures": self.failures,
                "threshold": self.failure_threshold,
                "error": str(exc),
            })
            
            # Trip circuit se threshold exceeded
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                self.open_until = time.time() + self.timeout
                metrics.gauge("circuit_breaker_open", 1)
                logger.error({
                    "event": "circuit_breaker_open",
                    "timeout_seconds": self.timeout,
                })
            
            raise


class HybridConversationManager(ConversationManager):
    """
    Hybrid Memory Manager: L1 cache (in-memory) + L2 storage (DB).
    
    Story 9.1 AC1, AC2, AC5: Estende ConversationManager preservando
    backward compatibility, aggiunge async DB persistence con backpressure
    e circuit breaker protection.
    
    Features:
    - Dual-write: sync L1 cache + async L2 DB (non-blocking)
    - Bounded queue: max 100 pending writes (backpressure)
    - Circuit breaker: 3 consecutive failures → OPEN per 30s
    - Graceful degradation: DB failure → L1 only mode
    - Feature flag controlled: ENABLE_PERSISTENT_MEMORY
    """
    
    MAX_PENDING_WRITES = 100  # Backpressure threshold (AC2)
    
    def __init__(
        self,
        persistence_service: Optional[ConversationPersistenceService] = None,
        enable_persistence: bool = False,
        outbox_queue: Optional[OutboxPersistenceQueue] = None,
        max_turns: int = ConversationManager.MAX_TURNS,
        max_tokens: int = ConversationManager.MAX_CONTEXT_TOKENS,
        compact_length: int = ConversationManager.COMPACT_MESSAGE_LENGTH,
    ):
        """
        Inizializza HybridConversationManager.
        
        Args:
            persistence_service: ConversationPersistenceService per DB ops
            enable_persistence: Feature flag per L2 persistence (AC3)
            outbox_queue: OutboxPersistenceQueue per eventual consistency (AC9)
            max_turns: L1 cache max turns (default 3)
            max_tokens: L1 cache token budget (default 2000)
            compact_length: Message compact length (default 150)
        """
        # Init parent L1 cache
        super().__init__(max_turns, max_tokens, compact_length)
        
        self.persistence = persistence_service
        self.persistence_enabled = enable_persistence
        self.outbox_queue = outbox_queue
        self._write_tasks: list[asyncio.Task] = []
        
        # Circuit breaker per DB protection (AC2, Task 3.9)
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)
        
        logger.info({
            "event": "hybrid_conversation_manager_initialized",
            "persistence_enabled": enable_persistence,
            "outbox_enabled": outbox_queue is not None,
            "max_turns": max_turns,
            "max_tokens": max_tokens,
        })
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        chunk_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Aggiunge turno conversazionale con dual-write (L1 + L2).
        
        Story 9.1 AC1, AC2: Override per dual-write pattern:
        1. Sync L1 cache write (fast, blocking <5ms)
        2. Async L2 DB write (non-blocking, fire-and-forget)
        
        Args:
            session_id: Session identifier
            user_message: User message content
            assistant_message: Assistant response
            chunk_ids: Cited chunk IDs (optional)
        
        Notes:
            - L1 cache write sempre succeeds (in-memory)
            - L2 DB write asincrono con backpressure control
            - Backpressure: se queue depth >100, drop oldest task (AC2)
        """
        # L1 cache write (synchronous, fast <5ms)
        super().add_turn(session_id, user_message, assistant_message, chunk_ids)
        
        # L2 DB write (asynchronous, non-blocking)
        if self.persistence_enabled and self.persistence:
            # BACKPRESSURE: Check queue depth (AC2, Task 3.8)
            if len(self._write_tasks) >= self.MAX_PENDING_WRITES:
                logger.warning({
                    "event": "backpressure_activated",
                    "session_id": session_id,
                    "queue_depth": len(self._write_tasks),
                })
                # Drop oldest pending write (sacrifice completeness for availability)
                dropped_task = self._write_tasks.pop(0)
                dropped_task.cancel()
                metrics.increment("backpressure_activated")
            
            # Enqueue async write task
            messages = self._get_messages_for_session(session_id)
            task = asyncio.create_task(self._async_persist(session_id, messages))
            self._write_tasks.append(task)
    
    def _get_messages_for_session(self, session_id: str) -> List[ConversationMessage]:
        """
        Recupera messaggi per session da L1 cache.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Lista ConversationMessage da persistere
        """
        stored_messages = chat_messages_store.get(session_id, [])
        
        messages: List[ConversationMessage] = []
        for msg_dict in stored_messages:
            try:
                role = msg_dict.get("role", "assistant")
                content = msg_dict.get("content", "")
                
                timestamp_str = msg_dict.get("created_at")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except Exception:
                        timestamp = datetime.now(timezone.utc)
                else:
                    timestamp = datetime.now(timezone.utc)
                
                chunk_ids = None
                if role == "assistant":
                    citations = msg_dict.get("citations", [])
                    if citations:
                        chunk_ids = [c.get("chunk_id") for c in citations if c.get("chunk_id")]
                
                messages.append(
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
        
        return messages
    
    async def _async_persist(self, session_id: str, messages: List[ConversationMessage]) -> None:
        """
        Async DB persistence con circuit breaker e error handling.
        
        Story 9.1 AC2, AC6: Background task per L2 DB write con:
        - 5s timeout per singola write
        - Circuit breaker protection (3 failures → OPEN per 30s)
        - Graceful degradation su errors (log + continue)
        
        Args:
            session_id: Session identifier
            messages: Lista messaggi da persistere
        
        Notes:
            - Non-blocking: chiamato async da add_turn()
            - Errors non propagano (logged only)
            - Circuit breaker protegge DB da overload
        """
        try:
            start_time = time.time()
            
            # Call through circuit breaker (AC2, Task 3.10)
            success = await self.circuit_breaker.call(
                asyncio.wait_for,
                self.persistence.save_messages(session_id, messages),
                timeout=5.0,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if success:
                logger.debug({
                    "event": "db_persist_success",
                    "session_id": session_id,
                    "messages_count": len(messages),
                    "latency_ms": f"{latency_ms:.0f}",
                })
                metrics.increment("db_writes_succeeded")
                metrics.histogram("db_write_latency_ms", latency_ms)
            else:
                logger.warning({
                    "event": "db_persist_failed",
                    "session_id": session_id,
                })
                metrics.increment("db_writes_failed")
        
        except CircuitBreakerOpenError:
            logger.warning({
                "event": "db_persist_skipped_circuit_breaker_open",
                "session_id": session_id,
            })
            metrics.increment("db_writes_circuit_breaker_open")
            # Story 9.1 AC9: Fallback to outbox per eventual consistency
            if self.outbox_queue:
                await self.outbox_queue.append(session_id, messages)
        
        except asyncio.TimeoutError:
            logger.error({
                "event": "db_persist_timeout",
                "session_id": session_id,
            })
            metrics.increment("db_writes_timeout")
            # Story 9.1 AC9: Fallback to outbox per eventual consistency
            if self.outbox_queue:
                await self.outbox_queue.append(session_id, messages)
        
        except Exception as exc:
            logger.error({
                "event": "db_persist_error",
                "session_id": session_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            })
            metrics.increment("db_writes_failed")
            # Story 9.1 AC9: Fallback to outbox per eventual consistency
            if self.outbox_queue:
                await self.outbox_queue.append(session_id, messages)
    
    async def load_full_history(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConversationMessage]:
        """
        Load full session history da L2 DB (bypass L1 cache).
        
        Story 9.1 AC1: Query completa DB per accesso storico illimitato.
        
        Args:
            session_id: Session identifier
            limit: Max messaggi per page (default 100)
            offset: Pagination offset
        
        Returns:
            Lista ConversationMessage da DB
        
        Notes:
            - Bypassa L1 cache (accesso diretto L2)
            - Pagination support per large histories
            - Graceful degradation: DB error → return []
        """
        if not self.persistence_enabled or not self.persistence:
            logger.warning({
                "event": "load_full_history_persistence_disabled",
                "session_id": session_id,
            })
            return []
        
        try:
            messages = await self.persistence.load_session_history(
                session_id=session_id,
                limit=limit,
                offset=offset,
                order_desc=False,  # Chronological order
            )
            
            logger.info({
                "event": "load_full_history_success",
                "session_id": session_id,
                "messages_loaded": len(messages),
            })
            
            return messages
        
        except Exception as exc:
            logger.error({
                "event": "load_full_history_error",
                "session_id": session_id,
                "error": str(exc),
            })
            return []
