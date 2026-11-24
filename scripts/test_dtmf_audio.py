
import math
import struct
import wave
from pathlib import Path

from app.voice.telephony.ivr.dtmf_audio import generate_dtmf


digit = "2"
duration_ms = 200
sample_rate = 8000

audio = generate_dtmf(
    digit=digit,
    duration_ms=duration_ms,
    sample_rate=sample_rate,
)

expected_bytes = int(
    sample_rate * duration_ms / 1000
) * 2

assert len(audio) == expected_bytes

samples = struct.unpack(
    f"<{len(audio) // 2}h",
    audio,
)

peak = max(abs(sample) for sample in samples)
rms = math.sqrt(
    sum(sample * sample for sample in samples)
    / len(samples)
)

assert peak > 0
assert peak <= 32767

output = Path("dtmf_2.wav")

with wave.open(str(output), "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    wav.writeframes(audio)

print("Digit:", digit)
print("Sample rate:", sample_rate)
print("Duration:", duration_ms, "ms")
print("Audio bytes:", len(audio))
print("Peak amplitude:", peak)
print("RMS:", round(rms, 2))
print("Saved:", output.resolve())
