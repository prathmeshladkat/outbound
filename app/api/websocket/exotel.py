
import base64
import binascii
import json
from loguru import logger
import asyncio
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.voice.telephony.audio_adapter import TelephonyAudioAdapter
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)

from app.voice.serializers.exotel import ExotelFrameSerializer
from app.voice.pipeline import run_transcription_pipeline
from app.voice.telephony.call_session import (CallSession, CallState)

router = APIRouter()


@router.websocket("/ws/exotel")
async def exotel_websocket(websocket: WebSocket):
    # Development-only endpoint.
    # Add provider authentication before exposing publicly.
    await websocket.accept()

    audio_adapter = TelephonyAudioAdapter()
    converted_audio_bytes = 0

    stream_sid = None
    call_sid = None
    media_chunks = 0
    audio_bytes = 0
    media_format = {}

    logger.info("[EXOTEL] WebSocket connected")

    try:
        while True:
            message = await websocket.receive_text()

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.warning("[EXOTEL] Invalid JSON received")
                continue

            if not isinstance(data, dict):
                logger.warning("[EXOTEL] Expected JSON object")
                continue

            event = data.get("event")

            if event == "connected":
                logger.info("[EXOTEL] Connected event")

            elif event == "start":
                start = data.get("start") or {}

                stream_sid = (
                    start.get("stream_sid")
                    or data.get("stream_sid")
                )
                call_sid = start.get("call_sid")

                media_format = start.get("media_format") or {}

                logger.info(
                    "[EXOTEL] Stream started "
                    "stream_sid={} call_sid={} format={}",
                    stream_sid,
                    call_sid,
                    media_format,
                )

            elif event == "media":
                media = data.get("media") or {}
                payload = media.get("payload")

                if not isinstance(payload, str):
                    logger.warning("[EXOTEL] Missing media payload")
                    continue

                try:
                    audio = base64.b64decode(
                        payload,
                        validate=True,
                    )
                except (binascii.Error, ValueError):
                    logger.warning("[EXOTEL] Invalid base64 audio")
                    continue

                media_chunks += 1
                audio_bytes += len(audio)

                # Only convert streams that declare our test format.
                if (
                    media_format.get("encoding") == "audio/x-raw"
                    and int(media_format.get("sample_rate", 0)) == 8000
                    and int(media_format.get("bit_depth", 0)) == 16
                    and int(media_format.get("channels", 0)) == 1
                ):
                    audio_16khz = audio_adapter.to_16khz(audio)
                    converted_audio_bytes += len(audio_16khz)
                else:
                    logger.warning(
                        "[EXOTEL] Unsupported media format: {}",
                        media_format,
                    )
                    continue

                if media_chunks % 50 == 0:
                    logger.info(
                        "[EXOTEL] Received {} audio chunks, "
                        "{} bytes",
                        media_chunks,
                        audio_bytes,
                    )

                    logger.info(
                        "[EXOTEL] Converted audio bytes={}",
                        converted_audio_bytes,
                    )

                # Next step:
                # Decode/resample telephone audio and
                # forward it into Pipecat.

            elif event == "dtmf":
                dtmf = data.get("dtmf") or {}

                logger.info(
                    "[EXOTEL] DTMF digit={}",
                    dtmf.get("digit"),
                )

            elif event == "mark":
                logger.info(
                    "[EXOTEL] Mark received name={}",
                    (data.get("mark") or {}).get("name"),
                )
                

            elif event == "clear":
                logger.info("[EXOTEL] Clear event received")

            elif event == "stop":
                stop = data.get("stop") or {}

                logger.info(
                    "[EXOTEL] Stream stopped reason={}",
                    stop.get("reason"),
                )
                break

            else:
                logger.warning(
                    "[EXOTEL] Unknown event={}",
                    event,
                )

    except WebSocketDisconnect:
        logger.info("[EXOTEL] WebSocket disconnected")

    except Exception:
        logger.exception("[EXOTEL] WebSocket error")

    finally:
        logger.info(
            "[EXOTEL] Session finished "
            "call_sid={} chunks={} bytes={}",
            call_sid,
            media_chunks,
            audio_bytes,
        )

        try:
            await websocket.close()
        except RuntimeError:
            pass




@router.websocket("/ws/exotel-pipecat-test")
async def exotel_pipecat_test(websocket: WebSocket):
    logger.info("[EXOTEL TEST] Endpoint entered")

    await websocket.accept()

    logger.info("[EXOTEL TEST] WebSocket accepted")

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

            serializer=ExotelFrameSerializer(),
        ),
    )

    logger.info("[EXOTEL TEST] Starting Pipecat")

    await run_transcription_pipeline(transport)

