"""
FeedbackRepository - Data access layer for user feedback persistence.

Story 4.2.4: Migrates feedback storage from in-memory dict to Supabase PostgreSQL,
implementing UPSERT logic for duplicate prevention and admin-only read access via RLS.

Risk Mitigation:
- DATA-001: UPSERT with on_conflict prevents race conditions on duplicate feedback
- SEC-001: RLS policies enforce admin-only SELECT at database level
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from supabase import Client

logger = logging.getLogger("api.repositories")


class FeedbackRepository:
    """
    Repository for feedback data access.
    
    Provides abstraction over Supabase client for feedback CRUD operations,
    with focus on UPSERT logic for idempotency and performance-optimized queries.
    
    Attributes:
        client: Supabase client instance (service_role for RLS bypass on INSERT)
    """
    
    def __init__(self, client: Client):
        """
        Initialize repository with Supabase client.
        
        Args:
            client: Authenticated Supabase client (service_role key)
        """
        self.client = client
        self._table_name = "feedback"
    
    async def create_feedback(
        self,
        session_id: str | UUID,
        message_id: str | UUID,
        vote: str,
        comment: Optional[str] = None,
        user_id: Optional[str | UUID] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update feedback entry with UPSERT logic.
        
        DATA-001 MITIGATION: Uses ON CONFLICT (session_id, message_id) to prevent
        duplicate feedback entries. Second submission updates existing vote/comment.
        
        Args:
            session_id: Chat session identifier
            message_id: Assistant message identifier
            vote: Feedback vote ('up' or 'down')
            comment: Optional user comment
            user_id: Optional authenticated user ID (NULL for anonymous students)
            ip_address: Optional client IP (masked for GDPR)
        
        Returns:
            Created/updated feedback record
        
        Raises:
            Exception: Supabase client errors (logged with context)
        
        Example:
            >>> repo = FeedbackRepository(supabase_client)
            >>> result = await repo.create_feedback(
            ...     session_id="abc-123",
            ...     message_id="msg-456",
            ...     vote="up",
            ...     comment="Great answer!"
            ... )
            >>> result["id"]  # UUID of feedback entry
        """
        try:
            # Convert UUIDs to strings for Supabase
            session_id_str = str(session_id)
            message_id_str = str(message_id)
            user_id_str = str(user_id) if user_id else None
            
            # Validate vote value (CHECK constraint backup)
            if vote not in ("up", "down"):
                raise ValueError(f"Invalid vote value: {vote}. Must be 'up' or 'down'.")
            
            # Prepare payload
            payload = {
                "session_id": session_id_str,
                "message_id": message_id_str,
                "vote": vote,
                "comment": comment,
                "user_id": user_id_str,
                "ip_address": ip_address,
            }
            
            # UPSERT with conflict resolution
            # on_conflict: unique constraint column names (session_id, message_id)
            # If conflict, update vote/comment/updated_at
            response = (
                self.client.table(self._table_name)
                .upsert(
                    payload,
                    on_conflict="session_id,message_id",
                    returning="representation"  # Return full record
                )
                .execute()
            )
            
            # Extract first result (should be single row)
            if response.data and len(response.data) > 0:
                feedback = response.data[0]
                logger.info({
                    "event": "feedback_persisted_db",
                    "feedback_id": feedback.get("id"),
                    "message_id": message_id_str,
                    "vote": vote,
                    "upsert": True  # Always True with this method
                })
                return feedback
            else:
                # Should not reach here with valid upsert
                logger.error({
                    "event": "feedback_upsert_empty_response",
                    "message_id": message_id_str
                })
                raise RuntimeError("Upsert returned empty data")
        
        except ValueError as e:
            # Validation error - don't log as exception
            logger.warning({
                "event": "feedback_validation_error",
                "message_id": str(message_id),
                "error": str(e)
            })
            raise
        
        except Exception as e:
            logger.error({
                "event": "feedback_save_failed",
                "message_id": str(message_id),
                "error": str(e),
                "error_type": type(e).__name__
            }, exc_info=True)
            raise
    
    async def get_feedback_summary(self) -> Dict[str, int]:
        """
        Get aggregated feedback summary (thumbs up/down counts).
        
        Optimized query using database-side aggregation (GROUP BY vote).
        
        Returns:
            Dictionary with keys: thumbs_up, thumbs_down, total
        
        Example:
            >>> repo = FeedbackRepository(supabase_client)
            >>> summary = await repo.get_feedback_summary()
            >>> summary
            {"thumbs_up": 42, "thumbs_down": 3, "total": 45}
        """
        try:
            # Fetch all feedback with vote column only (minimize data transfer)
            response = (
                self.client.table(self._table_name)
                .select("vote")
                .execute()
            )
            
            # Aggregate client-side (Supabase Python client doesn't support GROUP BY directly)
            thumbs_up = 0
            thumbs_down = 0
            
            for record in response.data:
                vote = record.get("vote")
                if vote == "up":
                    thumbs_up += 1
                elif vote == "down":
                    thumbs_down += 1
            
            total = thumbs_up + thumbs_down
            
            logger.debug({
                "event": "feedback_summary_fetched",
                "total": total,
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down
            })
            
            return {
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "total": total
            }
        
        except Exception as e:
            logger.error({
                "event": "feedback_summary_failed",
                "error": str(e)
            }, exc_info=True)
            raise
    
    async def get_feedback_by_timerange(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get feedback entries within a time range for temporal analytics.
        
        Uses idx_feedback_created_at index for performance on date filters.
        
        Args:
            start_date: Start of time range (inclusive)
            end_date: End of time range (inclusive). Defaults to NOW() if None.
        
        Returns:
            List of feedback records matching the time range
        
        Example:
            >>> from datetime import datetime, timedelta
            >>> repo = FeedbackRepository(supabase_client)
            >>> cutoff = datetime.now() - timedelta(days=7)
            >>> feedback_last_week = await repo.get_feedback_by_timerange(cutoff)
            >>> len(feedback_last_week)
            34
        """
        try:
            # Default end_date to now if not provided
            if end_date is None:
                end_date = datetime.now(timezone.utc)
            
            # Convert to ISO-8601 strings for Supabase filter
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            # Query with range filter (uses idx_feedback_created_at)
            response = (
                self.client.table(self._table_name)
                .select("*")
                .gte("created_at", start_iso)  # Greater than or equal
                .lte("created_at", end_iso)    # Less than or equal
                .order("created_at", desc=True)  # Most recent first
                .execute()
            )
            
            logger.debug({
                "event": "feedback_timerange_fetched",
                "start_date": start_iso,
                "end_date": end_iso,
                "count": len(response.data)
            })
            
            return response.data
        
        except Exception as e:
            logger.error({
                "event": "feedback_timerange_failed",
                "start_date": str(start_date),
                "end_date": str(end_date) if end_date else "None",
                "error": str(e)
            }, exc_info=True)
            raise
    
    async def get_feedback_by_session(self, session_id: str | UUID) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific session (used by analytics).
        
        Uses idx_feedback_session_id index for performance.
        
        Args:
            session_id: Session identifier
        
        Returns:
            List of feedback records for the session
        """
        try:
            session_id_str = str(session_id)
            
            response = (
                self.client.table(self._table_name)
                .select("*")
                .eq("session_id", session_id_str)
                .order("created_at", desc=False)  # Chronological order
                .execute()
            )
            
            logger.debug({
                "event": "feedback_by_session_fetched",
                "session_id": session_id_str,
                "count": len(response.data)
            })
            
            return response.data
        
        except Exception as e:
            logger.error({
                "event": "feedback_by_session_failed",
                "session_id": str(session_id),
                "error": str(e)
            }, exc_info=True)
            raise

