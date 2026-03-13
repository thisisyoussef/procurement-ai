"""Runtime configuration for the external agentic suite."""

from __future__ import annotations

import time
from pathlib import Path

from jose import jwt
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SuiteSettings(BaseSettings):
    """Configuration loaded from environment and CLI overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_base_url: str = Field(default="http://localhost:8000", alias="AGENTIC_API_BASE_URL")
    access_token: str | None = Field(default=None, alias="AGENTIC_ACCESS_TOKEN")

    # Local-dev token signing fallback.
    agentic_app_secret_key: str | None = Field(default=None, alias="AGENTIC_APP_SECRET_KEY")
    app_secret_key: str | None = Field(default=None, alias="APP_SECRET_KEY")
    dev_user_id: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        alias="AGENTIC_DEV_USER_ID",
    )
    dev_user_email: str = Field(default="agentic-suite@local.test", alias="AGENTIC_DEV_USER_EMAIL")

    runs: int = Field(default=5, alias="AGENTIC_RUNS")
    run_timeout_seconds: int = Field(default=900, alias="AGENTIC_RUN_TIMEOUT_SECONDS")
    poll_interval_seconds: float = Field(default=2.0, alias="AGENTIC_POLL_INTERVAL_SECONDS")
    max_restart_attempts: int = Field(default=1, alias="AGENTIC_MAX_RESTART_ATTEMPTS")
    max_clarification_round_trips: int = Field(default=2, alias="AGENTIC_MAX_CLARIFICATION_ROUNDS")
    keep_log_entries: int = Field(default=400, alias="AGENTIC_KEEP_LOG_ENTRIES")

    auto_outreach: bool = Field(default=False, alias="AGENTIC_AUTO_OUTREACH")
    output_root: str = Field(default="agentic_suite_outputs", alias="AGENTIC_OUTPUT_ROOT")
    scenario_file: str | None = Field(default=None, alias="AGENTIC_SCENARIO_FILE")
    dry_run: bool = Field(default=False, alias="AGENTIC_DRY_RUN")

    llm_enabled: bool = Field(default=True, alias="AGENTIC_LLM_ENABLED")
    llm_model: str = Field(default="claude-sonnet-4-5-20250929", alias="AGENTIC_LLM_MODEL")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    request_timeout_seconds: float = Field(default=20.0, alias="AGENTIC_REQUEST_TIMEOUT_SECONDS")

    @property
    def resolved_secret(self) -> str | None:
        return self.agentic_app_secret_key or self.app_secret_key

    @property
    def output_root_path(self) -> Path:
        return Path(self.output_root).expanduser().resolve()

    def validate_runs(self, runs: int) -> int:
        if not 5 <= runs <= 10:
            raise ValueError("runs must be between 5 and 10")
        return runs

    def resolve_access_token(self) -> str | None:
        """Resolve explicit token or generate a local-dev token from APP_SECRET_KEY."""
        if self.access_token:
            return self.access_token

        secret = self.resolved_secret
        if not secret:
            return None

        now = int(time.time())
        payload = {
            "sub": self.dev_user_id,
            "email": self.dev_user_email,
            "name": "Agentic Suite",
            "iat": now,
            "exp": now + (30 * 24 * 3600),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

