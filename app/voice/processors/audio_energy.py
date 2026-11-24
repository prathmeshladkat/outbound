import audioop
from collections import deque
from time import monotonic

from pipecat.frames.frames import Frame, InputAudioRawFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection


class AudioEnergyProcessor(FrameProcessor):
    def __init__(self, window_size: int = 20, **kwargs):
        super().__init__(**kwargs)
        self.rms_values = deque(maxlen=window_size)
        self.last_audio_at = None

    @property
    def average_rms(self) -> float:
        if not self.rms_values:
            return 0.0
        return sum(self.rms_values) / len(self.rms_values)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InputAudioRawFrame):
            rms = audioop.rms(frame.audio, 2)
            normalized_rms = rms / 32768.0

            self.rms_values.append(normalized_rms)
            self.last_audio_at = monotonic()

        await self.push_frame(frame, direction)