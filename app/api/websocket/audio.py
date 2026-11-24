from fastapi import APIRouter, WebSocket
from loguru import logger

from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)

from app.voice.serializers.pcm import PCMFrameSerializer
from app.voice.pipeline import run_transcription_pipeline

router = APIRouter()


@router.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    await websocket.accept()

    logger.info("Audio WebSocket connected")

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_in_sample_rate=16000,
            audio_in_channels=1,

            audio_out_enabled=True,
            audio_out_sample_rate=24000,
            audio_out_channels=1,

            add_wav_header=False,
            serializer=PCMFrameSerializer(),
        ),
    )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Audio WebSocket disconnected")

    await run_transcription_pipeline(transport)