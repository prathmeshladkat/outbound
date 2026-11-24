"""Suppress IVR/voicemail input to the outbound LLM context until human activation."""
from pipecat.frames.frames import (Frame, TranscriptionFrame, InterimTranscriptionFrame,
    VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame, LLMRunFrame)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

class OutboundVoiceGate(FrameProcessor):
    def __init__(self, hold_controller=None, **kwargs):
        super().__init__(**kwargs)
        self.hold_controller = hold_controller
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
        if direction == FrameDirection.DOWNSTREAM and self.human_active and self.hold_controller is not None:
            if isinstance(frame, TranscriptionFrame) and frame.text.strip():
                if self.hold_controller.final(frame.text):
                    return
            elif self.hold_controller.blocked and isinstance(frame, (
                InterimTranscriptionFrame, VADUserStartedSpeakingFrame,
                VADUserStoppedSpeakingFrame, LLMRunFrame,
            )):
                return
        await self.push_frame(frame, direction)
