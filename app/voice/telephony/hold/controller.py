"""Synchronous routing policy; no provider dependencies."""
from .state import HoldStateMachine

class HoldController:
    def __init__(self, machine=None, on_transition=lambda transition: None):
        self.machine = machine or HoldStateMachine()
        self.on_transition = on_transition
        self.fragments = []
        self.resume_pending = False

    @property
    def blocked(self):
        return self.machine.suppress_conversation or self.resume_pending

    def tick(self):
        transition = self.machine.tick()
        if transition:
            self.on_transition(transition)

    def final(self, text):
        """Called before forwarding a final to the LLM aggregator."""
        self.tick()
        if self.resume_pending:
            return True
        self.fragments.append(text)
        combined = ' '.join(self.fragments)
        was_blocked = self.blocked
        transition = self.machine.observe(combined, human_confirmed=True)
        if transition:
            self.on_transition(transition)
            if transition.action == 'hold_ended':
                self.resume_pending = True
        return was_blocked or self.blocked

    def completed(self):
        self.fragments.clear()
        if self.resume_pending:
            self.resume_pending = False
            return not self.machine.suppress_conversation
        return False
