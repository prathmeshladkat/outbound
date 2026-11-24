from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.services.deepgram.stt import DeepgramSTTService
import asyncio

from pipecat.frames.frames import LLMMessagesAppendFrame
from pipecat.frames.frames import LLMRunFrame


from app.core.config import settings
from app.voice.processors.transcript import TranscriptProcessor
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.audio.vad_processor import VADProcessor

from app.voice.processors.speech_activity import SpeechActivityMonitor
from app.voice.vad.hybrid_controller import HybridVADController
from app.voice.processors.audio_energy import AudioEnergyProcessor
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from app.voice.llm.gemini import create_llm
from app.voice.llm.prompts import SYSTEM_PROMPT
from app.voice.processors.llm_response import LLMResponseLogger
from app.voice.processors.frame_debug import FrameDebugProcessor
from app.voice.tts.deepgram import create_tts
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.turns.user_stop import SpeechTimeoutUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from app.voice.processors.latency import LatencyMonitor
from app.voice.processors.language_voice_router import LanguageVoiceRouter
from loguru import logger
from app.voice.processors.ivr_processor import IVRProcessor
from app.voice.telephony.ivr.dtmf_output import make_dtmf_output_frame
from app.voice.telephony.ivr.state import IVRState
from uuid import uuid4

from app.voice.processors.answer_classification import (
    AnswerClassificationProcessor,
)
from app.voice.telephony.answer.turn_coordinator import TurnCoordinator
from app.voice.telephony.answer.human_policy import HumanConfirmationPolicy
from app.voice.processors.outbound_voice_gate import OutboundVoiceGate
from app.voice.telephony.events import InMemoryCallEventSink
from app.voice.telephony.hold.controller import HoldController
from app.voice.telephony.answer.models import (
    AnswerType,
    CallEvent,
    CallEventType,
)


