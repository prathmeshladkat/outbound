
import unittest
from unittest.mock import AsyncMock, patch

from pipecat.frames.frames import (
    TranscriptionFrame,
    InterimTranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
    LLMRunFrame,
)
from pipecat.processors.frame_processor import (
    FrameProcessor,
    FrameDirection,
)

from app.voice.processors.outbound_voice_gate import (
    OutboundVoiceGate,
)
from app.voice.telephony.hold.controller import HoldController
from app.voice.telephony.hold.state import HoldStateMachine


class HoldFrameTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.now = 0.0
        self.events = []

        self.machine = HoldStateMachine(
            clock=lambda: self.now
        )

        self.controller = HoldController(
            machine=self.machine,
            on_transition=self.events.append,
        )

        self.gate = OutboundVoiceGate(
            hold_controller=self.controller
        )

        # Isolate frame routing from Pipecat runtime lifecycle.
        self.base_patch = patch.object(
            FrameProcessor,
            "process_frame",
            new_callable=AsyncMock,
        )

        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)

        self.gate.push_frame = AsyncMock()

    async def send(self, frame, expected_forwarded):
        self.gate.push_frame.reset_mock()

        await self.gate.process_frame(
            frame,
            FrameDirection.DOWNSTREAM,
        )

        if expected_forwarded:
            self.gate.push_frame.assert_awaited_once_with(
                frame,
                FrameDirection.DOWNSTREAM,
            )
        else:
            self.gate.push_frame.assert_not_awaited()

    async def final(self, text, forwarded):
        await self.send(
            TranscriptionFrame(
                text=text,
                user_id="representative",
                timestamp="0",
            ),
            forwarded,
        )

    async def enter_hold(self):
        self.gate.activate_human()
        await self.final("Please hold.", False)
        self.controller.completed()
        self.assertTrue(self.controller.blocked)

    async def test_pre_human_ivr(self):
        await self.final(
            "For insurance claims, press 2.",
            False,
        )
        await self.send(LLMRunFrame(), False)
        self.assertFalse(self.controller.blocked)

    async def test_one_time_probe(self):
        self.gate.allow_one_probe()
        await self.send(LLMRunFrame(), True)
        await self.send(LLMRunFrame(), False)

    async def test_normal_conversation(self):
        self.gate.activate_human()

        await self.send(
            VADUserStartedSpeakingFrame(), True
        )
        await self.final(
            "What is the claim number?", True
        )
        await self.send(
            VADUserStoppedSpeakingFrame(), True
        )

        self.assertFalse(self.controller.completed())

    async def test_explicit_hold(self):
        await self.enter_hold()
        self.assertEqual(
            self.events[-1].action,
            "hold_started",
        )

    async def test_announcement_suppression(self):
        await self.enter_hold()

        await self.final(
            "Your call is important to us.", False
        )

        self.assertFalse(self.controller.completed())
        self.assertTrue(self.controller.blocked)

    async def test_frames_blocked_during_hold(self):
        await self.enter_hold()

        await self.send(
            VADUserStartedSpeakingFrame(), False
        )

        await self.send(
            InterimTranscriptionFrame(
                text="Please remain on the line",
                user_id="representative",
                timestamp="0",
            ),
            False,
        )

        await self.send(
            VADUserStoppedSpeakingFrame(), False
        )
        await self.send(LLMRunFrame(), False)

    async def test_resume_once(self):
        await self.enter_hold()

        await self.final(
            "I have checked your claim.", False
        )

        self.assertTrue(self.controller.blocked)
        self.assertTrue(self.controller.completed())
        self.assertFalse(self.controller.completed())
        self.assertFalse(self.controller.blocked)

        await self.send(LLMRunFrame(), True)

        await self.final(
            "The claim has been approved.", True
        )

    async def test_ambiguous_resume(self):
        await self.enter_hold()

        await self.final(
            "Thank you for waiting.", False
        )

        self.assertFalse(self.controller.completed())
        self.assertTrue(self.controller.blocked)

    async def test_timeout_and_recovery(self):
        await self.enter_hold()

        self.now = 121
        self.controller.tick()
        self.controller.tick()

        self.assertTrue(self.controller.blocked)

        await self.final("I am back.", False)
        self.assertTrue(self.controller.completed())

        self.assertEqual(
            [event.action for event in self.events],
            [
                "hold_started",
                "hold_timeout",
                "hold_ended",
            ],
        )

    async def test_multiple_hold_cycles(self):
        for _ in range(3):
            await self.enter_hold()

            await self.final("I am back.", False)

            self.assertTrue(
                self.controller.completed()
            )
            self.assertFalse(
                self.controller.blocked
            )

        self.assertEqual(
            [event.action for event in self.events],
            ["hold_started", "hold_ended"] * 3,
        )

    async def test_split_hold_request(self):
        self.gate.activate_human()

        # Documents the current partial-fragment behaviour.
        await self.final("Please", True)
        await self.final("hold for a moment.", False)

        self.controller.completed()
        self.assertTrue(self.controller.blocked)

    async def test_upstream_passthrough(self):
        await self.enter_hold()

        frame = LLMRunFrame()
        self.gate.push_frame.reset_mock()

        await self.gate.process_frame(
            frame,
            FrameDirection.UPSTREAM,
        )

        self.gate.push_frame.assert_awaited_once_with(
            frame,
            FrameDirection.UPSTREAM,
        )


if __name__ == "__main__":
    unittest.main()
