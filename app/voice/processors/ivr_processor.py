
from loguru import logger
import asyncio
from typing import Callable
from collections import deque

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
)

from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)

from app.voice.telephony.ivr.detector import IVRDetector
from app.voice.telephony.ivr.state import IVRStateMachine, IVRState
from app.voice.telephony.ivr.normalizer import IVRTextNormalizer

class IVRProcessor(FrameProcessor):
    def __init__(self, on_ivr_result: Callable | None = None, **kwargs):
        super().__init__(**kwargs)

        self.detector = IVRDetector()
        self.machine = IVRStateMachine()
        self.first_transcript_event = asyncio.Event()
        self.on_ivr_result = on_ivr_result
        self.ivr_fragments = deque(maxlen=6)

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ):
        await super().process_frame(frame, direction)
        if (
            direction == FrameDirection.DOWNSTREAM
            and isinstance(
                frame,
                (TranscriptionFrame, InterimTranscriptionFrame),
            )
            and frame.text.strip()
        ):
            self.first_transcript_event.set()

        if (
            direction == FrameDirection.DOWNSTREAM
            and isinstance(frame, TranscriptionFrame)
            and frame.text.strip()
        ):
            if self.machine.state in (IVRState.HUMAN_CONNECTED, IVRState.FAILED):
                await self.push_frame(frame, direction)
                return
            # Keep recent final STT fragments.
            self.ivr_fragments.append(frame.text.strip())

            # Reconstruct instructions split across STT results.
            combined_text = " ".join(self.ivr_fragments)

            logger.debug(
                "[IVR BUFFER] combined={!r}",
                combined_text,
            )

            normalized_text = IVRTextNormalizer.normalize(
                combined_text
            )

            logger.debug(
                "[IVR NORMALIZED] {!r}",
                normalized_text,
            )

            decision = self.detector.detect(normalized_text)

            if decision.is_ivr:
                action = self.machine.process(
                    normalized_text,
                    decision,
                )

                logger.info(
                    "[IVR] transcript={!r} state={} action={} digit={} reason={}",
                    frame.text,
                    self.machine.state.value,
                    action.action,
                    action.digit,
                    action.reason,
                )
                if self.on_ivr_result is not None:
                    self.on_ivr_result(action)

                # Detection-only mode:
                # No DTMF is transmitted here.

        await self.push_frame(frame, direction)
