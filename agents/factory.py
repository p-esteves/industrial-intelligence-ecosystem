import logging
import tenacity
from typing import Any
from config import get_settings

logger = logging.getLogger(__name__)


def get_llm():
    """Instantiates the configured LLM based on environment variables."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    
    if provider == "groq":
        from llama_index.llms.groq import Groq
        logger.info(f"Initializing Groq LLM: {settings.groq_model}")
        return Groq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.1)
    
    elif provider == "gemini":
        from llama_index.llms.google_genai import Gemini
        logger.info(f"Initializing Gemini LLM: {settings.google_model}")
        return Gemini(model=settings.google_model, api_key=settings.google_api_key, temperature=0.1)
    
    elif provider == "claude":
        from llama_index.llms.anthropic import Anthropic
        logger.info(f"Initializing Anthropic Claude LLM: {settings.anthropic_model}")
        return Anthropic(model=settings.anthropic_model, api_key=settings.anthropic_api_key, temperature=0.1)
    
    else:  # Fallback to local Ollama
        from llama_index.llms.ollama import Ollama
        logger.info(f"Initializing Ollama LLM: {settings.ollama_model} at {settings.ollama_base_url}")
        return Ollama(base_url=settings.ollama_base_url, model=settings.ollama_model, temperature=0.1, request_timeout=60.0)


@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    retry=tenacity.retry_if_exception_type(Exception),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def llm_achat_with_retry(llm: Any, messages: list[Any]) -> Any:
    """Execute an async LLM chat call with a tenacity retry policy."""
    logger.info("Executing async LLM chat call with retry policy...")
    return await llm.achat(messages)
