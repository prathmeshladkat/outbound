
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.database.session import AsyncSessionLocal
from app.api.schemas.calls import (
    CreateCallRequest,
    TransitionRequest,
)
from app.orchestration.call_manager import (
    CallManager,
    CallNotFoundError,
)
from app.orchestration.state_machine import InvalidTransitionError


router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("")
async def create_call(
    body: CreateCallRequest,
    request: Request,
):
    async with AsyncSessionLocal() as db:

        manager = CallManager(
            db,
            request.app.state.redis,
        )

        call = await manager.create_call(body.phone_number)

        return {
            "call_id": str(call.id),
            "phone_number": call.phone_number,
            "status": call.status,
        }


@router.post("/{call_id}/transition")
async def transition_call(
    call_id: UUID,
    body: TransitionRequest,
    request: Request,
):
    async with AsyncSessionLocal() as db:

        manager = CallManager(
            db,
            request.app.state.redis,
        )

        try:
            return await manager.transition(
                call_id,
                body.target_state,
                body.metadata,
            )

        except InvalidTransitionError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            )

        except CallNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Call not found",
            )
