
import asyncio
import base64
import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly
import websockets


URL = "wss://artwork-reconstruction-machinery-makeup.trycloudflare.com/ws/exotel-pipecat-test"
INPUT_FILE = Path("tests/audio/user_speech.wav")
OUTPUT_FILE = Path("tests/audio/agent_response.wav")

STREAM_SID = "test-speech-stream-001"


def load_audio(path):
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        raise ValueError(
            "Input WAV must be 16-bit PCM. "
            "Convert the recording to PCM16 first."
        )

    samples = np.frombuffer(frames, dtype="<i2")

    if channels > 1:
        samples = samples.reshape(-1, channels)
        samples = samples.astype(np.float32).mean(axis=1)

    samples = samples.astype(np.float32)

    from math import gcd

    divisor = gcd(sample_rate, 8000)

    converted = resample_poly(
        samples,
        8000 // divisor,
        sample_rate // divisor,
    )

    converted = np.clip(
        np.rint(converted),
        -32768,
        32767,
    ).astype("<i2")

    return converted.tobytes()


async def receive_audio(ws, chunks):
    try:
        async for raw in ws:
            if not isinstance(raw, str):
                continue

            message = json.loads(raw)
            event = message.get("event")

            if event == "media":
                payload = message.get("media", {}).get("payload")

                if payload:
                    chunks.append(base64.b64decode(payload))

                    if len(chunks) % 25 == 0:
                        print(
                            f"[RECEIVED] {len(chunks)} audio chunks"
                        )

            elif event == "clear":
                print("[RECEIVED] Clear event")
                # Remove previously buffered audio.
                chunks.clear()

    except websockets.exceptions.ConnectionClosed:
        pass


def save_response(chunks):
    if not chunks:
        print("[RESULT] No agent audio received")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(OUTPUT_FILE), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"".join(chunks))

    print(f"[SAVED] {OUTPUT_FILE}")


async def main():
    audio = load_audio(INPUT_FILE)

    # Each 20 ms chunk = 160 samples = 320 bytes.
    chunk_size = 320

    received_chunks = []

    async with websockets.connect(
        URL,
        max_size=None,
        open_timeout=15,
    ) as ws:

        print("[CONNECTED] Telephony simulator")

        await ws.send(json.dumps({
            "event": "connected",
            "protocol": "Call",
            "version": "1.0.0",
        }))

        await ws.send(json.dumps({
            "event": "start",
            "stream_sid": STREAM_SID,
            "start": {
                "stream_sid": STREAM_SID,
                "call_sid": "test-speech-call-001",
                "media_format": {
                    "encoding": "audio/x-raw",
                    "sample_rate": 8000,
                    "channels": 1,
                    "bit_depth": 16,
                },
            },
        }))

        receiver = asyncio.create_task(
            receive_audio(ws, received_chunks)
        )

        for offset in range(0, len(audio), chunk_size):
            chunk = audio[offset:offset + chunk_size]

            if len(chunk) < chunk_size:
                chunk = chunk.ljust(chunk_size, b"\x00")

            await ws.send(json.dumps({
                "event": "media",
                "stream_sid": STREAM_SID,
                "media": {
                    "payload": base64.b64encode(
                        chunk
                    ).decode("ascii")
                },
            }))

            await asyncio.sleep(0.02)

        print("[SENT] Recorded speech")

        # Give Deepgram time to finalize the utterance.
        for _ in range(50):
            await ws.send(json.dumps({
                "event": "media",
                "stream_sid": STREAM_SID,
                "media": {
                    "payload": base64.b64encode(
                        b"\x00" * chunk_size
                    ).decode("ascii")
                },
            }))

            await asyncio.sleep(0.02)

        print("[WAITING] For agent response...")

        # Initial integration test: allow 15 seconds.
        await asyncio.sleep(15)

        await ws.send(json.dumps({
            "event": "stop",
            "stream_sid": STREAM_SID,
        }))

        await ws.close()
        await receiver

    save_response(received_chunks)


if __name__ == "__main__":
    asyncio.run(main())
