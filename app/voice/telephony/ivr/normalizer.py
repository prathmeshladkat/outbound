import re


class IVRTextNormalizer:
    # Conservative corrections for known STT errors.
    # Only apply them when the phrase occurs inside
    # an IVR option containing a keypad digit.
    CORRECTIONS = {
        "paying status": "claim status",
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        normalized = " ".join(text.lower().split())

        for incorrect, correct in cls.CORRECTIONS.items():
            pattern = (
                r"(\bpress\s+(?:\d|one|two|three|four|five|six|seven|eight|nine)\b"
                r"[^.!?]{0,60})"
            )

            def replace(match):
                segment = match.group(0)

                return re.sub(
                    rf"\b{re.escape(incorrect)}\b",
                    correct,
                    segment,
                    flags=re.IGNORECASE,
                )

            normalized = re.sub(
                pattern,
                replace,
                normalized,
                flags=re.IGNORECASE,
            )
            normalized = re.sub(
                r"\bpress\s+([0-9])\s+claim\s+status\b",
                r"press \1 for claim status",
                normalized,
                flags=re.IGNORECASE,
            )

        return normalized