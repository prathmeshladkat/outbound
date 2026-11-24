
import math
import struct


DTMF_FREQUENCIES = {
    "1": (697, 1209),
    "2": (697, 1336),
    "3": (697, 1477),
    "4": (770, 1209),
    "5": (770, 1336),
    "6": (770, 1477),
    "7": (852, 1209),
    "8": (852, 1336),
    "9": (852, 1477),
    "*": (941, 1209),
    "0": (941, 1336),
    "#": (941, 1477),
}


def generate_dtmf(
    digit: str,
    duration_ms: int = 200,
    sample_rate: int = 8000,
) -> bytes:
    if digit not in DTMF_FREQUENCIES:
        raise ValueError(f"Unsupported DTMF digit: {digit}")

    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")

    if sample_rate != 8000:
        raise ValueError("Expected 8000 Hz telephony audio")

    low_freq, high_freq = DTMF_FREQUENCIES[digit]
    sample_count = round(sample_rate * duration_ms / 1000)

    amplitude = 0.35 * 32767
    fade_samples = min(
        int(sample_rate * 0.005),
        sample_count // 2,
    )

    audio = bytearray()

    for i in range(sample_count):
        t = i / sample_rate

        value = (
            math.sin(2 * math.pi * low_freq * t)
            + math.sin(2 * math.pi * high_freq * t)
        ) / 2

        envelope = 1.0

        if fade_samples:
            envelope = min(
                1.0,
                i / fade_samples,
                (sample_count - 1 - i) / fade_samples,
            )

        sample = int(amplitude * value * envelope)
        audio.extend(struct.pack("<h", sample))

    return bytes(audio)
