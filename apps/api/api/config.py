"""
Configuration management using pydantic-settings.

Centralizza tutte le variabili d'ambiente con validazione e type hints.
Pattern: Singleton con dependency injection.
"""
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, FieldValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("api")

# Story 6.2 Fix: .env path relativo a questo file, non a cwd
# Permette `poetry --directory apps/api` dalla root APPLICAZIONE
# Structure: APPLICAZIONE/.env e APPLICAZIONE/apps/api/api/config.py
_ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"

# Story 6.2 Fix: Load .env esplicitamente per supportare file nascosti Windows
# Path.exists() non vede file hidden, ma load_dotenv() funziona
# Story 6.3 Fix: override=True per dare precedenza a .env su variabili Windows obsolete
load_dotenv(_ENV_FILE, override=True)


class Settings(BaseSettings):
    """Application settings con validazione Pydantic."""

    # Database
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_role_key: str = Field(..., description="Service role key")
    supabase_jwt_secret: str = Field(..., description="JWT signing secret")
    
    # JWT Configuration
    jwt_issuer: str = Field(
        default="https://example.supabase.co/auth/v1",
        description="JWT issuer claim",
        validation_alias=AliasChoices("JWT_ISSUER", "SUPABASE_JWT_ISSUER"),
    )
    temp_jwt_expires_minutes: int = Field(
        default=15, ge=1, le=1440,
        description="Access token duration (minutes)"
    )
    clock_skew_leeway_seconds: int = Field(
        default=120, ge=0, le=300,
        description="Clock skew tolerance (seconds)"
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Optional override for OpenAI API base URL"
    )
    openai_project: Optional[str] = Field(
        default=None,
        description="Optional OpenAI project identifier"
    )
    openai_model: str = Field(
        default="gpt-5-nano",
        description="OpenAI model for generation"
    )
    openai_temperature_chat: Optional[float] = Field(
        default=None,
        description="Chat temperature override; None usa default modello"
    )
    openai_temperature_classification: float = Field(
        default=1.0,
        description="Temperatura classificazione (default 1.0 per stabilita)"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model"
    )
    llm_config_refactor_enabled: bool = Field(
        default=True,
        description="Feature flag per configurazione LLM centralizzata (Story 2.12)"
    )
    
    # Rate Limiting
    exchange_code_rate_limit_window_sec: int = Field(default=60)
    exchange_code_rate_limit_max_requests: int = Field(default=10)
    admin_create_token_rate_limit_window_sec: int = Field(default=3600)
    admin_create_token_rate_limit_max_requests: int = Field(default=10)
    refresh_token_rate_limit_window_sec: int = Field(default=3600)
    refresh_token_rate_limit_max_requests: int = Field(default=60)
    admin_debug_rate_limit_window_hours: int = Field(default=1, ge=1)
    admin_debug_rate_limit_max_requests: int = Field(default=10, ge=1)
    chat_rate_limit_window_sec: int = Field(
        default=60,
        ge=1,
        description="Window size (seconds) for chat message rate limiting",
    )
    chat_rate_limit_max_requests: int = Field(
        default=60,
        ge=1,
        description="Maximum requests per window for chat message rate limiting",
    )
    
    # Application
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Testing environment (Story 5.4)
    testing: bool = Field(
        default=False,
        description="Test environment flag - disables rate limiting"
    )
    
    # Rate Limiting Control (Story 5.4)
    rate_limiting_enabled: bool = Field(
        default=True,
        description="Global rate limiting toggle"
    )
    
    # Celery
    celery_enabled: bool = Field(default=False)
    celery_broker_url: str = Field(default="redis://localhost:6379/0")

    # Classification cache
    classification_cache_enabled: bool = Field(
        default=True,
        description="Toggle for Redis-backed classification cache",
    )
    classification_cache_ttl_seconds: int = Field(
        default=604800,
        ge=60,
        description="TTL for cached classification results (seconds)",
    )
    classification_cache_redis_url: Optional[str] = Field(
        default=None,
        description="Override Redis URL for classification cache (defaults to broker DB+1)",
    )

    # Watcher configuration (Story 6.1)
    watcher_enable_classification: bool = Field(
        default=True,
        description="Feature flag: enable classification inside ingestion watcher",
    )
    classification_timeout_seconds: int = Field(
        default=20,
        ge=1,
        le=60,
        description="Timeout (seconds) for watcher classification stage",
    )
    ingestion_watch_dir: Optional[str] = Field(
        default=None,
        description="Optional override for ingestion watcher source directory",
    )
    ingestion_temp_dir: Optional[str] = Field(
        default=None,
        description="Optional override for ingestion watcher temporary directory",
    )
    
    # Story 7.1: Academic Conversational RAG feature flags
    enable_enhanced_response_model: bool = Field(
        default=False,
        description="Story 7.1: Enable structured academic response model",
    )
    enable_conversational_memory: bool = Field(
        default=False,
        description="Story 7.1: Enable conversational memory (3 turns context window)",
    )
    enable_academic_prompt: bool = Field(
        default=False,
        description="Story 7.1: Enable academic medical prompt (medico fisioterapista persona)",
    )
    
    # Story 7.1: Conversation configuration
    conversation_max_turns: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Story 7.1: Maximum conversation turns to keep in context (default 3 = 6 messages)",
    )
    conversation_max_tokens: int = Field(
        default=2000,
        ge=500,
        le=8000,
        description="Story 7.1: Maximum tokens for conversation context window",
    )
    conversation_message_compact_length: int = Field(
        default=150,
        ge=50,
        le=500,
        description="Story 7.1: Maximum character length for compacted older messages",
    )
    
    # Story 7.2: Advanced Retrieval Optimization feature flags
    enable_cross_encoder_reranking: bool = Field(
        default=False,
        description="Story 7.2 AC1: Enable cross-encoder re-ranking for improved precision",
    )
    enable_dynamic_match_count: bool = Field(
        default=False,
        description="Story 7.2 AC2: Enable dynamic match count based on query complexity",
    )
    enable_chunk_diversification: bool = Field(
        default=False,
        description="Story 7.2 AC3: Enable chunk diversification to reduce document redundancy",
    )
    
    # Story 7.2: Cross-encoder configuration
    cross_encoder_model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Story 7.2 AC1: Cross-encoder model for re-ranking",
    )
    cross_encoder_over_retrieve_factor: int = Field(
        default=3,
        ge=2,
        le=5,
        description="Story 7.2 AC1: Over-retrieval factor for re-ranking (3x = retrieve 3x target count)",
    )
    cross_encoder_threshold_post_rerank: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Story 7.2 AC1: Threshold for filtering after re-ranking",
    )
    
    # Story 7.2: Dynamic retrieval configuration
    dynamic_match_count_min: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Story 7.2 AC2: Minimum match count for simple queries",
    )
    dynamic_match_count_max: int = Field(
        default=12,
        ge=10,
        le=20,
        description="Story 7.2 AC2: Maximum match count for complex queries",
    )
    dynamic_match_count_default: int = Field(
        default=8,
        ge=5,
        le=12,
        description="Story 7.2 AC2: Default match count for normal queries",
    )
    
    # Story 7.2: Diversification configuration
    diversification_max_per_document: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Story 7.2 AC3: Maximum chunks from same document in results",
    )
    diversification_preserve_top_n: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Story 7.2 AC3: Number of top chunks to preserve regardless of diversification",
    )
    
    # Validatori custom
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        if not v.startswith('https://'):
            raise ValueError('SUPABASE_URL must start with https://')
        return v
    
    @field_validator('temp_jwt_expires_minutes')
    @classmethod
    def validate_jwt_expires(cls, v: any) -> int:
        """Ensure JWT expiry è int (evita TypeError in timedelta). Story 5.4 Task 5.2"""
        if isinstance(v, str):
            return int(v)
        return v
    
    @field_validator("openai_model", mode="before")
    @classmethod
    def sanitize_openai_model(cls, value: Optional[str]) -> str:
        """
        Normalizza il nome del modello e fallback al default se non fornito.
        """
        if value is None:
            return "gpt-5-nano"
        if isinstance(value, str):
            sanitized = value.strip()
            if not sanitized:
                logger.warning({
                    "event": "settings_openai_model_defaulted",
                    "reason": "blank_value",
                })
                return "gpt-5-nano"
            return sanitized
        raise TypeError("OPENAI_MODEL must be a string")

    @field_validator(
        "openai_temperature_chat",
        "openai_temperature_classification",
        mode="before",
    )
    @classmethod
    def validate_temperature(
        cls,
        value: Optional[float],
        info: FieldValidationInfo,
    ) -> Optional[float]:
        """
        Valida temperature OpenAI (range 0.0-2.0) con fallback sicuro.
        """
        field_name = info.field_name
        default_value = None if field_name == "openai_temperature_chat" else 1.0

        if value is None:
            return default_value

        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                logger.warning({
                    "event": "settings_temperature_defaulted",
                    "field": field_name,
                    "reason": "blank_value",
                })
                return default_value
            try:
                value = float(stripped)
            except ValueError as exc:
                raise ValueError(
                    f"{field_name} must be a float between 0.0 and 2.0"
                ) from exc

        try:
            temperature = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field_name} must be a float between 0.0 and 2.0"
            ) from exc

        if not 0.0 <= temperature <= 2.0:
            raise ValueError(
                f"{field_name} must be between 0.0 and 2.0 (received {temperature})"
            )

        return temperature

    @field_validator("classification_timeout_seconds")
    @classmethod
    def validate_classification_timeout(
        cls,
        value: int,
        info: FieldValidationInfo,
    ) -> int:
        """
        Log warning if timeout is below recommended threshold per environment.
        """
        environment = str(info.data.get("environment") or "").lower()
        recommended = 10
        if environment in {"development", "dev", "local"}:
            recommended = 20
        elif environment in {"production", "prod"}:
            recommended = 10

        if value < recommended:
            logger.warning(
                {
                    "event": "classification_timeout_below_recommended",
                    "environment": environment or "unknown",
                    "configured_timeout_seconds": value,
                    "minimum_recommended_seconds": recommended,
                }
            )

        return value

    @property
    def should_enable_rate_limiting(self) -> bool:
        """
        Rate limiting attivo solo in non-test environment.
        
        Story 5.4 Task 1.1
        Returns:
            bool: True se rate limiting deve essere attivo
        """
        return self.rate_limiting_enabled and not self.testing
    
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Dependency per ottenere settings (singleton pattern).
    
    Usage in FastAPI:
        settings: Annotated[Settings, Depends(get_settings)]
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """
    Reset settings cache per testing.
    
    Story 6.2 Task T7: Utility per test che modificano env vars.
    """
    global _settings
    _settings = None