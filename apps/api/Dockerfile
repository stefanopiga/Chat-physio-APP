# ============================================================================
# Multi-stage Dockerfile for FisioRAG API
# Optimized for Story 7.2: Advanced Retrieval with sentence-transformers
# ============================================================================

# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.11-slim-bullseye AS builder

# Build arguments
ARG POETRY_VERSION=1.7.1
ARG POETRY_HOME=/opt/poetry

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=${POETRY_VERSION} \
    POETRY_HOME=${POETRY_HOME} \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true

# Install system dependencies
# - build-essential: for compiling Python packages (torch, numpy)
# - curl: for downloading resources
# - git: for git-based dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s ${POETRY_HOME}/bin/poetry /usr/local/bin/poetry

# Set working directory
WORKDIR /app

# Copy dependency files first (for layer caching)
COPY apps/api/pyproject.toml apps/api/poetry.lock ./

# Story 7.2: Pre-install torch to prevent network timeouts during poetry install
# Using official CPU-only wheel for smaller image size and better stability in CI/CD.
# Story 9.2 Fix: Timeout esteso (600s) + 3 retry per connessioni lente
RUN pip install --timeout=600 --retries=3 torch --index-url https://download.pytorch.org/whl/cpu

# Install dependencies with Poetry
# - --no-root: don't install the project itself (just dependencies)
# - --only main: skip dev dependencies
# Story 9.2 Fix: Configura pip timeout 600s + 3 retry, Poetry max-workers 10
RUN pip config set global.timeout 600 && \
    pip config set global.retries 3 && \
    poetry config installer.max-workers 10 && \
    poetry install --no-root --only main

# ============================================================================
# Stage 2: Runtime - Lightweight production image
# ============================================================================
FROM python:3.11-slim-bullseye AS runtime

# Runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Story 7.2: Feature flags (defaults disabled for safety)
    ENABLE_CROSS_ENCODER_RERANKING=false \
    ENABLE_DYNAMIC_MATCH_COUNT=false \
    ENABLE_CHUNK_DIVERSIFICATION=false

# Install runtime dependencies only
# - libgomp1: required by torch for OpenMP support
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser apps/api/api /app/api

# Create directory for model cache (sentence-transformers)
RUN mkdir -p /app/.cache/torch/sentence_transformers \
    && chown -R appuser:appuser /app/.cache

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck
# - Checks /health endpoint every 30s
# - Timeout 10s, retries 3 times before unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: Uvicorn with production settings
# - workers: 1 (scale with replicas, not workers)
# - worker-class: uvloop for performance
# - access-log: disabled for performance (use reverse proxy logs)
CMD ["uvicorn", "api.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "1", \
    "--loop", "uvloop", \
    "--no-access-log"]

# ============================================================================
# Build & Run Instructions
# ============================================================================
# Build:
#   docker build -t fisio-rag-api:latest -f apps/api/Dockerfile .
#
# Run (development):
#   docker run -p 8000:8000 --env-file .env fisio-rag-api:latest
#
# Run (production with Story 7.2 features):
#   docker run -p 8000:8000 --env-file .env \
#     -e ENABLE_CROSS_ENCODER_RERANKING=true \
#     -e ENABLE_DYNAMIC_MATCH_COUNT=true \
#     fisio-rag-api:latest
#
# Multi-stage benefits:
# - Builder stage: ~1.2GB (includes build tools, Poetry)
# - Runtime stage: ~800MB (only runtime deps, no Poetry)
# - Savings: ~400MB per image
# ============================================================================
