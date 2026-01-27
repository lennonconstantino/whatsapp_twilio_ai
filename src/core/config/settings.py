"""
Configuration module for the Owner project.
Handles environment variables and application settings.
"""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file immediately
load_dotenv()


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

    model_config = SettingsConfigDict(env_prefix="CONVERSATION_")


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/owner_db",
        description="Database connection URL",
    )

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class SupabaseSettings(BaseSettings):
    """Supabase connection settings."""

    url: str = Field(..., description="Supabase project URL")
    key: str = Field(..., description="Supabase anon key")
    service_key: str | None = Field(
        default=None, description="Supabase service role key"
    )

    model_config = SettingsConfigDict(env_prefix="SUPABASE_")


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

    model_config = SettingsConfigDict(env_prefix="TWILIO_")


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

    model_config = SettingsConfigDict(env_prefix="API_")


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""

    secret_key: str = Field(
        default="change-me-in-production", description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Token expiration time"
    )

    model_config = SettingsConfigDict(env_prefix="")


class LogSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")

    model_config = SettingsConfigDict(env_prefix="LOG_")


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

    model_config = SettingsConfigDict(env_prefix="QUEUE_")


class Settings(BaseSettings):
    """Main application settings."""

    # Sub-settings
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    toggle: ToggleSettings = Field(default_factory=ToggleSettings)
    queue: QueueSettings = Field(default_factory=QueueSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    twilio: TwilioSettings = Field(default_factory=TwilioSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    log: LogSettings = Field(default_factory=LogSettings)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global settings instance
settings = Settings()
