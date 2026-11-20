from app.config import Settings
from app.services.ai.provider import LLMProvider
from app.services.ai.mindrouter_provider import MindRouterProvider


def get_llm_provider(config: Settings) -> LLMProvider:
    if config.llm_provider == "mindrouter":
        return MindRouterProvider(
            endpoint_url=config.mindrouter_endpoint_url,
            api_key=config.mindrouter_api_key,
            model=config.mindrouter_model,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
