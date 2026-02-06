"""
Configuration module for the Owner project.
Handles environment variables and application settings.
"""

from pydantic import Field, field_validator, model_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConversationSettings(BaseSettings):
    """Conversation-specific settings."""

    expiration_minutes: int = Field(
        default=1440,  # 24 hours
        description="Minutes until a conversation in PROGRESS expires (Standard: 24h/1440m)",
    )
    pending_expiration_minutes: int = Field(
        default=2880,  # 48 hours
        description="Minutes until a conversation in PENDING expires (Standard: 48h/2880m)",
    )
    idle_timeout_minutes: int = Field(
        default=15,
        description="Minutes of inactivity before idle timeout (Standard: 10-15m)",
    )
    min_conversation_duration: int = Field(
        default=30, description="Minimum duration in seconds before allowing closure"
    )
    closure_keywords: list[str] = Field(
        default=[
            "tchau",
            "obrigado",
            "valeu",
            "até logo",
            "até mais",
            "até breve",
            "bye",
            "thanks",
            "adeus",
            "flw",
        ],
        description="Keywords that indicate conversation closure",
    )

    model_config = SettingsConfigDict(
        env_prefix="CONVERSATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    backend: str = Field(
        default="supabase",
        description="Database backend (supabase, postgres)",
    )
    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/owner_db",
        description="Database connection URL",
    )
    pool_min_conn: int = Field(
        default=1,
        description="Postgres pool minimum connections (used when backend=postgres)",
    )
    pool_max_conn: int = Field(
        default=10,
        description="Postgres pool maximum connections (used when backend=postgres)",
    )

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class SupabaseSettings(BaseSettings):
    """Supabase connection settings."""

    url: str | None = Field(default=None, description="Supabase project URL")
    key: str | None = Field(default=None, description="Supabase anon key")
    service_key: str | None = Field(
        default=None, 
        description="Supabase service role key",
        validation_alias=AliasChoices("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    )
    db_schema: str = Field(
        default="public", description="Default database schema (e.g. public, app)"
    )
    project_ref: str | None = Field(default=None, description="Supabase project reference")
    access_token: str | None = Field(default=None, description="Supabase access token")

    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class TwilioSettings(BaseSettings):
    """Default Twilio settings (can be overridden per owner)."""

    account_sid: str | None = Field(default=None, description="Twilio Account SID")
    auth_token: str | None = Field(default=None, description="Twilio Auth Token")
    phone_number: str | None = Field(
        default=None, description="Default Twilio phone number"
    )
    internal_api_key: str | None = Field(
        default=None, description="Internal API key for sender.py and internal services"
    )

    model_config = SettingsConfigDict(
        env_prefix="TWILIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class APISettings(BaseSettings):
    """API server settings."""

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    use_fake_sender: bool = Field(
        default=False, description="Use fake sender in development environment"
    )
    bypass_subscription_check: bool = Field(
        default=False,
        description="Bypass subscription validation (Development only)",
    )

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""

    secret_key: str = Field(
        default="change-me-in-production", description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Token expiration time"
    )

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # We can't easily access other settings here (like api.environment) 
        # because SecuritySettings is nested.
        # But we can check if it is the default value.
        # Ideally we check environment, but BaseSettings validation is per-model.
        # We will do a check in the main Settings validator or just warn here.
        # However, for now, let's just allow it but we will add a check in main Settings.
        return v



class LogSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class WhisperSettings(BaseSettings):
    """Whisper transcription settings."""

    size: str = Field(
        default="base",
        description="Model size (tiny, base, small, medium, large-v3). Use 'medium' or 'large-v3' for better accuracy.",
    )
    device: str = Field(
        default="cpu",
        description="Device to use (cpu, cuda, auto). Use 'cuda' or 'auto' for GPU acceleration.",
    )
    compute_type: str = Field(
        default="int8",
        description="Compute type (int8, float16, int8_float16). Use 'float16' for GPU.",
    )
    beam_size: int = Field(
        default=5,
        description="Beam size for decoding. Higher values improve accuracy but slow down transcription.",
    )

    model_config = SettingsConfigDict(
        env_prefix="WHISPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class ToggleSettings(BaseSettings):
    """Toggle settings."""

    enable_background_tasks: bool = Field(
        default=True, description="Enable background tasks worker"
    )


class QueueSettings(BaseSettings):
    """Queue configuration."""

    backend: str = Field(
        default="sqlite", description="Queue backend type (sqlite, redis, sqs)"
    )
    sqlite_db_path: str = Field(
        default="queue.db", description="Path to Sqlite database file for queue"
    )
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL for BullMQ"
    )
    # AWS SQS Settings
    sqs_queue_url: str | None = Field(default=None, description="AWS SQS Queue URL")
    aws_region: str = Field(default="us-east-1", description="AWS Region")
    aws_access_key_id: str | None = Field(default=None, description="AWS Access Key ID")
    aws_secret_access_key: str | None = Field(
        default=None, description="AWS Secret Access Key"
    )

    model_config = SettingsConfigDict(
        env_prefix="QUEUE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

class LLMModelSettings(BaseSettings):
    """LLM model settings."""

    provider: str = Field(default="ollama", description="LLM provider")
    model_name: str = Field(default="gpt-oss:20b", description="LLM model name")

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        protected_namespaces=('settings_',),
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    

class EmbeddingSettings(BaseSettings):
    """Embedding settings."""

    provider: str = Field(
        default="openai", description="Embedding provider (openai, ollama)"
    )
    model_name: str = Field(
        default="text-embedding-3-small", description="Embedding model name"
    )
    dimensions: int = Field(default=1536, description="Embedding dimensions")

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class MemorySettings(BaseSettings):
    recent_messages_limit: int = Field(
        default=10,
        description="Quantidade de mensagens recentes (L1/L2) incluídas no contexto",
    )
    redis_max_messages: int = Field(
        default=50,
        description="Quantidade máxima de mensagens armazenadas por sessão no Redis (L1)",
    )
    redis_ttl_seconds: int = Field(
        default=3600,
        description="TTL de chaves de memória no Redis (L1), em segundos",
    )
    redis_reconnect_backoff_seconds: int = Field(
        default=30,
        description="Tempo mínimo entre tentativas de reconexão do Redis após falha",
    )
    semantic_top_k: int = Field(
        default=100,
        description="Quantidade de resultados semânticos (L3) inseridos no contexto",
    )
    semantic_match_threshold: float = Field(
        default=0.0,
        description="Threshold mínimo de similaridade (0-1) para busca vetorial (L3)",
    )
    enable_hybrid_retrieval: bool = Field(
        default=True,
        description="Habilita recuperação híbrida (FTS + vetor + RRF) no L3",
    )
    hybrid_weight_vector: float = Field(
        default=1.5,
        description="Peso do componente vetorial na fusão RRF",
    )
    hybrid_weight_text: float = Field(
        default=1.0,
        description="Peso do componente textual (FTS) na fusão RRF",
    )
    hybrid_rrf_k: int = Field(
        default=60,
        description="Constante K do RRF (estabiliza impacto dos ranks)",
    )
    fts_language: str = Field(
        default="portuguese",
        description="Config de linguagem do Postgres para FTS (ex: portuguese, simple)",
    )

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class OTELSettings(BaseSettings):
    """OpenTelemetry settings."""
    exporter_otlp_endpoint: str | None = Field(default=None, description="OTLP Exporter Endpoint")
    service_name: str = Field(default="owner-api", description="Service Name")
    resource_attributes: str | None = Field(default=None, description="Resource Attributes")

    model_config = SettingsConfigDict(
        env_prefix="OTEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class AISettings(BaseSettings):
    """AI configuration."""

    log_retention_days: int = Field(
        default=30, description="Days to retain AI logs (thoughts/results)"
    )

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class StripeSettings(BaseSettings):
    """Stripe payment settings."""
    
    api_key: str | None = Field(default=None, description="Stripe Secret API Key")
    webhook_secret: str | None = Field(default=None, description="Stripe Webhook Secret")
    publishable_key: str | None = Field(default=None, description="Stripe Publishable Key")
    
    model_config = SettingsConfigDict(
        env_prefix="STRIPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )



class Settings(BaseSettings):
    """Main application settings."""

    # Sub-settings
    otel: OTELSettings = Field(default_factory=OTELSettings)
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    toggle: ToggleSettings = Field(default_factory=ToggleSettings)
    queue: QueueSettings = Field(default_factory=QueueSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    twilio: TwilioSettings = Field(default_factory=TwilioSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    log: LogSettings = Field(default_factory=LogSettings)
    whisper: WhisperSettings = Field(default_factory=WhisperSettings)
    llm_model: LLMModelSettings = Field(default_factory=LLMModelSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    ai: AISettings = Field(default_factory=AISettings)
    stripe: StripeSettings = Field(default_factory=StripeSettings)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("security")
    @classmethod
    def validate_security(cls, v: SecuritySettings, info) -> SecuritySettings:
        # Access 'api' settings is hard here because validation order.
        # But we can check environment variable directly or assume defaults.
        # A better approach is to check this in the root validator or __init__.
        # For simplicity and robustness, we will check against the default value
        # and raise error if we are likely in production (heuristic or explicit env check).
        
        # We can't access 'api.environment' easily inside a field validator for 'security'
        # if 'api' hasn't been validated yet or isn't passed to this validator.
        # So we'll use a model_validator for the whole Settings class.
        return v

    @model_validator(mode="after")
    def check_production_security(self) -> "Settings":
        if self.api.environment == "production":
            if self.security.secret_key == "change-me-in-production":
                raise ValueError(
                    "CRITICAL: SECRET_KEY must be changed in production environment!"
                )
        return self


# Global settings instance
settings = Settings()
