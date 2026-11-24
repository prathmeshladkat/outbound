
from enum import StrEnum


class CallState(StrEnum):
    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"

    IVR_DETECTED = "ivr_detected"
    IVR_NAVIGATION = "ivr_navigation"

    HOLD = "hold"
    HUMAN_CONNECTED = "human_connected"

    VOICEMAIL = "voicemail"

    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    DISCONNECTED = "disconnected"


TERMINAL_STATES = {
    CallState.COMPLETED,
    CallState.FAILED,
    CallState.BUSY,
    CallState.DISCONNECTED,
}
