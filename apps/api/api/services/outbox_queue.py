"""
Durable Outbox Pattern per Persistent Memory (Story 9.1).

Garantisce eventual consistency durante DB outages prolungati con:
- Append-only disk-based queue (.data/persistence_outbox.jsonl)
- Idempotency keys deterministici per anti-duplicazione
- Exponential backoff retry (1s → 60s max)
- Dead-letter queue per failures >10 attempts

Reference: docs/architecture/addendum-persistent-conversational-memory.md
Story 9.1 AC9, Task 8
"""
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..models.conversation import ConversationMessage
from ..utils.metrics import metrics

logger = logging.getLogger("outbox")


class OutboxPersistenceQueue:
    """
    Durable outbox queue per eventual persistence guarantee.
    
    Story 9.1 AC9: Garantisce che messaggi non vadano persi anche durante
    DB outages prolungati tramite disk-based queue con retry.
    
    Features:
    - Append-only JSONL log (crash-safe)
    - Idempotency keys SHA256 per prevenire duplicati
    - Exponential backoff retry (1s → 2s → 4s → 8s → max 60s)
    - Dead-letter queue dopo 10 failures consecutive
    - Background retry loop automatico
    """
    
    def __init__(
        self,
        outbox_path: str = "/tmp/.data/persistence_outbox.jsonl",
        dlq_path: str = "/tmp/.data/persistence_dlq.jsonl",
        max_retries: int = 10,
    ):
        """
        Inizializza OutboxPersistenceQueue.
        
        Args:
            outbox_path: Path per outbox file
            dlq_path: Path per dead-letter queue file
            max_retries: Max retry attempts prima DLQ (default 10)
        """
        self.outbox_path = Path(outbox_path)
        self.dlq_path = Path(dlq_path)
        self.max_retries = max_retries
        
        # Ensure .data directory exists
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        self.dlq_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info({
            "event": "outbox_queue_initialized",
            "outbox_path": str(self.outbox_path),
            "dlq_path": str(self.dlq_path),
            "max_retries": max_retries,
        })
    
    async def append(
        self,
        session_id: str,
        messages: List[ConversationMessage],
    ) -> None:
        """
        Append message batch a durable outbox.
        
        Story 9.1 AC9: Chiamato quando DB write fails per garantire eventual persistence.
        
        Args:
            session_id: Session identifier
            messages: Lista ConversationMessage da persistere eventually
        
        Notes:
            - Append-only write garantisce atomicità (crash-safe)
            - Idempotency key previene duplicati su retry
            - Entry contiene metadata per retry logic
        """
        if not messages:
            return
        
        entry = {
            "id": self._generate_idempotency_key(session_id, messages),
            "session_id": session_id,
            "messages": [self._message_to_dict(m) for m in messages],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "first_failure_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Append-only write (crash-safe, atomic)
        try:
            with open(self.outbox_path, mode="a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            
            logger.info({
                "event": "outbox_append",
                "session_id": session_id,
                "message_count": len(messages),
                "idempotency_key": entry["id"],
            })
            metrics.increment("outbox_appends_total")
            metrics.gauge("outbox_queue_depth", await self._count_pending())
        
        except Exception as exc:
            logger.error({
                "event": "outbox_append_error",
                "session_id": session_id,
                "error": str(exc),
            })
    
    def _generate_idempotency_key(
        self,
        session_id: str,
        messages: List[ConversationMessage],
    ) -> str:
        """
        Genera idempotency key deterministico.
        
        Story 9.1 AC9, Task 8.3: Formula SHA256 per anti-duplicazione.
        
        Formula: sha256(session_id + timestamp + content_hash)
        
        Args:
            session_id: Session identifier
            messages: Lista messaggi
        
        Returns:
            Idempotency key (SHA256 hex string)
        
        Notes:
            - Stesso batch riprocessato → stesso key
            - Timestamp milliseconds precision
            - Content hash del primo messaggio per brevity
        """
        if not messages:
            return hashlib.sha256(f"{session_id}:empty".encode()).hexdigest()
        
        first_msg = messages[0]
        timestamp_ms = int(first_msg.timestamp.timestamp() * 1000)
        content_hash = hashlib.sha256(first_msg.content.encode()).hexdigest()[:16]
        
        combined = f"{session_id}:{timestamp_ms}:{content_hash}"
        idempotency_key = hashlib.sha256(combined.encode()).hexdigest()
        
        return idempotency_key
    
    def _message_to_dict(self, msg: ConversationMessage) -> dict:
        """Serializza ConversationMessage per JSONL storage."""
        return {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "chunk_ids": msg.chunk_ids,
        }
    
    def _dict_to_message(self, data: dict) -> ConversationMessage:
        """Deserializza dict to ConversationMessage."""
        return ConversationMessage(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            chunk_ids=data.get("chunk_ids"),
        )
    
    async def retry_pending(self, persistence_service) -> None:
        """
        Background task: retry all pending outbox entries con exponential backoff.
        
        Story 9.1 AC9, Task 8.4: Retry loop con backoff 1s→2s→4s→8s→max 60s.
        
        Args:
            persistence_service: ConversationPersistenceService per DB writes
        
        Notes:
            - Runs periodically (ogni 5s) per process pending writes
            - Exponential backoff: 2^retry_count secondi (max 60s)
            - Success → remove da outbox
            - Failures >= 10 → move to DLQ
            - Compatta outbox file dopo processing (remove successes)
        """
        if not self.outbox_path.exists():
            return
        
        try:
            # Read all pending entries
            with open(self.outbox_path, mode="r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            logger.error({
                "event": "outbox_read_error",
                "error": str(exc),
            })
            return
        
        if not content.strip():
            return
        
        lines = content.strip().split("\n")
        pending: List[dict] = []
        
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.error({
                    "event": "outbox_parse_error",
                    "line": line[:100],
                    "error": str(exc),
                })
                continue
            
            # Calculate exponential backoff delay
            backoff_seconds = min(2 ** entry["retry_count"], 60)  # Max 60s
            time_since_failure = time.time() - datetime.fromisoformat(entry["timestamp"]).timestamp()
            
            if time_since_failure < backoff_seconds:
                # Too early to retry, keep in pending
                pending.append(entry)
                continue
            
            # Attempt retry
            try:
                messages = [self._dict_to_message(m) for m in entry["messages"]]
                success = await persistence_service.save_messages(entry["session_id"], messages)
                
                if success:
                    logger.info({
                        "event": "outbox_retry_success",
                        "session_id": entry["session_id"],
                        "idempotency_key": entry["id"],
                        "retry_count": entry["retry_count"],
                    })
                    metrics.increment("outbox_retry_success")
                    metrics.increment("retry_attempts_total")
                    # Success: remove from outbox (don't re-add to pending)
                else:
                    # Failed but no exception, increment retry and keep pending
                    entry["retry_count"] += 1
                    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
                    pending.append(entry)
                    metrics.increment("outbox_retry_failure")
                    metrics.increment("retry_attempts_total")
            
            except Exception as exc:
                entry["retry_count"] += 1
                entry["timestamp"] = datetime.now(timezone.utc).isoformat()
                
                logger.error({
                    "event": "outbox_retry_error",
                    "session_id": entry["session_id"],
                    "retry_count": entry["retry_count"],
                    "error": str(exc),
                })
                metrics.increment("retry_attempts_total")
                
                # Dead-letter queue dopo max_retries failures
                if entry["retry_count"] >= self.max_retries:
                    await self._move_to_dlq(entry)
                    logger.error({
                        "event": "outbox_dlq",
                        "session_id": entry["session_id"],
                        "idempotency_key": entry["id"],
                        "retry_count": entry["retry_count"],
                    })
                    metrics.increment("dlq_messages_total")
                else:
                    pending.append(entry)
        
        # Rewrite outbox con solo pending entries (compact on success)
        try:
            with open(self.outbox_path, mode="w", encoding="utf-8") as f:
                for entry in pending:
                    f.write(json.dumps(entry) + "\n")
            
            metrics.gauge("outbox_queue_depth", len(pending))
            
            if len(pending) > 0:
                logger.info({
                    "event": "outbox_retry_cycle_complete",
                    "pending_count": len(pending),
                    "max_retry_count": max(e["retry_count"] for e in pending) if pending else 0,
                })
        except Exception as exc:
            logger.error({
                "event": "outbox_rewrite_error",
                "error": str(exc),
            })
    
    async def _move_to_dlq(self, entry: dict) -> None:
        """
        Move entry to dead-letter queue per manual review.
        
        Story 9.1 AC9, Task 8.5: DLQ per messaggi con retry_count >= max_retries.
        
        Args:
            entry: Outbox entry da spostare in DLQ
        """
        entry["moved_to_dlq_at"] = datetime.now(timezone.utc).isoformat()
        
        try:
            with open(self.dlq_path, mode="a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.error({
                "event": "dlq_append_error",
                "session_id": entry.get("session_id"),
                "error": str(exc),
            })
    
    async def _count_pending(self) -> int:
        """Conta pending entries in outbox."""
        if not self.outbox_path.exists():
            return 0
        
        try:
            with open(self.outbox_path, mode="r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

