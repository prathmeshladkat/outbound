
import asyncio
import base64
import json
import math
import struct

import websockets


SAMPLE_RATE = 8000
CHUNK_DURATION_MS = 20
TOTAL_DURATION_SECONDS = 2

SAMPLES_PER_CHUNK = (
    SAMPLE_RATE * CHUNK_DURATION_MS // 1000
)


def generate_pcm16_chunk(start_sample: int) -> bytes:
    """Generate a 440 Hz test tone as 16-bit PCM."""
    samples = []

    for i in range(SAMPLES_PER_CHUNK):
        t = (start_sample + i) / SAMPLE_RATE

        value = int(
            8000 * math.sin(2 * math.pi * 440 * t)
        )

        samples.append(value)

    return struct.pack(
        f"<{len(samples)}h",
        *samples,
    )


async def main():
    async with websockets.connect(
        "ws://localhost:8000/ws/exotel-pipecat-test"
    ) as ws:

        await ws.send(json.dumps({
            "event": "connected"
        }))

        await ws.send(json.dumps({
            "event": "start",
            "stream_sid": "test-audio-stream-001",
            "start": {
                "stream_sid": "test-audio-stream-001",
                "call_sid": "test-audio-call-001",
                "media_format": {
                    "encoding": "audio/x-raw",
                    "sample_rate": 8000,
                    "channels": 1,
                    "bit_depth": 16,
                },
            },
        }))

        total_chunks = (
            TOTAL_DURATION_SECONDS * 1000
            // CHUNK_DURATION_MS
        )

        for sequence in range(total_chunks):
            audio = generate_pcm16_chunk(
                sequence * SAMPLES_PER_CHUNK
            )

            encoded = base64.b64encode(
                audio
            ).decode("ascii")

            await ws.send(json.dumps({
                "event": "media",
                "stream_sid": "test-audio-stream-001",
                "sequence_number": sequence + 1,
                "media": {
                    "payload": encoded,
                },
            }))

            await asyncio.sleep(
                CHUNK_DURATION_MS / 1000
            )

        await ws.send(json.dumps({
            "event": "stop",
            "stop": {
                "reason": "test_completed"
            },
        }))

        print(
            f"Sent {total_chunks} audio chunks "
            f"({TOTAL_DURATION_SECONDS}s)"
        )


if __name__ == "__main__":
    asyncio.run(main())
