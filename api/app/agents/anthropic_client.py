from anthropic import AsyncAnthropic

from app.config import get_settings

_settings = get_settings()


def get_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=_settings.anthropic_api_key)
