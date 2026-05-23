from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    event_type: str = Field(..., examples=["order.created", "payment.approved", "shipment.sent"])
    payload: dict[str, Any] = Field(..., examples=[{"order_id": "abc123", "amount": 199.90}])


class EventResponse(BaseModel):
    id: int
    event_id: UUID
    event_type: str
    payload: dict[str, Any]
    status: str
    error_msg: str | None
    retry_count: int
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    data: list[EventResponse]
    total: int
    limit: int
    offset: int
