
from fastapi import FastAPI

from app.core.lifecycle import lifespan
from app.api.routes.health import router as health_router
from app.api.routes.calls import router as calls_router
from app.api.websocket.audio import router as audio_router
from app.api.websocket.exotel import router as exotel_router

app = FastAPI(
    title="Payer Voice Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(audio_router)
app.include_router(calls_router)
app.include_router(exotel_router)