
import asyncio
import base64
import json
import math
import struct

import websockets


URL = "ws://localhost:8000/ws/exotel-pipecat-test"


async def receive_audio(ws):
    received = 0
    total_bytes = 0

    try:
        async for raw in ws:
            if not isinstance(raw, str):
                continue

            message = json.loads(raw)
            event = message.get("event")

            if event == "media":
                payload = message.get("media", {}).get("payload")
                if not payload:
                    continue

                audio = base64.b64decode(payload)

                received += 1
                total_bytes += len(audio)

                if received % 10 == 0:
                    print(
                        f"[RECEIVED] {received} audio chunks, "
                        f"{total_bytes} bytes"
                    )

            elif event == "clear":
                print("[RECEIVED] Barge-in clear event")

    except websockets.exceptions.ConnectionClosed:
        pass

    print(
        f"[RESULT] Received {received} audio chunks, "
        f"{total_bytes} bytes"
    )


async def main():
    async with websockets.connect(
        URL,
        max_size=None,
        open_timeout=15,
    ) as ws:

        print("[CONNECTED] Pipecat telephony WebSocket")

        await ws.send(json.dumps({
            "event": "connected",
            "protocol": "Call",
            "version": "1.0.0",
        }))

        await ws.send(json.dumps({
            "event": "start",
            "stream_sid": "test-bidirectional-001",
            "start": {
                "stream_sid": "test-bidirectional-001",
                "call_sid": "test-call-001",
                "media_format": {
                    "encoding": "audio/x-raw",
                    "sample_rate": 8000,
                    "channels": 1,
                    "bit_depth": 16,
                },
            },
        }))

        receiver = asyncio.create_task(receive_audio(ws))

        # Generate 2 seconds of 440 Hz test audio.
        for _ in range(100):
            samples = [
                int(
                    8000 * math.sin(
                        2 * math.pi * 440 * i / 8000
                    )
                )
                for i in range(160)
            ]

            audio = struct.pack("<160h", *samples)

            await ws.send(json.dumps({
                "event": "media",
                "stream_sid": "test-bidirectional-001",
                "media": {
                    "payload": base64.b64encode(
                        audio
                    ).decode("ascii")
                },
            }))

            await asyncio.sleep(0.02)

        print("[SENT] 100 audio chunks")

        # Allow time for a potential LLM/TTS response.
        await asyncio.sleep(5)

        await ws.send(json.dumps({
            "event": "stop",
            "stream_sid": "test-bidirectional-001",
        }))

        await ws.close()
        await receiver


asyncio.run(main())
