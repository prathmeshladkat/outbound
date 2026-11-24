from time import monotonic

from loguru import logger
import asyncio


from pipecat.frames.frames import (
    Frame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)


class SpeechActivityMonitor(FrameProcessor):
    def __init__(self, hybrid_controller, energy_processor, on_speech_started=None, on_speech_stopped=None, **kwargs):
        super().__init__(**kwargs)
        self.hybrid = hybrid_controller
        self.energy = energy_processor
        self.first_speech_event = asyncio.Event()
        self.on_speech_started_callback = on_speech_started
        self.on_speech_stopped_callback = on_speech_stopped

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM and isinstance(frame, VADUserStartedSpeakingFrame):
            self.first_speech_event.set()
            self.hybrid.on_speech_started()
            if self.on_speech_started_callback:
                self.on_speech_started_callback()

        elif direction == FrameDirection.DOWNSTREAM and isinstance(frame, VADUserStoppedSpeakingFrame):
            self.hybrid.on_speech_stopped(
                average_rms=self.energy.average_rms
            )
            if self.on_speech_stopped_callback:
                self.on_speech_stopped_callback()

        await self.push_frame(frame, direction)