from app.voice.telephony.ivr.detector import IVRDetector
from app.voice.telephony.ivr.state import IVRStateMachine, IVRState

def main():
    d = IVRDetector()
    m = IVRStateMachine(max_depth=2)
    a = "For insurance claims, press 2."
    b = "For existing claim, press 1."
    assert m.process(a,d.detect(a)).digit == "2"
    assert m.process(a,d.detect(a)).action == "wait"
    m.confirm_dtmf_sent()
    assert m.process(a,d.detect(a)).action == "wait"
    assert m.process(b,d.detect(b)).digit == "1"
    m.confirm_dtmf_sent()
    assert m.menu_depth == 2
    assert m.process(a,d.detect(a)).action == "escalate"
    assert m.state == IVRState.FAILED
    m = IVRStateMachine(timeout_seconds=0)
    m.process(a,d.detect(a)); m.confirm_dtmf_sent()
    assert m.check_timeout().action == "escalate"
    m.mark_human_connected()
    assert m.process(b,d.detect(b)).action == "ignore"
    print("Nested IVR state tests PASSED")

if __name__ == "__main__": main()
