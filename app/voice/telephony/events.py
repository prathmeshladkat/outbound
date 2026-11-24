from loguru import logger

from app.voice.telephony.answer.models import CallEvent


class InMemoryCallEventSink:
    def __init__(self):
        self.events: list[CallEvent] = []

    def emit(self, event: CallEvent):
        self.events.append(event)

        logger.info(
            "[EVENT] {} call_id={} payload={}",
            event.event_type.value,
            event.call_id,
            event.payload,
        )