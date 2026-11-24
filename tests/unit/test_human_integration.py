"""Run in your project: uv run python -m tests.unit.test_human_integration"""
import asyncio
from app.voice.telephony.answer.turn_coordinator import TurnCoordinator
from app.voice.telephony.answer.human_policy import HumanConfirmationPolicy
from app.voice.telephony.answer.models import AnswerType

async def main():
    policy = HumanConfirmationPolicy()
    turns = []
    tracker = TurnCoordinator(lambda turn: (turns.append(turn), policy.consider(turn.text)), grace_seconds=0.02)
    tracker.speech_started()
    tracker.final_transcript('Hello?')
    tracker.speech_stopped()
    tracker.final_transcript('Who is this?')  # late Deepgram final
    await asyncio.sleep(0.04)
    assert len(turns) == 1 and turns[0].text == 'Hello? Who is this?'
    assert policy.human_turns == 1 and not policy.confirmed
    tracker.speech_started()
    tracker.final_transcript('Can you hear me?')
    tracker.speech_stopped()
    await asyncio.sleep(0.04)
    assert len(turns) == 2 and policy.confirmed
    await tracker.close()

    ivr = HumanConfirmationPolicy()
    ivr.set_initial_answer(AnswerType.IVR)
    assert not ivr.consider('Press 2 for claim status.')
    assert not ivr.confirmed
    assert not ivr.consider('Hello?')
    assert ivr.consider('Who is this?')  # human after IVR

    vm = HumanConfirmationPolicy()
    vm.set_initial_answer(AnswerType.VOICEMAIL)
    assert not vm.consider('Hello?')
    assert not vm.consider('Who is this?')
    assert not vm.confirmed
    print('Human integration policy tests PASSED')

if __name__ == '__main__':
    asyncio.run(main())
