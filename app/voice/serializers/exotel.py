import base64
import binascii
import json
from loguru import logger
from typing import Callable

from pipecat.frames.frames import Frame, InputAudioRawFrame
from app.voice.telephony.ivr.frames import DTMFOutputFrame
from app.voice.telephony.ivr.dtmf_adapter import ExotelDTMFAdapter

from pipecat.serializers.base_serializer import FrameSerializer

from app.voice.telephony.audio_adapter import TelephonyAudioAdapter
from pipecat.frames.frames import (
    InterruptionFrame,
    OutputAudioRawFrame,
)

from app.voice.telephony.audio_adapter import (
    OutgoingTelephonyAudioAdapter,
)

class ExotelFrameSerializer(FrameSerializer):
    def __init__(
        self,
        on_event: Callable[[str, str | None], None] | None = None,
    ):
        super().__init__()
        self.audio_adapter = TelephonyAudioAdapter()
        self.outgoing_adapter = OutgoingTelephonyAudioAdapter()
        self.stream_sid = None
        self.media_chunks = 0
        self.on_event = on_event

    
    async def serialize(self, frame: Frame):
        if not self.stream_sid:
            return None

        if isinstance(frame, DTMFOutputFrame):
            messages = ExotelDTMFAdapter.build_messages(
                digit=frame.digit,
                stream_sid=self.stream_sid,
                duration_ms=frame.duration_ms,
            )
        
            if len(messages) != 1:
                raise ValueError(
                    "This serializer currently supports "
                    "one DTMF media message per frame"
                )
        
            logger.info(
                "[DTMF] Serialized digit={} stream_sid={} "
                "duration_ms={}",
                frame.digit,
                self.stream_sid,
                frame.duration_ms,
            )
        
            return json.dumps(messages[0])

        if isinstance(frame, InterruptionFrame):
            return json.dumps({
                "event": "clear",
                "stream_sid": self.stream_sid,
            })

        if isinstance(frame, OutputAudioRawFrame):
            if frame.sample_rate != 24000:
                raise ValueError(
                    f"Expected 24000 Hz TTS audio, "
                    f"received {frame.sample_rate} Hz"
                )

            audio_8khz = self.outgoing_adapter.to_8khz(
                frame.audio
            )

            logger.info(
                "[EXOTEL OUTBOUND] Audio serialized "
                "input_bytes={} output_bytes={} stream_sid={}",
                len(frame.audio),
                len(audio_8khz),
                self.stream_sid,
            )

            if not audio_8khz:
                return None

            return json.dumps({
                "event": "media",
                "stream_sid": self.stream_sid,
                "media": {
                    "payload": base64.b64encode(
                        audio_8khz
                    ).decode("ascii")
                },
            })

        return None


    async def deserialize(self, data):
        if not isinstance(data, str):
            return None
        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            return None
        if not isinstance(message, dict):
            return None
        if message.get("event") == "start":
            start = message.get("start") or {}
            self.stream_sid = (
                start.get("stream_sid")
                or message.get("stream_sid")
            )
            logger.info(
                "[EXOTEL SERIALIZER] Stream started: {}",
                self.stream_sid,
            )
            if self.on_event:
                self.on_event("start", self.stream_sid)
            return None
        # --- ADDED: DTMF event handler ---
        if message.get("event") == "dtmf":
            dtmf = message.get("dtmf") or {}
            digit = str(dtmf.get("digit", ""))
            duration = dtmf.get("duration")
            if digit not in "0123456789*#ABCD" or len(digit) != 1:
                logger.warning("[EXOTEL DTMF] Invalid digit")
                return None
            logger.info(
                "[EXOTEL DTMF] Digit={} duration={}ms",
                digit,
                duration,
            )
            if self.on_event:
                self.on_event("dtmf", digit)
            return None
        # --- REPLACED: Updated stop event handler ---
        if message.get("event") == "stop":
            stop = message.get("stop") or {}
            reason = stop.get("reason", "unknown")
            if reason not in ("stopped", "callended"):
                reason = "unknown"
            logger.info(
                "[EXOTEL SERIALIZER] Stream stopped reason={}",
                reason,
            )
            if self.on_event:
                self.on_event("stop", reason)
            return None
        # Keep all non-media events ABOVE this line
        if message.get("event") != "media":
            return None
        media = message.get("media") or {}
        if not isinstance(media, dict):
            return None
        payload = media.get("payload")
        if not isinstance(payload, str):
            return None
        try:
            audio_8khz = base64.b64decode(
                payload,
                validate=True,
            )
            audio_16khz = self.audio_adapter.to_16khz(
                audio_8khz
            )
            self.media_chunks += 1
            if self.media_chunks % 50 == 0:
                logger.info(
                    "[EXOTEL SERIALIZER] Processed {} chunks, "
                    "input={} bytes, output={} bytes",
                    self.media_chunks,
                    len(audio_8khz),
                    len(audio_16khz),
                )
        except (binascii.Error, ValueError):
            return None
        if not audio_16khz:
            return None
        return InputAudioRawFrame(
            audio=audio_16khz,
            sample_rate=16000,
            num_channels=1,
        )