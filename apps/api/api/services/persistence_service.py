"""
Conversation Persistence Service (Story 9.1).

Database persistence layer per conversational memory con asyncpg.

Features:
- Bulk insert messaggi con UNNEST SQL pattern
- Idempotency keys per prevenire duplicati
- Pagination per load historical messages
- Graceful error handling con logging strutturato

Reference: docs/architecture/addendum-persistent-conversational-memory.md
"""
import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import asyncpg

from ..models.conversation import ConversationMessage

logger = logging.getLogger("api")


class ConversationPersistenceService:
    """
    Database persistence layer per conversational memory.
    
    Story 9.1 AC1, AC2: Persiste full history illimitato in PostgreSQL,
    con async writes e idempotency per prevenire duplicati.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        """
        Inizializza ConversationPersistenceService.
        
        Args:
            db_pool: asyncpg connection pool per DB operations
        """
        self.db_pool = db_pool
        logger.info({
            "event": "persistence_service_initialized",
            "db_pool_available": db_pool is not None,
        })
    
    async def save_messages(
        self,
        session_id: str,
        messages: List[ConversationMessage],
    ) -> bool:
        """
        Persist messaggi in database con bulk insert.
        
        Story 9.1 AC2: Bulk insert con UNNEST SQL per performance,
        idempotency keys per prevenire duplicati.
        
        Args:
            session_id: Session identifier
            messages: Lista ConversationMessage da persistere
        
        Returns:
            bool: True se successo, False altrimenti
        
        Notes:
            - Usa bulk insert con UNNEST per performance
            - Idempotent: ON CONFLICT (idempotency_key) DO NOTHING
            - Non-blocking: chiamato async da HybridConversationManager
        """
        if not messages:
            logger.debug({
                "event": "save_messages_skip_empty",
                "session_id": session_id,
            })
            return True
        
        try:
            # Prepare data arrays per bulk insert
            ids: List[UUID] = []
            session_ids: List[str] = []
            roles: List[str] = []
            contents: List[str] = []
            source_chunk_ids_list: List[List[UUID]] = []  # Always list, never None
            metadatas: List[dict] = []
            created_ats: List[datetime] = []
            idempotency_keys: List[str] = []
            
            for msg in messages:
                # Generate unique message ID (UUID)
                msg_id = UUID(int=hash(f"{session_id}_{msg.timestamp.isoformat()}_{msg.content[:50]}") & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
                
                # Generate idempotency key per prevenire duplicati
                idempotency_key = self._generate_idempotency_key(
                    session_id=session_id,
                    timestamp=msg.timestamp,
                    content=msg.content,
                )
                
                # Convert chunk_ids string list to UUID list se presenti
                chunk_uuids: List[UUID] = []
                if msg.chunk_ids:
                    try:
                        chunk_uuids = [UUID(cid) for cid in msg.chunk_ids]
                    except (ValueError, TypeError) as exc:
                        logger.warning({
                            "event": "chunk_id_conversion_failed",
                            "session_id": session_id,
                            "error": str(exc),
                            "chunk_ids": msg.chunk_ids,
                        })
                
                ids.append(msg_id)
                session_ids.append(session_id)
                roles.append(msg.role)
                contents.append(msg.content)
                source_chunk_ids_list.append(chunk_uuids)  # Always List[UUID], empty or populated
                metadatas.append({})  # Empty metadata per ora
                created_ats.append(msg.timestamp)
                idempotency_keys.append(idempotency_key)
            
            # Diagnostic logging pre-insert
            logger.debug({
                "event": "save_messages_prepared",
                "session_id": session_id,
                "messages_count": len(messages),
                "source_chunk_ids_types": [
                    {"type": type(scids).__name__, "len": len(scids), "sample": str(scids[0]) if scids else None}
                    for scids in source_chunk_ids_list
                ],
            })
            
            # Row-by-row insert (asyncpg più robusto per uuid[][] typing)
            query = """
                INSERT INTO chat_messages (
                    id, session_id, role, content, source_chunk_ids, metadata, created_at, idempotency_key
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (idempotency_key) DO NOTHING;
            """
            
            inserted_count = 0
            async with self.db_pool.acquire() as conn:
                for i in range(len(ids)):
                    result = await conn.execute(
                        query,
                        ids[i],
                        session_ids[i],
                        roles[i],
                        contents[i],
                        source_chunk_ids_list[i],  # asyncpg converts List[UUID] → uuid[]
                        json.dumps(metadatas[i]),  # Convert dict to JSON string for asyncpg
                        created_ats[i],
                        idempotency_keys[i],
                    )
                    # Count actual inserts (result format: "INSERT 0 <count>")
                    if result and "INSERT" in result:
                        inserted_count += int(result.split()[-1])
            
            logger.info({
                "event": "save_messages_success",
                "session_id": session_id,
                "messages_count": len(messages),
                "inserted_count": inserted_count,
            })
            
            return True
        
        except Exception as exc:
            logger.error({
                "event": "save_messages_error",
                "session_id": session_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }, exc_info=True)
            return False
    
    async def load_session_history(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = False,
    ) -> List[ConversationMessage]:
        """
        Load historical messages per session con pagination.
        
        Story 9.1 AC1: Query DB con INDEX per performance,
        esclude messaggi archived.
        
        Args:
            session_id: Session identifier
            limit: Max messaggi per page (default 100, max 500)
            offset: Pagination offset
            order_desc: Se True, newest first (default: chronological)
        
        Returns:
            Lista ConversationMessage objects
        
        Notes:
            - Usa INDEX idx_chat_messages_session_created
            - Esclude archived: metadata->>'archived' != 'true'
            - Limit max 500 per protezione
        """
        # Enforce limit max 500
        limit = min(limit, 500)
        
        try:
            order_clause = "DESC" if order_desc else "ASC"
            query = f"""
                SELECT id, session_id, role, content, source_chunk_ids, metadata, created_at
                FROM chat_messages
                WHERE session_id = $1
                  AND (metadata->>'archived' IS NULL OR metadata->>'archived' != 'true')
                ORDER BY created_at {order_clause}
                LIMIT $2 OFFSET $3;
            """
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, session_id, limit, offset)
            
            # Convert rows to ConversationMessage
            messages: List[ConversationMessage] = []
            for row in rows:
                # Convert UUID[] to string list per chunk_ids
                chunk_ids = None
                if row["source_chunk_ids"]:
                    chunk_ids = [str(uuid) for uuid in row["source_chunk_ids"]]
                
                messages.append(
                    ConversationMessage(
                        role=row["role"],
                        content=row["content"],
                        timestamp=row["created_at"],
                        chunk_ids=chunk_ids,
                    )
                )
            
            logger.info({
                "event": "load_session_history_success",
                "session_id": session_id,
                "messages_loaded": len(messages),
                "limit": limit,
                "offset": offset,
            })
            
            return messages
        
        except Exception as exc:
            logger.error({
                "event": "load_session_history_error",
                "session_id": session_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }, exc_info=True)
            return []
    
    def _generate_idempotency_key(
        self,
        session_id: str,
        timestamp: datetime,
        content: str,
    ) -> str:
        """
        Genera idempotency key deterministico per prevenire duplicati.
        
        Story 9.1 AC9, Task 1.2: Formula esatta per idempotency.
        
        Formula: sha256(session_id + timestamp_ms + content_hash)
        
        Args:
            session_id: Session identifier
            timestamp: Message timestamp
            content: Message content
        
        Returns:
            Idempotency key (SHA256 hex string)
        
        Notes:
            - Timestamp con milliseconds precision per unicità
            - Content hash per prevenire duplicati identici
            - Deterministico: stesso input → stesso output
        """
        # Timestamp milliseconds precision
        timestamp_ms = int(timestamp.timestamp() * 1000)
        
        # Content hash (SHA256 first 16 chars per brevity)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        
        # Combine components
        combined = f"{session_id}:{timestamp_ms}:{content_hash}"
        
        # Generate SHA256 idempotency key
        idempotency_key = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        
        return idempotency_key

