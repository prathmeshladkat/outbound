
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.database.session import engine

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request):

    checks = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "connected"
    except Exception:
        checks["postgres"] = "unavailable"

    try:
        await request.app.state.redis.ping()
        checks["redis"] = "connected"
    except Exception:
        checks["redis"] = "unavailable"

    healthy = all(
        value == "connected"
        for value in checks.values()
    )

    return {
        "status": "ready" if healthy else "degraded",
        "dependencies": checks,
    }
