"""Per-call policy. Caller supplies completed turns and periodically calls tick()."""
import time
from collections.abc import Callable
from .detector import HoldDetector
from .models import HoldIntent, HoldState, HoldTransition


class HoldStateMachine:
    def __init__(self, *, max_hold_seconds: float = 120, candidate_seconds: float = 8,
                 clock: Callable[[], float] = time.monotonic):
        if max_hold_seconds <= 0 or candidate_seconds <= 0:
            raise ValueError('timeouts must be positive')
        self.clock = clock
        self.max_hold_seconds = max_hold_seconds
        self.candidate_seconds = candidate_seconds
        self.detector = HoldDetector()
        self.state = HoldState.ACTIVE
        self.hold_started_at = None
        self.candidate_at = None

    @property
    def suppress_conversation(self) -> bool:
        return self.state in (HoldState.ON_HOLD, HoldState.RESUME_CANDIDATE, HoldState.TIMED_OUT)

    def _move(self, state, action, reason):
        previous = self.state
        self.state = state
        self.candidate_at = self.clock() if state in (HoldState.HOLD_CANDIDATE, HoldState.RESUME_CANDIDATE) else None
        if action == 'hold_started':
            self.hold_started_at = self.clock()
        elif action == 'hold_ended':
            self.hold_started_at = None
        return HoldTransition(previous, state, action, reason)

    def observe(self, text: str, *, human_confirmed: bool) -> HoldTransition | None:
        if not human_confirmed or not text.strip():
            return None
        expired = self.tick()
        if expired and expired.action == 'hold_timeout':
            return expired
        intent = self.detector.detect(text).intent
        if self.state in (HoldState.ACTIVE, HoldState.HOLD_CANDIDATE):
            if intent == HoldIntent.REQUEST:
                return self._move(HoldState.ON_HOLD, 'hold_started', 'explicit request')
            if self.state == HoldState.HOLD_CANDIDATE and intent == HoldIntent.ANNOUNCEMENT:
                return self._move(HoldState.ON_HOLD, 'hold_started', 'request followed by queue announcement')
            if intent == HoldIntent.POSSIBLE_REQUEST:
                if self.state == HoldState.ACTIVE:
                    return self._move(HoldState.HOLD_CANDIDATE, 'candidate', 'ambiguous request')
            elif self.state == HoldState.HOLD_CANDIDATE:
                return self._move(HoldState.ACTIVE, 'candidate_cleared', 'no supporting hold evidence')
        elif self.state in (HoldState.ON_HOLD, HoldState.RESUME_CANDIDATE, HoldState.TIMED_OUT):
            if intent == HoldIntent.RESUME:
                return self._move(HoldState.ACTIVE, 'hold_ended', 'specific conversational return')
            if self.state == HoldState.TIMED_OUT:
                return None
            if intent == HoldIntent.POSSIBLE_RESUME and self.state == HoldState.ON_HOLD:
                return self._move(HoldState.RESUME_CANDIDATE, 'resume_candidate', 'ambiguous greeting')
            if intent in (HoldIntent.ANNOUNCEMENT, HoldIntent.REQUEST) and self.state == HoldState.RESUME_CANDIDATE:
                return self._move(HoldState.ON_HOLD, 'resume_rejected', 'continued hold evidence')
        return expired

    def tick(self) -> HoldTransition | None:
        now = self.clock()
        if self.state in (HoldState.ON_HOLD, HoldState.RESUME_CANDIDATE) and now - self.hold_started_at >= self.max_hold_seconds:
            return self._move(HoldState.TIMED_OUT, 'hold_timeout', 'maximum hold duration exceeded')
        if self.candidate_at is not None and now - self.candidate_at >= self.candidate_seconds:
            if self.state == HoldState.HOLD_CANDIDATE:
                return self._move(HoldState.ACTIVE, 'candidate_expired', 'no supporting evidence')
            return self._move(HoldState.ON_HOLD, 'resume_expired', 'no specific return evidence')
        return None
