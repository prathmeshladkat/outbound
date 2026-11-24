
import numpy as np

from app.voice.telephony.ivr.dtmf_audio import (
    DTMF_FREQUENCIES,
    generate_dtmf,
)


SAMPLE_RATE = 8000

LOW_FREQUENCIES = [697, 770, 852, 941]
HIGH_FREQUENCIES = [1209, 1336, 1477]


def detect_frequencies(audio: bytes):
    samples = np.frombuffer(
        audio,
        dtype="<i2",
    ).astype(np.float64)

    samples *= np.hanning(len(samples))

    spectrum = np.abs(np.fft.rfft(samples))

    frequencies = np.fft.rfftfreq(
        len(samples),
        d=1 / SAMPLE_RATE,
    )

    def strongest(candidates):
        return max(
            candidates,
            key=lambda freq: spectrum[
                np.argmin(np.abs(frequencies - freq))
            ],
        )

    return (
        strongest(LOW_FREQUENCIES),
        strongest(HIGH_FREQUENCIES),
    )


for digit, expected in DTMF_FREQUENCIES.items():
    audio = generate_dtmf(digit)

    detected = detect_frequencies(audio)

    assert detected == expected, (
        f"Digit {digit}: expected {expected}, "
        f"detected {detected}"
    )

    print(
        f"Digit {digit}: "
        f"{detected[0]} Hz + {detected[1]} Hz — PASS"
    )

print("\nAll DTMF frequency tests passed!")
