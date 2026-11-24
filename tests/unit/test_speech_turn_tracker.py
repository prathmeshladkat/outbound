from app.voice.telephony.answer.speech_turn_tracker import (
    SpeechTurnTracker,
)


def test_multiple_fragments_single_turn():
    tracker = SpeechTurnTracker()

    tracker.on_speech_started()

    tracker.on_transcript("Hello?")
    tracker.on_transcript("Who is this?")

    turn = tracker.on_speech_stopped()

    assert turn is not None
    assert turn.turn_id == 1
    assert turn.text == "Hello? Who is this?"
    assert tracker.turn_count == 1

    print("Single-turn grouping PASSED")


def test_multiple_speech_turns():
    tracker = SpeechTurnTracker()

    tracker.on_speech_started()
    tracker.on_transcript("Hello?")
    first = tracker.on_speech_stopped()

    tracker.on_speech_started()
    tracker.on_transcript("Can you hear me?")
    second = tracker.on_speech_stopped()

    assert first.turn_id == 1
    assert second.turn_id == 2
    assert tracker.turn_count == 2

    print("Multiple speech turns PASSED")


def test_empty_turn():
    tracker = SpeechTurnTracker()

    tracker.on_speech_started()
    result = tracker.on_speech_stopped()

    assert result is None
    assert tracker.turn_count == 0

    print("Empty-turn handling PASSED")


if __name__ == "__main__":
    test_multiple_fragments_single_turn()
    test_multiple_speech_turns()
    test_empty_turn()

    print("Phase 1E.3 speech-turn tests PASSED")