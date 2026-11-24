import inspect

from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.frames.frames import (
    UserSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)

print("UserSpeakingFrame:", inspect.signature(UserSpeakingFrame))

for method in (
    "process_frame",
    "on_speech_started",
    "on_speech_stopped",
):
    fn = getattr(VADProcessor, method, None)
    if fn:
        print(f"\n--- {method} ---")
        print(inspect.getsource(fn))

print("\nFrame inheritance:")
for cls in (
    UserSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
):
    print(cls.__name__, cls.__mro__)