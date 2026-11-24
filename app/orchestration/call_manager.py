
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.database.models import Call, CallEvent
from app.services.session_store import CallSessionStore

from app.orchestration.states import CallState
from app.orchestration.state_machine import validate_transition


class CallNotFoundError(Exception):
    pass


class CallManager:

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.sessions = CallSessionStore(redis)

    async def create_call(self, phone_number: str) -> Call:

        call = Call(
            id=uuid4(),
            phone_number=phone_number,
            direction="outbound",
            status=CallState.INITIATED.value,
        )

        self.db.add(call)

        await self.db.flush()

        self.db.add(
            CallEvent(
                call_id=call.id,
                event_type="call_created",
                payload={
                    "status": CallState.INITIATED.value,
                },
            )
        )

        await self.db.commit()
        await self.db.refresh(call)

        await self.sessions.create(
            call.id,
            {
                "call_id": str(call.id),
                "phone_number": phone_number,
                "status": CallState.INITIATED.value,
            },
        )

        return call

    async def transition(
        self,
        call_id: UUID,
        target: CallState,
        metadata: dict | None = None,
    ) -> dict:

        lock = self.redis.lock(
            f"lock:call:{call_id}",
            timeout=30,
            blocking_timeout=5,
        )

        async with lock:

            result = await self.db.execute(
              select(Call)
              .where(Call.id == call_id)
              .with_for_update()
            )

            call = result.scalar_one_or_none()

            if call is None:
              raise CallNotFoundError(str(call_id))

            current = CallState(call.status)

            validate_transition(current, target)


            call.status = target.value

            if target in {
                CallState.COMPLETED,
                CallState.FAILED,
                CallState.BUSY,
                CallState.DISCONNECTED,
            }:
                call.ended_at = datetime.now(timezone.utc)

            event = CallEvent(
                call_id=call_id,
                event_type="state_transition",
                payload={
                    "from": current.value,
                    "to": target.value,
                    "metadata": metadata or {},
                },
            )

            self.db.add(event)

            await self.db.commit()

        session_data = await self.sessions.get(call_id)

        if session_data is None:
            await self.sessions.create(
                call_id,
                {
                    "call_id": str(call_id),
                    "phone_number": call.phone_number,
                    "status": target.value,
                },
            )
        else:
            await self.sessions.update(
                call_id,
                {"status": target.value},
            )


            return {
                "call_id": str(call_id),
                "previous_state": current.value,
                "current_state": target.value,
            }
