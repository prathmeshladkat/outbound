from loguru import logger

from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)


class FrameDebugProcessor(FrameProcessor):
    def __init__(self, label: str, **kwargs):
        super().__init__(**kwargs)
        self.label = label

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        frame_name = type(frame).__name__

        if any(
            keyword in frame_name
            for keyword in (
                "Transcription",
                "Speaking",
                "Context",
                "LLM",
                "Error",
            )
        ):
            logger.info(
                "[{}] {} direction={}",
                self.label,
                frame_name,
                direction.name,
            )

        await self.push_frame(frame, direction)