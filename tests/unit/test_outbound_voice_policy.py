from app.voice.telephony.answer.human_policy import HumanConfirmationPolicy
from app.voice.telephony.answer.models import AnswerType

def main():
    p = HumanConfirmationPolicy()
    assert not p.consider("Hello?")
    assert not p.confirmed
    p.mark_probe_sent()
    assert p.consider("Who is this?")
    assert p.confirmed
    q = HumanConfirmationPolicy()
    q.mark_probe_sent()
    q.set_initial_answer(AnswerType.VOICEMAIL)
    assert not q.consider("Who is this?")
    r = HumanConfirmationPolicy()
    r.mark_probe_sent()
    assert not r.consider("Press 2 for claims")
    assert not r.confirmed
    print("Outbound voice policy tests PASSED")

if __name__ == "__main__":
    main()
