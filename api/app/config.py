from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/procurement"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    # Use the latest Claude 4.X aliases. Anthropic accepts both alias and pinned-version forms.
    claude_model_default: str = "claude-sonnet-4-6"
    claude_model_synthesis: str = "claude-opus-4-7"
    claude_model_embed: str = "voyage-3"
    voyage_api_key: str = ""

    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Search API (powers Risk Monitor news scanning AND Bid Evaluator price discovery)
    search_provider: str = "brave"        # brave | tavily | exa | serpapi
    search_api_key: str = ""

    # Intratec Primary Commodity Prices — cheap commercial price source ($299-699/yr).
    # Mode "off" = adapter is a no-op; "api" = REST (Advanced tier); "csv" = parse CSV
    # exports dropped into INTRATEC_CSV_DIR (Starter/Pro tier).
    intratec_mode: str = "off"
    intratec_api_key: str = ""
    intratec_api_url: str = ""
    intratec_csv_dir: str = ""

    epa_corpus_dir: str = "./corpus"

    cors_origins: str = "http://localhost:3000"

    @property
    def asyncpg_url(self) -> str:
        # asyncpg uses postgresql+asyncpg scheme
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
