
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def utc_now():
    return datetime.now(timezone.utc)


class CallState(str, Enum):
    CONNECTING = "connecting"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"


@dataclass
class CallSession:
    session_id: str = field(
        default_factory=lambda: uuid4().hex
    )
    state: CallState = CallState.CONNECTING
    created_at: datetime = field(default_factory=utc_now)
    connected_at: datetime | None = None
    ended_at: datetime | None = None
    disconnect_reason: str | None = None

    def activate(self):
        if self.state != CallState.CONNECTING:
            raise ValueError(
                f"Cannot activate call from {self.state}"
            )

        self.state = CallState.ACTIVE
        self.connected_at = utc_now()

    def end(self, reason: str):
        if self.state == CallState.ENDED:
            return

        self.state = CallState.ENDING
        self.disconnect_reason = reason
        self.ended_at = utc_now()
        self.state = CallState.ENDED

    @property
    def duration_seconds(self) -> float:
        if not self.connected_at:
            return 0.0

        end_time = self.ended_at or utc_now()

        return max(
            0.0,
            (end_time - self.connected_at).total_seconds(),
        )
