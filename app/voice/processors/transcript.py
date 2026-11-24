from loguru import logger

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
)
from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)


class TranscriptProcessor(FrameProcessor):
    def __init__(self, hybrid_controller=None, **kwargs):
        super().__init__(**kwargs)
        self.hybrid_controller = hybrid_controller

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        if isinstance(frame, InterimTranscriptionFrame):
            logger.debug("[INTERIM] {}", frame.text)
            if self.hybrid_controller:
                self.hybrid_controller.on_transcript(frame.text)

        elif isinstance(frame, TranscriptionFrame):
            logger.info("[FINAL] {}", frame.text)
            if self.hybrid_controller:
                self.hybrid_controller.on_transcript(frame.text)

        await self.push_frame(frame, direction)