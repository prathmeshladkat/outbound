
import base64

from app.voice.telephony.ivr.dtmf_audio import generate_dtmf


class ExotelDTMFAdapter:
    @staticmethod
    def build_messages(
        digit: str,
        stream_sid: str,
        duration_ms: int = 200,
    ) -> list[dict]:
        if not stream_sid:
            raise ValueError("stream_sid is required")

        pcm = generate_dtmf(
            digit=digit,
            duration_ms=duration_ms,
            sample_rate=8000,
        )

        # Exotel documents a minimum outgoing payload
        # size of 3200 bytes and multiples of 320.
        chunk_size = 3200

        if len(pcm) % 320:
            pcm += bytes(320 - len(pcm) % 320)

        messages = []

        for offset in range(0, len(pcm), chunk_size):
            chunk = pcm[offset:offset + chunk_size]

            if len(chunk) < 3200:
                chunk += bytes(3200 - len(chunk))

            messages.append({
                "event": "media",
                "stream_sid": stream_sid,
                "media": {
                    "payload": base64.b64encode(
                        chunk
                    ).decode("ascii")
                },
            })

        return messages
