from enum import StrEnum

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class ModelTier(StrEnum):
    """Task complexity tiers, not specific models. Every call site in the
    codebase asks for a TIER — never a hardcoded model name or provider.
    That's what makes swapping providers/models a one-line change here,
    instead of a hunt through the codebase.
    """

    FREE = "free"  # zero-cost dev/testing via Groq — rate-limited,
    # open-source models only, not for judging real quality
    FAST = "fast"  # cheap/quick judgment calls via OpenRouter
    CAPABLE = "capable"  # deeper reasoning via OpenRouter — costs real money


# Update these against each provider's live model list before relying on
# them — availability and naming both change over time.
TIER_MODELS: dict[ModelTier, str] = {
    ModelTier.FREE: "openai/gpt-oss-120b",
    ModelTier.FAST: "z-ai/glm-5.2",
    ModelTier.CAPABLE: "moonshotai/kimi-k2.7-code",
}


def get_llm(tier: ModelTier, max_tokens: int = 1024) -> ChatOpenAI:
    settings = get_settings()
    model_name = TIER_MODELS[tier]

    if tier == ModelTier.FREE:
        return ChatOpenAI(
            model=model_name,
            api_key=SecretStr(settings.groq_api_key),
            base_url=GROQ_BASE_URL,
            max_completion_tokens=max_tokens,
        )

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(settings.openrouter_api_key),
        base_url=OPENROUTER_BASE_URL,
        max_completion_tokens=max_tokens,
    )
