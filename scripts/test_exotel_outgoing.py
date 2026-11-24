
import asyncio
import base64
import json

from pipecat.frames.frames import (
    InterruptionFrame,
    OutputAudioRawFrame,
)

from app.voice.serializers.exotel import ExotelFrameSerializer


async def main():
    serializer = ExotelFrameSerializer()

    await serializer.deserialize(json.dumps({
        "event": "start",
        "stream_sid": "test-stream-001",
        "start": {
            "stream_sid": "test-stream-001",
        },
    }))

    # 100 ms of silent 24 kHz mono PCM16.
    audio = b"\x00\x00" * 2400

    frame = OutputAudioRawFrame(
        audio=audio,
        sample_rate=24000,
        num_channels=1,
    )

    encoded = await serializer.serialize(frame)
    message = json.loads(encoded)

    decoded = base64.b64decode(
        message["media"]["payload"]
    )

    assert message["event"] == "media"
    assert message["stream_sid"] == "test-stream-001"
    assert len(decoded) == 1600

    print("PASS: 24 kHz TTS converted to 8 kHz telephone audio")
    print("PASS: Outgoing Exotel media JSON created")

    clear = json.loads(
        await serializer.serialize(InterruptionFrame())
    )

    assert clear["event"] == "clear"
    assert clear["stream_sid"] == "test-stream-001"

    print("PASS: Barge-in clear event created")


asyncio.run(main())
