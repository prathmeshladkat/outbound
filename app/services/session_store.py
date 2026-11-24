
import json
from uuid import UUID

from redis.asyncio import Redis


class CallSessionStore:

    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, call_id: UUID) -> str:
        return f"call:{call_id}"

    async def create(
        self,
        call_id: UUID,
        data: dict,
        ttl: int = 86400,
    ):
        await self.redis.set(
            self._key(call_id),
            json.dumps(data),
            ex=ttl,
        )

    async def get(self, call_id: UUID) -> dict | None:
        data = await self.redis.get(self._key(call_id))

        if data is None:
            return None

        return json.loads(data)

    async def update(
        self,
        call_id: UUID,
        updates: dict,
        ttl: int = 86400,
    ):
        existing = await self.get(call_id)

        if existing is None:
            raise KeyError(f"Call session {call_id} not found")

        existing.update(updates)

        await self.create(call_id, existing, ttl)

    async def delete(self, call_id: UUID):
        await self.redis.delete(self._key(call_id))
