from collections import deque
from typing import Callable

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)
from app.voice.telephony.answer.human_detector import HumanDetector

from app.voice.telephony.answer.classifier import AnswerClassifier
from app.voice.telephony.answer.models import (
    AnswerType,
    AnswerDecision,
)


class AnswerClassificationProcessor(FrameProcessor):
    def __init__(
        self,
        on_classification: Callable | None = None,
        on_final_transcript: Callable | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.classifier = AnswerClassifier()
        self.on_classification = on_classification
        self.on_final_transcript = on_final_transcript

        self.fragments = deque(maxlen=8)
        self.current_type = AnswerType.UNKNOWN
        self.initial_answer_locked = False
        self.human_detector = HumanDetector()
        self.human_candidate_score = 0.0
        self.human_candidate_count = 0

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ):
        await super().process_frame(frame, direction)

        if (
            direction == FrameDirection.DOWNSTREAM
            and isinstance(frame, TranscriptionFrame)
            and frame.text.strip()
        ):
            if self.on_final_transcript:
                self.on_final_transcript(frame.text)

            # Track human evidence only while initial answer is unknown.
            if not self.initial_answer_locked:
                evidence = self.human_detector.detect(frame.text)
            
                if evidence.is_candidate:
                    self.human_candidate_count += 1
            
                    # Keep the strongest evidence observed so far.
                    self.human_candidate_score = max(
                        self.human_candidate_score,
                        evidence.score,
                    )
            
                    logger.info(
                        "[HUMAN CANDIDATE] score={} count={} reason={}",
                        evidence.score,
                        self.human_candidate_count,
                        evidence.reason,
                    )        
            if not self.initial_answer_locked:
                self.fragments.append(frame.text.strip())

                combined_text = " ".join(self.fragments)
                decision = self.classifier.classify(combined_text)

                if decision.answer_type != AnswerType.UNKNOWN:
                    previous_type = self.current_type
                    self.current_type = decision.answer_type
                    self.initial_answer_locked = True

                    logger.info(
                        "[ANSWER] {} -> {} reason={}",
                        previous_type.value,
                        decision.answer_type.value,
                        decision.reason,
                    )

                    if self.on_classification:
                        self.on_classification(decision)

            

        await self.push_frame(frame, direction)