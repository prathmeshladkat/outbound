import asyncio
import base64
import json
import struct

from app.voice.serializers.exotel import ExotelFrameSerializer


async def main():
    serializer = ExotelFrameSerializer()

    # 160 samples = 20 ms at 8 kHz.
    pcm_8khz = struct.pack("<160h", *([1000] * 160))

    event = {
        "event": "media",
        "media": {
            "payload": base64.b64encode(
                pcm_8khz
            ).decode("ascii")
        }
    }

    frame = await serializer.deserialize(
        json.dumps(event)
    )

    assert frame is not None
    assert frame.sample_rate == 16000
    assert frame.num_channels == 1
    assert len(frame.audio) == 640

    print("PASS: Exotel serializer converted 320 bytes to 640 bytes")


asyncio.run(main())