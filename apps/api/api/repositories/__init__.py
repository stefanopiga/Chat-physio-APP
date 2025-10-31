"""
Repository layer for database operations.

This module provides the repository pattern implementation for data access,
abstracting Supabase client interactions.

Story 4.2.4: Feedback persistence migration from in-memory to database.
"""

from .feedback_repository import FeedbackRepository

__all__ = ["FeedbackRepository"]