async def run_transcription_pipeline(
    transport,
    *,
    call_mode: str = "inbound",
    stream_started_event: asyncio.Event | None = None,
    enable_outbound_voice: bool = False,
):
    stt = DeepgramSTTService(
        api_key=settings.deepgram_api_key,
        sample_rate=16000,
        settings=DeepgramSTTService.Settings(
            model="nova-3",
            language="multi",
            interim_results=True,
            punctuate=True,
            smart_format=True,
        ),
    )

    energy = AudioEnergyProcessor()
    hybrid = HybridVADController()
    transcript = TranscriptProcessor(hybrid_controller=hybrid)
    call_id = str(uuid4())
    event_sink = InMemoryCallEventSink()


    def handle_answer_classification(decision):
        event_sink.emit(
            CallEvent(
                call_id=call_id,
                event_type=CallEventType.ANSWER_CLASSIFIED,
                payload={
                    "answer_type": decision.answer_type.value,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                },
            )
        )

        if decision.answer_type == AnswerType.IVR:
            event_sink.emit(
                CallEvent(
                    call_id=call_id,
                    event_type=CallEventType.IVR_DETECTED,
                )
            )

        elif decision.answer_type == AnswerType.VOICEMAIL:
            event_sink.emit(
                CallEvent(
                    call_id=call_id,
                    event_type=CallEventType.VOICEMAIL_DETECTED,
                )
            )


    human_policy = HumanConfirmationPolicy()
    def on_hold_transition(transition):
        logger.info("[HOLD] {} -> {} action={} reason={}", transition.previous.value,
                    transition.current.value, transition.action, transition.reason)
        event_type = {"hold_started": CallEventType.HOLD_STARTED,
                      "hold_ended": CallEventType.HOLD_ENDED}.get(transition.action)
        if event_type is not None:
            event_sink.emit(CallEvent(call_id=call_id, event_type=event_type,
                                      payload={"reason": transition.reason}))

    hold_controller = HoldController(on_transition=on_hold_transition)
    voice_gate = OutboundVoiceGate(hold_controller=hold_controller)
    hold_tasks = set()

    async def hold_watchdog():
        while True:
            await asyncio.sleep(0.25)
            hold_controller.tick()

    async def resume_conversation(text):
        if call_ending or hold_controller.blocked:
            return
        await task.queue_frames([LLMMessagesAppendFrame(
            messages=[{"role": "user", "content": text}], run_llm=True)])

    voice_activation_pending = False
    probe_task = None
    speech_active = False
    call_ending = False
    timeout_recoverable = False
    activation_task = None

    def on_completed_turn(turn):
        nonlocal voice_activation_pending, probe_task, activation_task
        if call_ending:
            return
        if human_policy.confirmed and call_mode == "outbound" and enable_outbound_voice:
            if hold_controller.completed():
                resume_task = asyncio.create_task(resume_conversation(turn.text))
                hold_tasks.add(resume_task)
                resume_task.add_done_callback(hold_tasks.discard)
            return
        if ivr_processor.machine.state == IVRState.ACTION_PENDING:
            schedule_dtmf()
            return
        if ivr_processor.machine.state == IVRState.FAILED and not timeout_recoverable:
            return
        if ivr_processor.detector.detect(turn.text).is_ivr:
            return
        if human_policy.consider(turn.text):
            if timeout_task is not None:
                timeout_task.cancel()
            ivr_processor.machine.mark_human_connected()
            ivr_processor.ivr_fragments.clear()
            logger.info("[HUMAN] confirmed after conversational evidence; call_id={}", call_id)
            event_sink.emit(CallEvent(
                call_id=call_id,
                event_type=CallEventType.HUMAN_DETECTED,
                payload={"reason": "conversational evidence", "turn": turn.number},
            ))
            if call_mode == "outbound" and enable_outbound_voice:
                voice_gate.activate_human()
                voice_activation_pending = True
                if probe_task is not None and not probe_task.done():
                    probe_task.cancel()
                activation_task = asyncio.create_task(start_human_conversation(turn.text))
        elif (call_mode == "outbound" and enable_outbound_voice
              and not human_policy.confirmed
              and not human_policy.probe_sent
              and probe_context_allowed()):
            # A weak greeting such as "Hello?" must not deadlock the call.
            # Only probe after a completed turn, not on a raw VAD edge.
            evidence = human_policy.detector.detect(turn.text)
            # A short, standalone greeting is ambiguous, but deserves one
            # controlled response rather than leaving the caller in silence.
            if evidence.is_candidate or human_policy.is_short_greeting(turn.text):
                logger.info("[VOICE PROBE] scheduling after ambiguous turn={!r}", turn.text)
                if probe_task is not None and not probe_task.done():
                    probe_task.cancel()
                probe_task = asyncio.create_task(delayed_ambiguous_probe())

    def probe_context_allowed():
        return (ivr_processor.machine.state not in (IVRState.ACTION_PENDING, IVRState.HUMAN_CONNECTED)
                and (ivr_processor.machine.state != IVRState.FAILED or timeout_recoverable)
                and (answer_processor.current_type == AnswerType.UNKNOWN
                     or (answer_processor.current_type == AnswerType.IVR
                         and (ivr_processor.machine.state == IVRState.WAITING_FOR_NEXT_MENU or timeout_recoverable))))

    async def emit_probe(reason: str):
        # This is an introduction, NOT human confirmation.
        if (call_ending or speech_active or human_policy.confirmed
            or human_policy.probe_sent
            or not probe_context_allowed()):
            logger.info("[VOICE PROBE] suppressed reason={} speech_active={} answer={}",
                        reason, speech_active, answer_processor.current_type.value)
            return
        human_policy.mark_probe_sent()
        voice_gate.allow_one_probe()
        logger.info("[VOICE PROBE] sending reason={}", reason)
        context.add_message({"role": "user", "content": (
            "The outbound recipient may have answered but is not yet confirmed human. "
            "Give one brief introduction: you are the healthcare provider's AI assistant "
            "calling about an insurance claim. Ask whether you are speaking to a representative. "
            "Do not mention patient names, identifiers, or protected information. "
            "Do not claim you have verified who answered."
        )})
        await task.queue_frames([LLMRunFrame()])

    async def delayed_ambiguous_probe():
        try:
            await asyncio.sleep(1.5)
            if stream_started_event is not None:
                await stream_started_event.wait()
            await emit_probe("ambiguous_greeting")
        except asyncio.CancelledError:
            return

    def on_voice_speech_started():
        nonlocal speech_active, probe_task
        speech_active = True
        invalidate_dtmf()
        turn_coordinator.speech_started()
        if probe_task is not None and not probe_task.done():
            probe_task.cancel()

    def on_voice_speech_stopped():
        nonlocal speech_active
        speech_active = False
        turn_coordinator.speech_stopped()

    turn_coordinator = TurnCoordinator(on_turn=on_completed_turn)

    def on_final_transcript(text):
        invalidate_dtmf()
        turn_coordinator.final_transcript(text)

    def on_answer(decision):
        human_policy.set_initial_answer(decision.answer_type)
        handle_answer_classification(decision)

    answer_processor = AnswerClassificationProcessor(
        on_classification=on_answer,
        on_final_transcript=on_final_transcript,
    )

    async def start_human_conversation(last_text: str):
        # The confirmed turn was intentionally blocked from the LLM by the gate.
        # Start with one explicit prompt, then let subsequent human turns flow normally.
        if stream_started_event is not None:
            await stream_started_event.wait()
        if not human_policy.confirmed:
            return
        if human_policy.probe_sent:
            prompt = (
                "You already introduced yourself and asked whether you are speaking "
                "with a representative. The recipient replied: " + repr(last_text)
                + ". Continue the conversation naturally, answering their question "
                "or asking the next appropriate question. Do not repeat your introduction. "
                "Do not disclose patient information before appropriate verification."
            )
        else:
            prompt = (
                "A live recipient appears to have answered. Their last words were: "
                + repr(last_text) + ". Briefly identify yourself as the healthcare "
                "provider's AI assistant and ask if this is a good time to discuss "
                "an insurance claim. Do not disclose patient information yet."
            )
        logger.info("[VOICE] activating Gemini after confirmed human")
        context.add_message({"role": "user", "content": prompt})
        await task.queue_frames([LLMRunFrame()])

    dtmf_task = None
    pending_digit = None
    menu_version = 0
    timeout_task = None


    async def send_dtmf_after_menu(digit: str, version: int):
        nonlocal pending_digit, timeout_task, timeout_recoverable

        try:
            # Wait for a pause after the most recent
            # recognized IVR menu instruction.
            await asyncio.sleep(2.5)

            if speech_active or turn_coordinator.active or turn_coordinator.fragments or version != menu_version or ivr_processor.machine.state != IVRState.ACTION_PENDING:
                return

            if stream_started_event is not None:
                await stream_started_event.wait()

            if call_ending or speech_active or turn_coordinator.active or turn_coordinator.fragments or version != menu_version or ivr_processor.machine.state != IVRState.ACTION_PENDING:
                return
            frame = make_dtmf_output_frame(digit)

            logger.info(
                "[DTMF] Submitting digit={} to Pipecat",
                digit,
            )

            pending_digit = None
            ivr_processor.ivr_fragments.clear()

            ivr_processor.machine.confirm_dtmf_sent()
            timeout_recoverable = False
            human_policy.human_turns = 0
            human_policy.strong_turns = 0
            human_policy.probe_sent = False
            if timeout_task is not None:
                timeout_task.cancel()
            timeout_task = asyncio.create_task(wait_for_next_menu())

            await task.queue_frames([frame])

            logger.info(
                "[DTMF] State updated to {}",
                ivr_processor.machine.state.value,
            )

            logger.info(
                "[DTMF] Digit={} queued; "
                "remote IVR recognition not yet confirmed",
                digit,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("[DTMF] Failed to queue digit={}", digit)


    async def wait_for_next_menu():
        nonlocal timeout_recoverable
        await asyncio.sleep(ivr_processor.machine.timeout_seconds)
        result = ivr_processor.machine.check_timeout()
        if result:
            timeout_recoverable = True
            logger.warning("[IVR] {}", result.reason)

    def invalidate_dtmf():
        nonlocal menu_version, dtmf_task
        menu_version += 1
        if (dtmf_task is not None and not dtmf_task.done()
                and ivr_processor.machine.state == IVRState.ACTION_PENDING):
            dtmf_task.cancel()
        dtmf_task = None

    def schedule_dtmf():
        nonlocal dtmf_task
        if (call_ending or speech_active or turn_coordinator.active
                or turn_coordinator.fragments or pending_digit is None
                or ivr_processor.machine.state != IVRState.ACTION_PENDING):
            return
        invalidate_dtmf()
        logger.info("[DTMF] Completed turn; waiting for quiet menu boundary")
        dtmf_task = asyncio.create_task(send_dtmf_after_menu(pending_digit, menu_version))

    def handle_ivr_result(action):
        nonlocal pending_digit, timeout_recoverable
        if action.action == "escalate":
            timeout_recoverable = False
            logger.warning("[IVR] {}", action.reason)
            return
        if action.action == "send_dtmf" and action.digit and pending_digit is None:
            pending_digit = action.digit
            logger.info("[DTMF] Selected digit={}; waiting for completed turn", pending_digit)


    ivr_processor = IVRProcessor(
        on_ivr_result=(
            handle_ivr_result
            if call_mode == "outbound"
            else None
        )
    )

    vad_analyzer = SileroVADAnalyzer(
        sample_rate=16000,
        params=VADParams(
            confidence=0.7,
            start_secs=0.2,
            stop_secs=0.5,
            min_volume=0.6,
        ),
    )
    
    vad_processor = VADProcessor(
        vad_analyzer=vad_analyzer,
    )
    
    speech_monitor = SpeechActivityMonitor(
        hybrid_controller=hybrid,
        energy_processor=energy,
        on_speech_started=(on_voice_speech_started if call_mode == "outbound" else None),
        on_speech_stopped=(on_voice_speech_stopped if call_mode == "outbound" else None),
    )

    llm = create_llm()
    tts = create_tts()
    context = LLMContext(
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]
    )
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                stop=[
                    SpeechTimeoutUserTurnStopStrategy(
                        user_speech_timeout=0.5,
                        wait_for_transcript=True,
                    )
                ]
            )
        ),
    )
    llm_logger = LLMResponseLogger()
    latency_monitor = LatencyMonitor()
    language_voice_router = LanguageVoiceRouter()
    ivr_test_mode = call_mode == "outbound" and not enable_outbound_voice


    processors = [
        transport.input(),
        stt,
        transcript,
    ]
    
    if call_mode == "outbound":
        processors.append(answer_processor)
    
    processors.extend([
        ivr_processor,
        energy,
        vad_processor,
        speech_monitor,
    ])

    if not ivr_test_mode:
        if call_mode == "outbound":
            processors.append(voice_gate)
        processors.extend([
            context_aggregator.user(),
            llm,
            latency_monitor,
            llm_logger,
            language_voice_router,
            tts,
            context_aggregator.assistant(),
        ])

    processors.append(transport.output())

    pipeline = Pipeline(processors)
    if call_mode not in ("inbound", "outbound"):
        raise ValueError(f"Unsupported call mode: {call_mode}")

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            enable_metrics=True,
        ),
    )
    
    async def outbound_greeting_timer():
        logger.info("[OUTBOUND DEBUG] Greeting timer task created")
        try:
            if stream_started_event is not None:
                logger.info(
                    "[OUTBOUND DEBUG] Waiting for Exotel start event"
                )
                await stream_started_event.wait()

            logger.info(
                "[OUTBOUND DEBUG] Stream started; "
                "waiting 3 seconds for speech or transcript"
            )

            # Wait briefly for either VAD speech detection
            # or Deepgram transcription activity.
            speech_waiter = asyncio.create_task(
                speech_monitor.first_speech_event.wait()
            )

            transcript_waiter = asyncio.create_task(
                ivr_processor.first_transcript_event.wait()
            )

            try:
                done, pending = await asyncio.wait(
                    [speech_waiter, transcript_waiter],
                    timeout=3.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if done:
                    logger.info(
                        "[OUTBOUND] Incoming speech/transcript detected; "
                        "automatic greeting cancelled"
                    )
                    return

                # Check again to reduce the chance of a race
                # at the timeout boundary.
                if (
                    speech_monitor.first_speech_event.is_set()
                    or ivr_processor.first_transcript_event.is_set()
                ):
                    logger.info(
                        "[OUTBOUND] Speech detected at timeout; "
                        "greeting cancelled"
                    )
                    return

                logger.info(
                    "[OUTBOUND] No incoming speech within 3 seconds; "
                    "triggering greeting"
                )

                await emit_probe("initial_silence")

            finally:
                for waiter in (speech_waiter, transcript_waiter):
                    if not waiter.done():
                        waiter.cancel()

                await asyncio.gather(
                    speech_waiter,
                    transcript_waiter,
                    return_exceptions=True,
                )

        except asyncio.CancelledError:
            logger.info(
                "[OUTBOUND DEBUG] Greeting timer cancelled"
            )
            raise

        except Exception:
            logger.exception(
                "[OUTBOUND DEBUG] Greeting timer failed"
            )


    runner = PipelineRunner()
    greeting_task = None
    hold_watchdog_task = None

    try:
        logger.info(
            "[OUTBOUND DEBUG] Pipeline call_mode={}",
            call_mode,
        )

        if call_mode == "outbound" and not ivr_test_mode:
            hold_watchdog_task = asyncio.create_task(hold_watchdog())
            greeting_task = asyncio.create_task(
                outbound_greeting_timer()
            )

            logger.info(
                "[OUTBOUND DEBUG] Greeting task scheduled"
            )

        await runner.run(task)

    finally:
        call_ending = True
        if hold_watchdog_task is not None:
            hold_watchdog_task.cancel()
            await asyncio.gather(hold_watchdog_task, return_exceptions=True)
        pending_hold_tasks = list(hold_tasks)
        for hold_task in pending_hold_tasks:
            hold_task.cancel()
        await asyncio.gather(*pending_hold_tasks, return_exceptions=True)
        if activation_task is not None:
            activation_task.cancel()
            await asyncio.gather(activation_task, return_exceptions=True)
        if timeout_task is not None:
            timeout_task.cancel()
            await asyncio.gather(timeout_task, return_exceptions=True)
        if probe_task is not None:
            probe_task.cancel()
            await asyncio.gather(probe_task, return_exceptions=True)
        if greeting_task is not None:
            greeting_task.cancel()

            try:
                await greeting_task
            except asyncio.CancelledError:
                pass
            
        if dtmf_task is not None:
            dtmf_task.cancel()

            await asyncio.gather(
                dtmf_task,
                return_exceptions=True,
            )

        if call_mode == "outbound":
            await turn_coordinator.close()
        await task.cancel()
