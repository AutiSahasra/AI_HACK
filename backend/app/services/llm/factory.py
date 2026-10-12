import logging
from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAICompatibleProvider
from app.services.llm.anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)

def get_llm_provider() -> LLMProvider:
    provider_name = (settings.LLM_PROVIDER or "mock").strip().lower()

    if provider_name == "anthropic" and settings.ANTHROPIC_API_KEY:
        logger.info("Using Anthropic LLM Provider")
        return AnthropicProvider()
    elif provider_name in ("openai", "openai_compatible") and settings.OPENAI_API_KEY:
        logger.info("Using OpenAI LLM Provider")
        return OpenAICompatibleProvider()
    else:
        logger.info(f"Using Mock LLM Provider (configured: '{provider_name}')")
        return MockProvider()
