
import struct

from pipecat.frames.frames import OutputAudioRawFrame

from app.voice.telephony.ivr.dtmf_audio import generate_dtmf


def make_dtmf_output_frame(
    digit: str,
    duration_ms: int = 200,
) -> OutputAudioRawFrame:
    pcm_8khz = generate_dtmf(
        digit=digit,
        duration_ms=duration_ms,
        sample_rate=8000,
    )

    if len(pcm_8khz) % 2:
        raise ValueError("Invalid 16-bit PCM length")

    samples = struct.unpack(
        f"<{len(pcm_8khz) // 2}h",
        pcm_8khz,
    )

    # Simple 8 kHz -> 24 kHz conversion for
    # this controlled DTMF experiment.
    samples_24khz = [
        sample
        for sample in samples
        for _ in range(3)
    ]

    pcm_24khz = struct.pack(
        f"<{len(samples_24khz)}h",
        *samples_24khz,
    )

    return OutputAudioRawFrame(
        audio=pcm_24khz,
        sample_rate=24000,
        num_channels=1,
    )
