import unittest
from app.voice.telephony.hold.controller import HoldController
from app.voice.telephony.hold.state import HoldStateMachine

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.events = []
        self.c = HoldController(HoldStateMachine(clock=lambda: self.now), self.events.append)
    def test_normal(self):
        self.assertFalse(self.c.final('What is the claim number?'))
        self.assertFalse(self.c.completed())
    def test_hold_resume(self):
        self.assertTrue(self.c.final('Please hold.'))
        self.c.completed()
        self.assertTrue(self.c.final('Your call is important to us.'))
        self.c.completed()
        self.assertTrue(self.c.final('I have checked your claim.'))
        self.assertTrue(self.c.blocked)
        self.assertTrue(self.c.completed())
        self.assertFalse(self.c.blocked)
        self.assertFalse(self.c.completed())
        self.assertEqual([e.action for e in self.events], ['hold_started','hold_ended'])
    def test_split_request(self):
        self.assertFalse(self.c.final('Please'))
        self.assertTrue(self.c.final('hold for a moment.'))
        self.c.completed()
        self.assertTrue(self.c.blocked)
    def test_timeout(self):
        self.c.final('Please hold.')
        self.c.completed()
        self.now = 121
        self.c.tick()
        self.c.tick()
        self.assertTrue(self.c.blocked)
        self.assertTrue(self.c.final('I am back.'))
        self.assertTrue(self.c.completed())
        self.assertEqual([e.action for e in self.events], ['hold_started','hold_timeout','hold_ended'])
    def test_ambiguous_return(self):
        self.c.final('Please hold.')
        self.c.completed()
        self.assertTrue(self.c.final('Thank you for waiting.'))
        self.assertFalse(self.c.completed())
        self.assertTrue(self.c.blocked)
    def test_repeated(self):
        for _ in range(2):
            self.assertTrue(self.c.final('Please hold.'))
            self.c.completed()
            self.assertTrue(self.c.final('I am back.'))
            self.assertTrue(self.c.completed())

if __name__ == '__main__': unittest.main()
