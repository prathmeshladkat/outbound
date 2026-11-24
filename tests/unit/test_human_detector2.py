import asyncio

from pipecat.frames.frames import TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection

from app.voice.processors.answer_classification import (
    AnswerClassificationProcessor,
)
from app.voice.telephony.answer.models import AnswerType


async def test_candidate_tracking():
    decisions = []

    processor = AnswerClassificationProcessor(
        on_classification=decisions.append
    )

    for text in [
        "Hello?",
        "Who is this?",
    ]:
        frame = TranscriptionFrame(
            text=text,
            user_id="test",
            timestamp="2026-11-23T00:00:00Z",
        )

        await processor.process_frame(
            frame,
            FrameDirection.DOWNSTREAM,
        )

    assert processor.human_candidate_count == 2
    assert processor.human_candidate_score == 0.8

    # Human candidates must not trigger final classification yet.
    assert processor.current_type == AnswerType.UNKNOWN
    assert decisions == []

    print("Phase 1E.2 candidate tracking PASSED")


asyncio.run(test_candidate_tracking())