
from app.voice.telephony.ivr.detector import IVRDetector
from app.voice.telephony.ivr.state import IVRStateMachine

detector = IVRDetector()
machine = IVRStateMachine(timeout_seconds=15)

menu1 = "Press 1 for eligibility, press 2 for claim status."
menu2 = "Press 1 for existing claims, press 2 for new claims."

def show(transcript: str):
    decision = detector.detect(transcript)
    action = machine.process(transcript, decision)

    print("Transcript:", transcript)
    print("Decision:", decision)
    print("Action:", action)
    print("State:", machine.state)
    print("-" * 50)

show(menu1)

# Repeat before confirming transmission.
show(menu1)

# Simulate successful DTMF transmission.
machine.confirm_dtmf_sent()
print("DTMF confirmed. State:", machine.state)
print("-" * 50)

# Same menu repeated.
show(menu1)

# A new menu arrives.
show(menu2)

# Do not confirm the second action: no real DTMF was sent.
print("Menu depth:", machine.menu_depth)
