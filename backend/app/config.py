"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    app_name: str = "B2B Workflow Automation"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/automationdb"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/automationdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "CHANGE-ME-in-production-use-openssl-rand-hex-32"
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"  # Only for initial setup

    # Encryption master key for tenant API keys (Fernet)
    master_encryption_key: str = "CHANGE-ME-generate-with-fernet-generate-key"

    # Local 7B model endpoint (llama.cpp server)
    local_model_url: str = "http://localhost:8081/completion"
    local_model_enabled: bool = False

    # Platform Anthropic key (for testing only)
    platform_anthropic_key: str = ""
    platform_key_mode: bool = False  # If true, use platform key instead of tenant BYOK

    # Safety defaults
    autosend_enabled: bool = False
    default_confidence_threshold: float = 0.85

    # Default tenant limits
    default_max_runs_per_day: int = 500
    default_max_tokens_per_day: int = 500000
    default_max_items_per_minute: int = 10

    # Slack (platform-level fallback)
    slack_webhook_url: str = ""

    # SMTP defaults
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    model_config = {"env_file": ".env", "env_prefix": "BWFA_"}


settings = Settings()
