
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.core.config import settings
from app.database.base import Base
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    await redis.ping()

    app.state.redis = redis

    # Local development bootstrap only.
    # Production schema changes will use Alembic.
    if settings.environment == "development":
        from app.database import models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    await redis.aclose()
    await engine.dispose()
