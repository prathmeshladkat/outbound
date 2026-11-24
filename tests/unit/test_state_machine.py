
import pytest

from app.orchestration.states import CallState
from app.orchestration.state_machine import (
    validate_transition,
    InvalidTransitionError,
)


def test_valid_transition():
    validate_transition(
        CallState.INITIATED,
        CallState.RINGING,
    )


def test_invalid_transition():
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            CallState.INITIATED,
            CallState.HUMAN_CONNECTED,
        )


def test_terminal_state_cannot_transition():
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            CallState.COMPLETED,
            CallState.RINGING,
        )


def test_ivr_to_hold():
    validate_transition(
        CallState.IVR_NAVIGATION,
        CallState.HOLD,
    )
