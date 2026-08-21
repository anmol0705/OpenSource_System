from enum import StrEnum

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class ModelTier(StrEnum):
    """Task complexity tiers, not specific models. Every call site in the
    codebase asks for a TIER ("I need FAST" or "I need CAPABLE") — never
    a hardcoded model name. That's what makes swapping providers/models
    later a one-line change here, instead of a hunt through the codebase.
    """

    FAST = "fast"  # cheap/quick judgment calls — "is this file relevant?"
    CAPABLE = "capable"  # deeper reasoning — hypothesis formation, code review


# Update these slugs against OpenRouter's live model list before relying
# on them — model names/availability change over time.
TIER_MODELS: dict[ModelTier, str] = {
    ModelTier.FAST: "z-ai/glm-5.2",
    ModelTier.CAPABLE: "moonshotai/kimi-k2.7-code",
}


def get_llm(tier: ModelTier, max_tokens: int = 1024) -> ChatOpenAI:
    settings = get_settings()
    model_name = TIER_MODELS[tier]

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(settings.openrouter_api_key),
        base_url=OPENROUTER_BASE_URL,
        max_completion_tokens=max_tokens,
    )
