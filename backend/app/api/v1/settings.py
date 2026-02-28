"""Settings API endpoints — read-only configuration info for the frontend."""

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai")
async def get_ai_settings():
    """Return the active LLM provider, model, and endpoint metadata.

    This exposes only the non-secret configuration so the Settings page
    can show which provider is currently in use.
    """
    base = {
        "active_provider": settings.llm_provider,
    }

    if settings.llm_provider == "claude":
        base["active_model"] = settings.claude_model
    elif settings.llm_provider == "openai":
        base["active_model"] = settings.openai_model
    elif settings.llm_provider == "mindrouter":
        base["active_model"] = settings.mindrouter_model
        base["endpoint_url"] = settings.mindrouter_endpoint_url
    else:
        base["active_model"] = "unknown"

    # Expose all available provider configs (no secrets)
    base["providers"] = {
        "claude": {
            "model": settings.claude_model,
            "configured": bool(settings.anthropic_api_key),
        },
        "openai": {
            "model": settings.openai_model,
            "configured": bool(settings.openai_api_key),
        },
        "mindrouter": {
            "model": settings.mindrouter_model,
            "endpoint_url": settings.mindrouter_endpoint_url,
            "configured": bool(settings.mindrouter_api_key),
        },
    }

    return base
