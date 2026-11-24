import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HumanEvidence:
    is_candidate: bool
    score: float
    reason: str


class HumanDetector:
    STRONG_PATTERNS = [
        r"\bwho (?:is|are) (?:this|you)\b",
        r"\bwho'?s (?:this|calling)\b",
        r"\bwhat (?:is|are) (?:this|you) calling (?:about|for)\b",
        r"\bmay i (?:ask|know) who(?:'s| is) calling\b",
    ]

    WEAK_PATTERNS = [
        r"\b(?:how (?:can|may) i (?:help|assist) you|how can i be of assistance)\b",
        r"\byes,?\s+speaking\b",
        r"\bhello,?\s+yes\b",
        r"\bcan you hear me\b",
        r"\bhello\??$",
    ]

    def detect(self, text: str) -> HumanEvidence:
        normalized = " ".join(text.lower().split())

        for pattern in self.STRONG_PATTERNS:
            if re.search(pattern, normalized):
                return HumanEvidence(
                    is_candidate=True,
                    score=0.8,
                    reason="Direct conversational question",
                )

        for pattern in self.WEAK_PATTERNS:
            if re.search(pattern, normalized):
                return HumanEvidence(
                    is_candidate=True,
                    score=0.4,
                    reason="Possible human greeting",
                )

        return HumanEvidence(
            is_candidate=False,
            score=0.0,
            reason="No human-specific conversational evidence",
        )