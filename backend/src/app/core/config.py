from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central typed config. Every value here is overridable via env vars
    or a .env file — nothing is hardcoded, nothing is read from os.environ
    directly anywhere else in the codebase. This is the single source of
    truth for configuration.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "apprentice-system"
    environment: str = "local"  # local | staging | production
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/apprentice"

    # GitHub
    github_token: str = ""
    github_write_token: str = ""

    # LLM provider (kept provider-neutral — see Phase 4)
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    groq_api_key: str = ""

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "apprentice-system"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton. FastAPI will inject this via Depends(get_settings)
    rather than importing a global — that's what makes it swappable in tests.
    """
    return Settings()
