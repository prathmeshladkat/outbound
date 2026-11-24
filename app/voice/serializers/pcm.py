import json
from loguru import logger

from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    InterruptionFrame,
    TTSStartedFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer


class PCMFrameSerializer(FrameSerializer):
    def __init__(self):
        super().__init__()
        self._generation = 0
        self._accept_audio = False

    async def serialize(self, frame: Frame):
       # if isinstance(frame, (TTSStartedFrame, OutputAudioRawFrame)):
        #    logger.info(
          #      "[AUDIO FLOW] frame={}",
          #      type(frame).__name__,
           # )

        if isinstance(frame, InterruptionFrame):
            return json.dumps({
                "type": "interrupt"
            })

        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio

        return None

    async def deserialize(self, data):
        if not isinstance(data, bytes):
            return None

        if not data or len(data) % 2 != 0:
            return None

        return InputAudioRawFrame(
            audio=data,
            sample_rate=16000,
            num_channels=1,
        )