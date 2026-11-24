
import base64

from app.voice.telephony.ivr.dtmf_adapter import (
    ExotelDTMFAdapter,
)


adapter = ExotelDTMFAdapter()

messages = adapter.build_messages(
    digit="2",
    stream_sid="test-stream-123",
    duration_ms=200,
)

assert len(messages) == 10

total_audio_bytes = 0

for message in messages:
    assert message["event"] == "media"
    assert message["streamSid"] == "test-stream-123"

    audio = base64.b64decode(
        message["media"]["payload"],
        validate=True,
    )

    assert len(audio) == 320

    total_audio_bytes += len(audio)

assert total_audio_bytes == 3200

print("Digit: 2")
print("Messages generated:", len(messages))
print("Bytes per message:", 320)
print("Total audio bytes:", total_audio_bytes)
print("All adapter tests passed!")
