from app.voice.telephony.answer.human_policy import HumanConfirmationPolicy
from app.voice.telephony.answer.models import AnswerType

def main():
    p = HumanConfirmationPolicy()
    assert p.is_short_greeting("Hello.")
    assert not p.consider("Hello.")
    p.mark_probe_sent()
    assert p.consider("Yes. I'm speaking. What is this?")
    assert p.confirmed
    q = HumanConfirmationPolicy()
    q.mark_probe_sent()
    assert not q.consider("Press 2 for claims")
    assert not q.confirmed
    r = HumanConfirmationPolicy()
    r.set_initial_answer(AnswerType.VOICEMAIL)
    r.mark_probe_sent()
    assert not r.consider("Yes. I'm speaking.")
    s = HumanConfirmationPolicy()
    assert not s.consider("Hello?")
    assert not s.confirmed
    print("Human conversation stabilization tests PASSED")

if __name__ == "__main__":
    main()
