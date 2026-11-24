from app.voice.telephony.answer.human_detector import HumanDetector


detector = HumanDetector()

cases = [
    ("Hello?", True),
    ("Hello, who is this?", True),
    ("Yes, speaking.", True),
    ("Can you hear me?", True),
    ("Press 2 for claim status.", False),
    ("Please leave a message after the beep.", False),
    ("Thank you for calling.", False),
]

for text, expected in cases:
    result = detector.detect(text)

    print(
        f"{text!r} -> "
        f"candidate={result.is_candidate} "
        f"score={result.score}"
    )

    assert result.is_candidate == expected

print("Phase 1E.1 human-evidence tests PASSED")