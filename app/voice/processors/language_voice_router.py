import re

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    InterruptionFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    LLMTextFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.processors.frame_processor import (
    FrameDirection,
    FrameProcessor,
)
from pipecat.services.deepgram.tts import DeepgramTTSService


ENGLISH_VOICE = "aura-2-helena-en"
SPANISH_VOICE = "aura-2-sirio-es"


class LanguageVoiceRouter(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.current_voice = ENGLISH_VOICE
        self.pending_frames = []
        self.pending_text = ""
        self.detecting = False

    def reset(self):
        self.pending_frames.clear()
        self.pending_text = ""
        self.detecting = False

    def detect_language(self, text: str) -> str:
        spanish_pattern = (
            r"\b(hola|claro|gracias|puedo|podría|"
            r"necesito|reclamación|número|paciente|"
            r"seguro|español|ayudarle|continuar|"
            r"proporcionar|por favor|con gusto)\b"
        )

        if re.search(spanish_pattern, text, re.IGNORECASE):
            return "es"

        if any(char in text for char in "¿¡"):
            return "es"

        return "en"

    async def flush_pending(self, direction):
        if not self.pending_frames:
            return

        language = self.detect_language(self.pending_text)

        voice = (
            SPANISH_VOICE
            if language == "es"
            else ENGLISH_VOICE
        )

        if voice != self.current_voice:
            logger.info(
                "[LANGUAGE] Switching voice {} -> {}",
                self.current_voice,
                voice,
            )

            await self.push_frame(
                TTSUpdateSettingsFrame(
                    delta=DeepgramTTSService.Settings(
                        voice=voice,
                    )
                ),
                direction,
            )

            self.current_voice = voice

        logger.info(
            "[LANGUAGE] detected={} voice={}",
            language,
            voice,
        )

        for frame in self.pending_frames:
            await self.push_frame(frame, direction)

        self.reset()

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ):
        await super().process_frame(frame, direction)

        if isinstance(frame, InterruptionFrame):
            self.reset()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMFullResponseStartFrame):
            self.reset()
            self.detecting = True
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMTextFrame) and self.detecting:
            self.pending_frames.append(frame)
            self.pending_text += frame.text

            # Wait for enough text to identify the language.
            if (
                len(self.pending_text.strip()) >= 40
                or (
                    len(self.pending_text.strip()) >= 15
                    and re.search(r"[.!?。！？]", self.pending_text)
                )
            ):
                await self.flush_pending(direction)

            return

        if isinstance(frame, LLMFullResponseEndFrame):
            if self.detecting:
                await self.flush_pending(direction)

            await self.push_frame(frame, direction)
            return

        await self.push_frame(frame, direction)