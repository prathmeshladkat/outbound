"""Suppress IVR/voicemail input to the outbound LLM context until human activation."""
from pipecat.frames.frames import (Frame, TranscriptionFrame, InterimTranscriptionFrame,
    VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame, LLMRunFrame)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

class OutboundVoiceGate(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.human_active = False
        self.probe_allowed = False

    def activate_human(self):
        self.human_active = True
        self.probe_allowed = False

    def allow_one_probe(self):
        if not self.human_active:
            self.probe_allowed = True

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if direction == FrameDirection.DOWNSTREAM and not self.human_active:
            if isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame,
                                  VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame)):
                return
            if isinstance(frame, LLMRunFrame):
                if not self.probe_allowed:
                    return
                self.probe_allowed = False
        await self.push_frame(frame, direction)
