import asyncio

from pipecat.frames.frames import TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection

from app.voice.processors.answer_classification import (
    AnswerClassificationProcessor,
)
from app.voice.telephony.answer.models import AnswerType


async def main():
    decisions = []

    processor = AnswerClassificationProcessor(
        on_classification=decisions.append
    )

    texts = [
        "Press 2 for claim status.",
        "Please leave a message after the beep.",
        "Hello, how can I help you?",
    ]

    for text in texts:
        frame = TranscriptionFrame(
            text=text,
            user_id="test",
            timestamp="2026-11-23T00:00:00Z",
        )

        await processor.process_frame(
            frame,
            FrameDirection.DOWNSTREAM,
        )

    assert len(decisions) == 1
    assert decisions[0].answer_type == AnswerType.IVR
    assert processor.initial_answer_locked is True

    print("Initial answer classification lock PASSED")


asyncio.run(main())