@router.websocket("/ws/exotel-live-probe/{token}")
async def exotel_live_probe(websocket: WebSocket, token: str):
    expected_token = os.environ.get("EXOTEL_PROBE_TOKEN")

    if not expected_token or not secrets.compare_digest(
        token, expected_token
    ):
        logger.warning("[EXOTEL AUTH] Invalid path token")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("[EXOTEL LIVE] WebSocket connected")

    try:
        for _ in range(5):
            message = await asyncio.wait_for(
                websocket.receive(),
                timeout=15,
            )

            if message["type"] == "websocket.disconnect":
                break

            if message.get("text"):
                try:
                    event = json.loads(message["text"])
                    if event.get("event") == "start":
                        start = event.get("start", {})

                        logger.info(
                            "[EXOTEL FORMAT] Media format: {}",
                            start.get("media_format"),
                        )

                    if event.get("event") == "media":
                        media = event.get("media", {})
    
                        logger.info(
                            "[EXOTEL FORMAT] Media keys: {}",
                            list(media.keys()),
                        )
    
                        payload = media.get("payload")
    
                        if payload:
                            import base64
    
                            audio = base64.b64decode(payload)
    
                            logger.info(
                                "[EXOTEL FORMAT] Audio bytes: {}",
                                len(audio),
                            )
                except json.JSONDecodeError:
                    logger.info("[EXOTEL LIVE] Non-JSON text")

            elif message.get("bytes") is not None:
                logger.info(
                    "[EXOTEL LIVE] Binary frame: {} bytes",
                    len(message["bytes"]),
                )

    except (asyncio.TimeoutError, WebSocketDisconnect):
        pass
    finally:
        logger.info("[EXOTEL LIVE] Connection ended")

async def handle_exotel_call(
    websocket: WebSocket,
    token: str,
    call_mode: str,
):
    expected_token = os.environ.get("EXOTEL_PROBE_TOKEN")

    if not expected_token or not secrets.compare_digest(
        token, expected_token
    ):
        logger.warning("[EXOTEL AGENT] Unauthorized connection")
        await websocket.close(code=1008)
        return

    session = CallSession()
    stream_started_event = asyncio.Event()

    def handle_exotel_event(
        event: str,
        value: str | None,
    ):
        if event == "start":
            stream_started_event.set()

            logger.info(
                "[OUTBOUND DEBUG] Stream event SET mode={} "
                "event_is_set={}",
                call_mode,
                stream_started_event.is_set(),
            )

            if session.state == CallState.CONNECTING:
                session.activate()
                

        elif event == "dtmf":
            logger.info(
                "[CALL {}] Key pressed: {}",
                session.session_id,
                value,
            )

        elif event == "stop":
            session.end(f"exotel_{value or 'unknown'}")

            logger.info(
                "[CALL {}] Stream ended reason={}",
                session.session_id,
                session.disconnect_reason,
            )

    logger.info(
        "[CALL {}] Created state={} mode={}",
        session.session_id,
        session.state.value,
        call_mode,
    )

    disconnect_reason = "pipeline_completed"

    try:
        await websocket.accept()
        session.activate()

        logger.info(
            "[CALL {}] Connected state={}",
            session.session_id,
            session.state.value,
        )

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
                serializer=ExotelFrameSerializer(
                    on_event=handle_exotel_event,
                ),
            ),
        )

        logger.info(
            "[CALL {}] Starting Pipecat",
            session.session_id,
        )

        await run_transcription_pipeline(
            transport,
            call_mode="outbound",
            stream_started_event=stream_started_event,
            enable_outbound_voice=True,
        )

    except asyncio.CancelledError:
        disconnect_reason = "task_cancelled"

        logger.warning(
            "[CALL {}] Pipeline task cancelled",
            session.session_id,
        )
        raise

    except WebSocketDisconnect as exc:
        disconnect_reason = f"websocket_disconnect_{exc.code}"

        logger.info(
            "[CALL {}] WebSocket disconnected code={}",
            session.session_id,
            exc.code,
        )

    except Exception:
        disconnect_reason = "pipeline_error"

        logger.exception(
            "[CALL {}] Pipeline failed",
            session.session_id,
        )

    finally:
        session.end(disconnect_reason)

        logger.info(
            "[CALL {}] Ended state={} reason={} duration={:.2f}s",
            session.session_id,
            session.state.value,
            session.disconnect_reason,
            session.duration_seconds,
        )


@router.websocket("/ws/exotel-live/{token}")
async def exotel_live_agent(
    websocket: WebSocket,
    token: str,
):
    await handle_exotel_call(
        websocket,
        token,
        call_mode="inbound",
    )
@router.websocket("/ws/exotel-outbound/{token}")
async def exotel_outbound_agent(
    websocket: WebSocket,
    token: str,
):
    await handle_exotel_call(
        websocket,
        token,
        call_mode="outbound",
    )