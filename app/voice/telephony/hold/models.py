from dataclasses import dataclass
from enum import Enum


class HoldState(str, Enum):
    ACTIVE = 'active'
    HOLD_CANDIDATE = 'hold_candidate'
    ON_HOLD = 'on_hold'
    RESUME_CANDIDATE = 'resume_candidate'
    TIMED_OUT = 'timed_out'


class HoldIntent(str, Enum):
    NONE = 'none'
    REQUEST = 'request'
    POSSIBLE_REQUEST = 'possible_request'
    ANNOUNCEMENT = 'announcement'
    POSSIBLE_RESUME = 'possible_resume'
    RESUME = 'resume'


@dataclass(frozen=True)
class HoldDecision:
    intent: HoldIntent
    reason: str


@dataclass(frozen=True)
class HoldTransition:
    previous: HoldState
    current: HoldState
    action: str
    reason: str
