"""Application configuration via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root and force-load it into os.environ.
# override=True ensures .env values take precedence over any empty
# system env vars that might shadow the key.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    app_title: str = "Tamkin"
    app_version: str = "0.1.0"
    frontend_url: str = "http://localhost:3000"
    cors_allow_origins: str = ""
    cors_allow_origin_regex: str = r"https://.*\.up\.railway\.app"
    project_store_backend: str = "database"
    project_store_fallback_inmemory: bool = True
    auth_jwt_ttl_hours: int = 720
    feature_focus_circle_search_v1: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/procurement"

    # Anthropic
    anthropic_api_key: str = ""

    # LiteLLM
    litellm_master_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # Resend
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    from_email: str = "sourcing@asmbl.app"

    # Retell AI (phone calling)
    retell_api_key: str = ""

    # Gmail (inbox monitoring)
    gmail_credentials_json: str = ""
    gmail_token_json: str = ""

    # Google Places
    google_places_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Firecrawl
    firecrawl_api_key: str = ""

    # Hunter.io (contact enrichment)
    hunter_api_key: str = ""

    # Browserless (website screenshots)
    browserless_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM Model Defaults
    model_cheap: str = "claude-haiku-4-5-20251001"
    model_balanced: str = "claude-sonnet-4-5-20250929"
    model_premium: str = "claude-sonnet-4-5-20250929"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
