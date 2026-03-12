from pydantic_settings import BaseSettings


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
    upload_dir: str = "./uploads"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
