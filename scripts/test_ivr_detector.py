
from app.voice.telephony.ivr.detector import IVRDetector

detector = IVRDetector()


examples = [
    "Press 1 for eligibility, press 2 for claim status, "
    "or press 3 for prior authorization.",

    "For claim status, press 2.",

    "To check an existing claim, press 3.",

    "Press two for claims status.",

    "For claims inquiries, select 4.",

    "Hello, thank you for calling. How can I help you?",
]


for example in examples:
    print("\nTranscript:", example)
    print("Decision:", detector.detect(example))
