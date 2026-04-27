import json
from typing import Any, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


LOCAL_DEV_CORS_ORIGINS = ["http://localhost:5173"]
PRODUCTION_ENVIRONMENTS = {"prod", "production"}


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./ucm_newsletter.db"

    # LLM Provider
    llm_provider: str = "claude"  # "claude", "openai", or "mindrouter"

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # MindRouter (University of Idaho on-prem AI services)
    mindrouter_api_key: str = ""
    mindrouter_endpoint_url: str = "https://mindrouter.uidaho.edu/v1/chat/completions"
    mindrouter_model: str = "openai/gpt-oss-120b"

    # App
    environment: str = "development"
    upload_dir: str = "./uploads"
    cors_origins: str | list[str] | None = None
    trusted_role_header_secret: str = ""
    calendar_source_url: str = (
        "https://www.qatrumba.com/events-calendar/ui/uidaho/vandals/vandal/event/events/calendar/moscow/idaho/id/university-of-idaho"
    )
    calendar_request_timeout_seconds: float = 10.0
    job_postings_source_url: str = "https://uidaho.peopleadmin.com/postings/search"
    job_postings_request_timeout_seconds: float = 10.0
    job_postings_max_pages: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str] | None:
        """Accept comma-separated or JSON-array CORS origin values."""
        if value is None:
            return None

        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return None
            if raw_value.startswith("["):
                try:
                    value = json.loads(raw_value)
                except json.JSONDecodeError as exc:
                    raise ValueError("CORS_ORIGINS must be comma-separated or a JSON array") from exc
            else:
                value = raw_value.split(",")

        if isinstance(value, list):
            origins = [str(origin).strip() for origin in value if str(origin).strip()]
            return origins or None

        raise ValueError("CORS_ORIGINS must be comma-separated or a JSON array")

    @model_validator(mode="after")
    def validate_cors_origins(self) -> Self:
        is_production = self.environment.lower() in PRODUCTION_ENVIRONMENTS

        if self.cors_origins is None:
            if is_production:
                raise ValueError("CORS_ORIGINS must be set when ENVIRONMENT=production")
            self.cors_origins = LOCAL_DEV_CORS_ORIGINS.copy()
            return self

        if is_production and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS cannot include '*' when ENVIRONMENT=production")

        return self


settings = Settings()
