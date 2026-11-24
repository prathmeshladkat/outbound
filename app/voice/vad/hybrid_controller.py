from time import monotonic
from loguru import logger


class HybridVADController:
    def __init__(
        self,
        min_speech_duration: float = 0.25,
        min_rms: float = 0.01,
    ):
        self.min_speech_duration = min_speech_duration
        self.min_rms = min_rms

        self.speech_started_at = None
        self.transcript_detected = False

    def on_speech_started(self):
        self.speech_started_at = monotonic()
        self.transcript_detected = False
        logger.info("[HYBRID] speech_started")

    def on_transcript(self, text: str):
        if text.strip():
            self.transcript_detected = True

    def on_speech_stopped(self, average_rms: float):
        if self.speech_started_at is None:
            return

        duration = monotonic() - self.speech_started_at

        confirmed = (
            duration >= self.min_speech_duration
            and (
                average_rms >= self.min_rms
                or self.transcript_detected
            )
        )

        if confirmed:
            logger.info(
                "[HYBRID] speech_confirmed duration={:.2f}s rms={:.4f}",
                duration,
                average_rms,
            )
        else:
            logger.info(
                "[HYBRID] short_speech duration={:.2f}s rms={:.4f}",
                duration,
                average_rms,
            )

        self.speech_started_at = None
        self.transcript_detected = False