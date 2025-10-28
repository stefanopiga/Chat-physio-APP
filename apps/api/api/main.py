﻿"""
FisioRAG API - FastAPI application entry point.

Refactored: Story 5.2 - FastAPI Modularization & Architecture Refactoring

Architecture:
- Modular routers per dominio funzionale
- Service layer per business logic
- Schema layer per Pydantic models
- Dependency injection pattern
"""
import os
import logging
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .database import lifespan
from .middleware import log_requests, add_request_id
from .utils.logging import setup_logging
from .config import get_settings

# Import routers
from .routers import (
    auth,
    student_tokens,
    admin,
    chat,
    knowledge_base,
    documents,
    health as health_router,
    monitoring,
)

# -------------------------------
# Environment & Logging Setup
# -------------------------------
load_dotenv()
setup_logging()
logger = logging.getLogger("api")
settings = get_settings()  # Story 5.4 Task 1.2

# -------------------------------
# FastAPI Application
# -------------------------------
app = FastAPI(
    lifespan=lifespan,
    title="FisioRAG API",
    version="2.0.0",
    description="Retrieval-Augmented Generation system for physiotherapy knowledge base"
)

# -------------------------------
# Middleware Configuration
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ristretto in produzione
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests)
app.middleware("http")(add_request_id)

# -------------------------------
# Rate Limiting (SlowAPI) - Story 5.4 Task 1.2
# -------------------------------
if settings.should_enable_rate_limiting:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting ENABLED")
else:
    logger.warning("Rate limiting DISABLED (test environment)")

# -------------------------------
# Router Registration
# -------------------------------
app.include_router(auth.router)
app.include_router(student_tokens.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(knowledge_base.router_classify)  # /classify root-level (Story 5.3)
app.include_router(knowledge_base.router)           # /api/v1/knowledge-base/*
app.include_router(documents.router)
app.include_router(health_router.router)
app.include_router(monitoring.router)


# -------------------------------
# Startup Log
# -------------------------------
logger.info({
    "event": "app_started",
    "version": "2.0.0",
    "architecture": "modular (Story 5.2)",
    "routers": [
        "auth",
        "student_tokens",
        "admin",
        "chat",
        "knowledge_base",
        "documents"
    ]
})
