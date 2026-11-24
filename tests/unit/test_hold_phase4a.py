import unittest
from app.voice.telephony.hold.detector import HoldDetector
from app.voice.telephony.hold.models import HoldIntent, HoldState
from app.voice.telephony.hold.state import HoldStateMachine


class HoldTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.machine = HoldStateMachine(clock=lambda: self.now)

    def say(self, text, confirmed=True):
        return self.machine.observe(text, human_confirmed=confirmed)

    def test_detector(self):
        for text, expected in [
            ('Please hold while I check.', HoldIntent.REQUEST),
            ('Can I put you on hold?', HoldIntent.REQUEST),
            ('Let me check that for you.', HoldIntent.POSSIBLE_REQUEST),
            ('Your claim is on hold.', HoldIntent.NONE),
            ("Please don't put me on hold.", HoldIntent.NONE),
            ('Your call is important to us.', HoldIntent.ANNOUNCEMENT),
            ('Thank you for waiting.', HoldIntent.POSSIBLE_RESUME),
            ('I have checked your claim.', HoldIntent.RESUME),
        ]:
            with self.subTest(text=text):
                self.assertEqual(HoldDetector().detect(text).intent, expected)

    def test_human_guard(self):
        self.assertIsNone(self.say('Please hold', False))
        self.assertEqual(self.machine.state, HoldState.ACTIVE)

    def test_explicit_hold_and_resume(self):
        self.assertEqual(self.say('Please hold').action, 'hold_started')
        self.assertTrue(self.machine.suppress_conversation)
        self.assertIsNone(self.say('Please hold'))
        self.now = 30
        self.assertIsNone(self.machine.tick())
        self.assertIsNone(self.say('Your call is important to us'))
        self.assertEqual(self.say('Thank you for waiting').action, 'resume_candidate')
        self.assertTrue(self.machine.suppress_conversation)
        self.assertEqual(self.say('I have checked your claim').action, 'hold_ended')
        self.assertFalse(self.machine.suppress_conversation)
        self.assertIsNone(self.say('I have checked your claim'))

    def test_ambiguous_request_expires(self):
        self.say('Let me check')
        self.assertFalse(self.machine.suppress_conversation)
        self.now = 8
        self.assertEqual(self.machine.tick().action, 'candidate_expired')

    def test_ambiguous_request_with_announcement(self):
        self.say('Let me check')
        self.assertEqual(self.say('All agents are busy').action, 'hold_started')

    def test_resume_rejected(self):
        self.say('Please hold')
        self.say('Thank you for waiting')
        self.assertEqual(self.say('Please continue to hold').action, 'resume_rejected')
        self.assertEqual(self.machine.state, HoldState.ON_HOLD)

    def test_resume_expiry(self):
        self.say('Please hold')
        self.say('Thank you for waiting')
        self.now = 8
        self.assertEqual(self.machine.tick().action, 'resume_expired')

    def test_timeout_once_and_late_resume(self):
        self.say('Please hold')
        self.now = 119
        self.say('Thank you for waiting')
        self.now = 120
        self.assertEqual(self.machine.tick().action, 'hold_timeout')
        self.assertIsNone(self.machine.tick())
        self.assertTrue(self.machine.suppress_conversation)
        self.assertEqual(self.say("I'm back").action, 'hold_ended')

    def test_silence_does_not_start_hold(self):
        self.now = 500
        self.assertIsNone(self.machine.tick())
        self.assertEqual(self.machine.state, HoldState.ACTIVE)

    def test_repeated_hold_new_deadline(self):
        self.say('Please hold')
        self.now = 100
        self.say("I'm back")
        self.say('Please hold')
        self.now = 120
        self.assertIsNone(self.machine.tick())
        self.now = 220
        self.assertEqual(self.machine.tick().action, 'hold_timeout')


if __name__ == '__main__':
    unittest.main(verbosity=2)
