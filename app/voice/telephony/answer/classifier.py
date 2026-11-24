import re

from app.voice.telephony.answer.models import (
    AnswerDecision,
    AnswerType,
)


class AnswerClassifier:
    VOICEMAIL_PATTERNS = [
        r"\bleave (?:a|your) message\b",
        r"\bafter the (?:tone|beep)\b",
        r"\byou(?:'ve| have) reached (?:the )?voicemail\b",
        r"\bmailbox is (?:full|not available)\b",
        r"\brecord your message\b",
    ]

    IVR_PATTERNS = [
        r"\bpress\s+(?:\d|one|two|three|four|five|six|seven|eight|nine)\b",
        r"\bselect (?:an? )?option\b",
        r"\bfor (?:english|hindi),?\s+press\b",
        r"\bmain menu\b",
    ]

    def classify(self, text: str) -> AnswerDecision:
        normalized = " ".join(text.lower().split())

        if not normalized:
            return AnswerDecision(
                AnswerType.UNKNOWN, 0.0, "No transcript"
            )

        for pattern in self.VOICEMAIL_PATTERNS:
            if re.search(pattern, normalized):
                return AnswerDecision(
                    AnswerType.VOICEMAIL,
                    0.9,
                    f"Voicemail phrase matched: {pattern}",
                )

        for pattern in self.IVR_PATTERNS:
            if re.search(pattern, normalized):
                return AnswerDecision(
                    AnswerType.IVR,
                    0.9,
                    f"IVR instruction matched: {pattern}",
                )

        return AnswerDecision(
            AnswerType.UNKNOWN,
            0.0,
            "Insufficient evidence to classify answer",
        )