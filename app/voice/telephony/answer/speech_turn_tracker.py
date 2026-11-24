from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class SpeechTurn:
    turn_id: int
    text: str
    duration_seconds: float


class SpeechTurnTracker:
    def __init__(self):
        self.turn_count = 0
        self.speech_active = False
        self.started_at = None
        self.fragments = []

    def on_speech_started(self):
        if self.speech_active:
            return

        self.speech_active = True
        self.started_at = monotonic()
        self.fragments.clear()

    def on_transcript(self, text: str):
        text = text.strip()

        if not text:
            return

        if self.speech_active:
            self.fragments.append(text)

    def on_speech_stopped(self) -> SpeechTurn | None:
        if not self.speech_active:
            return None

        duration = monotonic() - self.started_at
        text = " ".join(self.fragments).strip()

        self.speech_active = False
        self.started_at = None
        self.fragments.clear()

        if not text:
            return None

        self.turn_count += 1

        return SpeechTurn(
            turn_id=self.turn_count,
            text=text,
            duration_seconds=duration,
        )