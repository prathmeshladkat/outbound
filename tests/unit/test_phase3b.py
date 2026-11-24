from app.voice.telephony.answer.human_policy import HumanConfirmationPolicy
from app.voice.telephony.answer.models import AnswerType

def main():
    p = HumanConfirmationPolicy()
    p.set_initial_answer(AnswerType.IVR)
    greeting = "Hello. This is claim status department. How can I help you?"
    assert p.detector.detect(greeting).is_candidate
    assert not p.consider(greeting)
    p.mark_probe_sent()
    assert not p.consider("For claim status, press 2.")
    assert p.consider("Yes, I am speaking.")
    q = HumanConfirmationPolicy()
    q.set_initial_answer(AnswerType.VOICEMAIL)
    q.mark_probe_sent()
    assert not q.consider(greeting)
    print("Phase 3B human policy tests PASSED")

if __name__ == "__main__": main()
