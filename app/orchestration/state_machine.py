
from app.orchestration.states import (
    CallState,
    TERMINAL_STATES,
)


ALLOWED_TRANSITIONS = {
    CallState.INITIATED: {
        CallState.RINGING,
        CallState.FAILED,
        CallState.BUSY,
    },

    CallState.RINGING: {
        CallState.ANSWERED,
        CallState.VOICEMAIL,
        CallState.BUSY,
        CallState.FAILED,
        CallState.DISCONNECTED,
    },

    CallState.ANSWERED: {
        CallState.IVR_DETECTED,
        CallState.IVR_NAVIGATION,
        CallState.HUMAN_CONNECTED,
        CallState.HOLD,
        CallState.VOICEMAIL,
        CallState.COMPLETED,
        CallState.DISCONNECTED,
    },

    CallState.IVR_DETECTED: {
        CallState.IVR_NAVIGATION,
        CallState.HOLD,
        CallState.HUMAN_CONNECTED,
        CallState.VOICEMAIL,
        CallState.FAILED,
        CallState.DISCONNECTED,
    },

    CallState.IVR_NAVIGATION: {
        CallState.HOLD,
        CallState.HUMAN_CONNECTED,
        CallState.VOICEMAIL,
        CallState.FAILED,
        CallState.DISCONNECTED,
    },

    CallState.HOLD: {
        CallState.HUMAN_CONNECTED,
        CallState.IVR_NAVIGATION,
        CallState.FAILED,
        CallState.DISCONNECTED,
    },

    CallState.HUMAN_CONNECTED: {
        CallState.HOLD,
        CallState.COMPLETED,
        CallState.DISCONNECTED,
    },

    CallState.VOICEMAIL: {
        CallState.COMPLETED,
        CallState.DISCONNECTED,
    },
}


class InvalidTransitionError(Exception):
    pass


def validate_transition(
    current: CallState,
    target: CallState,
) -> None:

    if current in TERMINAL_STATES:
        raise InvalidTransitionError(
            f"Call already terminated: {current}"
        )

    allowed = ALLOWED_TRANSITIONS.get(current, set())

    if target not in allowed:
        raise InvalidTransitionError(
            f"Invalid transition: {current} -> {target}"
        )
