from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AnswerType(str, Enum):
    UNKNOWN = "unknown"
    HUMAN = "human"
    IVR = "ivr"
    VOICEMAIL = "voicemail"


@dataclass(frozen=True)
class AnswerDecision:
    answer_type: AnswerType
    confidence: float
    reason: str
    is_final: bool = False


class CallEventType(str, Enum):
    CALL_STARTED = "call.started"
    CALL_CONNECTED = "call.connected"

    ANSWER_CLASSIFIED = "answer.classified"

    IVR_DETECTED = "ivr.detected"
    DTMF_QUEUED = "dtmf.queued"
    DTMF_SENT = "dtmf.sent"

    HUMAN_DETECTED = "human.detected"
    VOICEMAIL_DETECTED = "voicemail.detected"

    HOLD_STARTED = "hold.started"
    HOLD_ENDED = "hold.ended"

    CALL_COMPLETED = "call.completed"
    CALL_FAILED = "call.failed"


@dataclass(frozen=True)
class CallEvent:
    call_id: str
    event_type: CallEventType
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "call_id": self.call_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }