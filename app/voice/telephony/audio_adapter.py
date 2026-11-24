
import struct


class TelephonyAudioAdapter:
    """
    Convert mono 8 kHz PCM16 audio to mono 16 kHz PCM16.

    Uses linear interpolation and preserves state
    across incoming WebSocket audio chunks.

    This is an initial adapter for our simulated
    PCM16 stream, not yet a universal Exotel decoder.
    """

    def __init__(self):
        self.previous_sample: int | None = None

    def to_16khz(self, audio_8khz: bytes) -> bytes:
        if len(audio_8khz) % 2 != 0:
            raise ValueError(
                "PCM16 audio must contain complete 2-byte samples"
            )

        if not audio_8khz:
            return b""

        sample_count = len(audio_8khz) // 2

        samples = struct.unpack(
            f"<{sample_count}h",
            audio_8khz,
        )

        output = []

        for sample in samples:
            if self.previous_sample is None:
                midpoint = sample
            else:
                midpoint = (
                    self.previous_sample + sample
                ) // 2

            output.append(midpoint)
            output.append(sample)

            self.previous_sample = sample

        return struct.pack(
            f"<{len(output)}h",
            *output,
        )

    def reset(self):
        self.previous_sample = None



class OutgoingTelephonyAudioAdapter:
    """
    Convert 24 kHz mono PCM16 to 8 kHz mono PCM16.

    Simple 3:1 averaging for local integration testing.
    Production should use a proper anti-aliasing resampler.
    """

    def __init__(self):
        self._pending = b""

    def to_8khz(self, audio_24khz: bytes) -> bytes:
        data = self._pending + audio_24khz

        if len(data) % 2:
            raise ValueError("Incomplete PCM16 sample")

        # 3 input samples produce 1 output sample.
        usable_bytes = (len(data) // 6) * 6

        self._pending = data[usable_bytes:]
        data = data[:usable_bytes]

        if not data:
            return b""

        samples = struct.unpack(
            f"<{len(data) // 2}h",
            data,
        )

        output = []

        for i in range(0, len(samples), 3):
            average = round(
                (samples[i] + samples[i + 1] + samples[i + 2]) / 3
            )
            output.append(average)

        return struct.pack(
            f"<{len(output)}h",
            *output,
        )
