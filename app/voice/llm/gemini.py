from pipecat.services.google.llm import GoogleLLMService

from app.core.config import settings


def create_llm():
    return GoogleLLMService(
        api_key=settings.gemini_api_key,
        model="gemini-3.5-flash-lite",
    )