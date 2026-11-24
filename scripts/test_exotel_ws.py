import asyncio
import json

import websockets


async def main():
    async with websockets.connect(
        "ws://localhost:8000/ws/exotel"
    ) as ws:
        events = [
            {"event": "connected"},
            {
                "event": "start",
                "stream_sid": "test-stream-001",
                "start": {
                    "stream_sid": "test-stream-001",
                    "call_sid": "test-call-001",
                    "media_format": {
                        "encoding": "audio/x-raw",
                        "sample_rate": "8000",
                    },
                },
            },
            {
                "event": "dtmf",
                "dtmf": {"digit": "1"},
            },
            {
                "event": "stop",
                "stop": {"reason": "callended"},
            },
        ]

        for event in events:
            await ws.send(json.dumps(event))
            await asyncio.sleep(0.2)

        print("Test events sent successfully")


asyncio.run(main())