
import time
from dataclasses import dataclass
from enum import Enum

from app.voice.telephony.ivr.detector import IVRDecision


class IVRState(str, Enum):
    LISTENING = "listening"
    ACTION_PENDING = "action_pending"
    WAITING_FOR_NEXT_MENU = "waiting_for_next_menu"
    HUMAN_CONNECTED = "human_connected"
    FAILED = "failed"


@dataclass
class IVRAction:
    action: str
    digit: str | None = None
    reason: str = ""


class IVRStateMachine:
    def __init__(self, timeout_seconds: float = 15.0, max_depth: int = 5):
        self.state = IVRState.LISTENING
        self.timeout_seconds = timeout_seconds

        self.last_menu = None
        self.last_digit = None
        self.last_action_time = None
        self.menu_depth = 0
        self.max_depth = max_depth
        self.history = []

    @staticmethod
    def normalize_menu(text: str) -> str:
        return " ".join(text.lower().split()).strip(" .,!")

    def process(
        self,
        transcript: str,
        decision: IVRDecision,
    ) -> IVRAction:
        if self.state in (IVRState.HUMAN_CONNECTED, IVRState.FAILED):
            return IVRAction(
                action="ignore",
                reason=f"Terminal state: {self.state.value}",
            )

        menu = self.normalize_menu(transcript)

        if decision.is_ivr:
            if decision.selected_digit is None:
                return IVRAction(
                    action="wait",
                    reason="IVR detected, no matching option",
                )

            if self.state == IVRState.ACTION_PENDING:
                return IVRAction(
                    action="wait",
                    reason="Previous DTMF action has not been confirmed",
                )

            if self.menu_depth >= self.max_depth:
                self.state = IVRState.FAILED
                return IVRAction(action="escalate", reason="Maximum IVR depth reached")

            if menu == self.last_menu:
                return IVRAction(
                    action="wait",
                    reason="Duplicate IVR menu",
                )

            self.last_menu = menu
            self.last_digit = decision.selected_digit
            self.state = IVRState.ACTION_PENDING

            return IVRAction(
                action="send_dtmf",
                digit=decision.selected_digit,
                reason=decision.reason,
            )

        return IVRAction(
            action="wait",
            reason="No IVR instruction detected",
        )

    def confirm_dtmf_sent(self) -> None:
        if self.state != IVRState.ACTION_PENDING:
            raise RuntimeError("No pending DTMF action")

        self.state = IVRState.WAITING_FOR_NEXT_MENU
        self.last_action_time = time.monotonic()
        self.menu_depth += 1
        self.history.append((self.last_menu, self.last_digit))

    def mark_human_connected(self) -> None:
        self.state = IVRState.HUMAN_CONNECTED

    def check_timeout(self) -> IVRAction | None:
        if self.state != IVRState.WAITING_FOR_NEXT_MENU:
            return None

        if self.last_action_time is None:
            return None

        elapsed = time.monotonic() - self.last_action_time

        if elapsed < self.timeout_seconds:
            return None

        self.state = IVRState.FAILED

        return IVRAction(
            action="escalate",
            reason="Timed out waiting for the next IVR response",
        )
