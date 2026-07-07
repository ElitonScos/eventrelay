"""Validation tests for the request/response schemas."""
import pytest
from pydantic import ValidationError

from app.schemas import EventCreate


def test_event_create_accepts_valid_payload():
    ev = EventCreate(event_type="payment.approved", payload={"amount": 199.9})
    assert ev.event_type == "payment.approved"
    assert ev.payload["amount"] == 199.9


def test_event_create_requires_event_type():
    with pytest.raises(ValidationError):
        EventCreate(payload={"amount": 1})


def test_event_create_requires_payload():
    with pytest.raises(ValidationError):
        EventCreate(event_type="order.created")
