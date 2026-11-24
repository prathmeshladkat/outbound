
import re
from dataclasses import dataclass


@dataclass
class IVRDecision:
    is_ivr: bool
    selected_digit: str | None
    reason: str



class IVRDetector:
    CLAIM_KEYWORDS = (
        "claim status",
        "claims status",
        "existing claim",
        "check a claim",
        "claim inquiry",
        "claim inquiries",
        "claims inquiry",
        "claims inquiries",
        "claim enquiries",
    )
    
    DIGIT_WORDS = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
    }

    @classmethod
    def normalize_digits(cls, text: str) -> str:
        for word, digit in cls.DIGIT_WORDS.items():
            text = re.sub(
                rf"\b{word}\b",
                digit,
                text,
                flags=re.IGNORECASE,
            )
        return text

    def detect(self, transcript: str) -> IVRDecision:
        text = self.normalize_digits(
            " ".join(transcript.strip().split())
        )

        digit_first = re.compile(
            r"\b(?:press|select)\s+([0-9])\s+"
            r"(?:for|to)\s+"
            r"(.+?)(?=,|\.|\bor\s+(?:press|select)\b|$)",
            re.IGNORECASE,
        )

        description_first = re.compile(
            r"\b(?:for|to)\s+"
            r"(.+?)\s*,?\s*(?:press|select)\s+([0-9])\b",
            re.IGNORECASE,
        )

        options = digit_first.findall(text)

        options.extend(
            (digit, description)
            for description, digit
            in description_first.findall(text)
        )

        if not options:
            return IVRDecision(
                is_ivr=False,
                selected_digit=None,
                reason="No recognizable IVR options",
            )

        for digit, description in options:
            if any(
                keyword in description.lower()
                for keyword in self.CLAIM_KEYWORDS
            ):
                return IVRDecision(
                    is_ivr=True,
                    selected_digit=digit,
                    reason=f"Matched claim option: {description}",
                )

        for digit, description in options:
            if re.fullmatch(r"(?:insurance |medical |healthcare )?claims?", description.strip().lower()):
                return IVRDecision(True, digit, "Matched general claims option")

        return IVRDecision(
            is_ivr=True,
            selected_digit=None,
            reason="IVR detected, but no claim-status option matched",
        )
