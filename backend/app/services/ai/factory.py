from app.config import Settings
from app.services.ai.provider import LLMProvider
from app.services.ai.claude_provider import ClaudeProvider
from app.services.ai.openai_provider import OpenAIProvider


def get_llm_provider(config: Settings) -> LLMProvider:
    if config.llm_provider == "claude":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=claude")
        return ClaudeProvider(api_key=config.anthropic_api_key, model=config.claude_model)
    elif config.llm_provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAIProvider(api_key=config.openai_api_key, model=config.openai_model)
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
