"""Group final STT fragments into VAD turns, allowing late Deepgram finals."""
import asyncio
from dataclasses import dataclass
from typing import Callable
from loguru import logger

@dataclass(frozen=True)
class CompletedTurn:
    text: str
    number: int

class TurnCoordinator:
    def __init__(self, on_turn: Callable[[CompletedTurn], None], grace_seconds: float = 1.0):
        self.on_turn = on_turn
        self.grace_seconds = grace_seconds
        self.fragments: list[str] = []
        self.active = False
        self.number = 0
        self._flush_task: asyncio.Task | None = None

    def speech_started(self):
        self._cancel_flush()
        if self.fragments and not self.active:
            self._flush()
        self.active = True

    def final_transcript(self, text: str):
        if text.strip():
            self.fragments.append(text.strip())
            # Some STT engines send final text after VAD stopped.
            if not self.active:
                self._schedule_flush()

    def speech_stopped(self):
        self.active = False
        self._schedule_flush()

    def _cancel_flush(self):
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        self._flush_task = None

    def _schedule_flush(self):
        self._cancel_flush()
        self._flush_task = asyncio.create_task(self._delayed_flush())

    async def _delayed_flush(self):
        try:
            await asyncio.sleep(self.grace_seconds)
            if not self.active:
                self._flush()
        except asyncio.CancelledError:
            return

    def _flush(self):
        text = ' '.join(self.fragments).strip()
        self.fragments.clear()
        if text:
            self.number += 1
            logger.info('[TURN] number={} text={!r}', self.number, text)
            self.on_turn(CompletedTurn(text=text, number=self.number))

    async def close(self):
        self._cancel_flush()
        # Do not invent a completed turn from an unfinished speech segment.
