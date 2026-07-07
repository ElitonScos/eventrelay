"""Test fixtures.

The API is exercised offline: the asyncpg pool is replaced by a fake and the
RabbitMQ publisher is patched, so no PostgreSQL or RabbitMQ is needed to run
the suite.
"""
import os
from datetime import datetime

# Settings require these before app.config is imported.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost/")

import pytest
from fastapi.testclient import TestClient


class FakePool:
    """Minimal stand-in for an asyncpg pool used by the routers."""

    def __init__(self):
        self.row = None          # returned by fetchrow
        self.rows: list = []     # returned by fetch
        self.count = 0           # returned by fetchval
        self.executed: list = [] # recorded execute() calls

    async def fetchrow(self, query, *args):
        return self.row

    async def fetch(self, query, *args):
        return self.rows

    async def fetchval(self, query, *args):
        return self.count

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return "UPDATE 1"


def make_row(**over):
    row = {
        "id": 1,
        "event_id": "11111111-1111-1111-1111-111111111111",
        "event_type": "order.created",
        "payload": {"order_id": "abc123"},
        "status": "queued",
        "error_msg": None,
        "retry_count": 0,
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "processed_at": None,
    }
    row.update(over)
    return row


@pytest.fixture()
def fake_pool():
    return FakePool()


@pytest.fixture()
def published():
    return []


@pytest.fixture()
def client(fake_pool, published, monkeypatch):
    from app.database import get_pool
    from app.main import app
    import app.routers.events as events

    app.dependency_overrides[get_pool] = lambda: fake_pool

    async def fake_publish(event_type, event_id, payload):
        published.append((event_type, event_id, payload))

    monkeypatch.setattr(events, "publish_event", fake_publish)

    # No context manager: skip the startup hook that connects to real services.
    yield TestClient(app)
    app.dependency_overrides.clear()
