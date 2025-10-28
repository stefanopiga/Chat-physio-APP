"""
Routers package - Modular API endpoints organization.

Import tutti i router per facilitare registration in main.py.
"""
from . import auth
from . import student_tokens
from . import admin
from . import chat
from . import knowledge_base
from . import documents
from . import health

__all__ = [
    "auth",
    "student_tokens",
    "admin",
    "chat",
    "knowledge_base",
    "documents",
    "health",
    "monitoring",
]

