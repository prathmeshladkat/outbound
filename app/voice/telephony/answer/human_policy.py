"""Conservative evidence policy; no voice output is triggered by this module."""
import re
from app.voice.telephony.answer.classifier import AnswerClassifier
from app.voice.telephony.answer.human_detector import HumanDetector
from app.voice.telephony.answer.models import AnswerType

class HumanConfirmationPolicy:
    def __init__(self):
        self.classifier = AnswerClassifier()
        self.detector = HumanDetector()
        self.human_turns = 0
        self.strong_turns = 0
        self.confirmed = False
        self.initial_answer = AnswerType.UNKNOWN
        self.probe_sent = False

    def set_initial_answer(self, answer_type: AnswerType):
        self.initial_answer = answer_type

    def mark_probe_sent(self):
        self.probe_sent = True

    @staticmethod
    def is_short_greeting(text: str) -> bool:
        normalized = re.sub(r"[^a-z ]", "", text.lower()).strip()
        return normalized in {"hello", "hi", "hey", "hello there", "good morning", "good afternoon"}

    @staticmethod
    def is_probe_response(text: str) -> bool:
        normalized = " ".join(text.lower().split())
        # Replies to the explicit question "Am I speaking with a representative?"
        # Require more than an isolated yes/no to avoid false positives.
        return bool(re.search(
            r"\b(?:yes|yeah|yep|sure|correct|right)[,.! ]+(?:i(?:'m| am)\s+speaking|this is|speaking|how can i help)\b"
            r"|\b(?:i(?:'m| am)\s+speaking|this is\s+[a-z]+\s+speaking|you are speaking with)\b"
            r"|\b(?:how (?:can|may) i (?:help|assist) you)\b"
            r"|\b(?:what is this|what(?:'s| is) this about|who is this|why are you calling)\b",
            normalized,
        ))

    def consider(self, text: str) -> bool:
        if self.confirmed or self.initial_answer == AnswerType.VOICEMAIL:
            return False
        # Exclude prompts even if they include conversational-sounding phrases.
        if self.classifier.classify(text).answer_type != AnswerType.UNKNOWN:
            return False
        evidence = self.detector.detect(text)
        probe_reply = self.probe_sent and self.is_probe_response(text)
        if not evidence.is_candidate and not probe_reply:
            return False
        self.human_turns += 1
        if evidence.score >= 0.8 or probe_reply:
            self.strong_turns += 1
        # Conservative heuristic, NOT proof of a live human.
        if (self.human_turns >= 2 and self.strong_turns >= 1) or (self.probe_sent and self.strong_turns >= 1):
            self.confirmed = True
            return True
        return False
