from pipecat.services.deepgram.tts import DeepgramTTSService

from app.core.config import settings


def create_tts():
    return DeepgramTTSService(
        api_key=settings.deepgram_api_key,
        settings=DeepgramTTSService.Settings(
            voice="aura-2-helena-en",
        ),
    )