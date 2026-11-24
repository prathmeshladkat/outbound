
from uuid import UUID

from pydantic import BaseModel, Field

from app.orchestration.states import CallState


class CreateCallRequest(BaseModel):
    phone_number: str = Field(
        min_length=10,
        max_length=20,
    )


class TransitionRequest(BaseModel):
    target_state: CallState
    metadata: dict = Field(default_factory=dict)


class CallResponse(BaseModel):
    call_id: UUID
    phone_number: str
    status: str
