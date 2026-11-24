from time import monotonic

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    UserStoppedSpeakingFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    LLMTextFrame,
    InterruptionFrame,
)
from pipecat.processors.frame_processor import (
    FrameDirection,
    FrameProcessor,
)


class LatencyMonitor(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.turn_ended_at = None
        self.llm_started_at = None
        self.first_token_at = None

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ):
        await super().process_frame(frame, direction)

        now = monotonic()

        if isinstance(frame, InterruptionFrame):
            self.turn_ended_at = None
            self.llm_started_at = None
            self.first_token_at = None

        elif isinstance(frame, UserStoppedSpeakingFrame):
            self.turn_ended_at = now
            logger.info("[LATENCY] user_turn_ended")

        elif isinstance(frame, LLMFullResponseStartFrame):
            self.llm_started_at = now
            self.first_token_at = None

        elif isinstance(frame, LLMTextFrame):
            if self.first_token_at is None:
                self.first_token_at = now

                if self.turn_ended_at is not None:
                    logger.info(
                        "[LATENCY] turn_end_to_first_token={:.3f}s",
                        now - self.turn_ended_at,
                    )

                if self.llm_started_at is not None:
                    logger.info(
                        "[LATENCY] llm_start_to_first_token={:.3f}s",
                        now - self.llm_started_at,
                    )

        elif isinstance(frame, LLMFullResponseEndFrame):
            if self.llm_started_at is not None:
                logger.info(
                    "[LATENCY] llm_full_response={:.3f}s",
                    now - self.llm_started_at,
                )

            if self.turn_ended_at is not None:
                logger.info(
                    "[LATENCY] turn_end_to_full_response={:.3f}s",
                    now - self.turn_ended_at,
                )

            self.llm_started_at = None
            self.first_token_at = None
            self.turn_ended_at = None

        await self.push_frame(frame, direction)