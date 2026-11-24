from loguru import logger

from pipecat.frames.frames import (
    Frame,
    TextFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
)
from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)


class LLMResponseLogger(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self.chunks = []

        elif isinstance(frame, TextFrame):
            self.chunks.append(frame.text)

        elif isinstance(frame, LLMFullResponseEndFrame):
            response = "".join(self.chunks).strip()

            if response:
                logger.info("[GEMINI] {}", response)

            self.chunks = []

        await self.push_frame(frame, direction)