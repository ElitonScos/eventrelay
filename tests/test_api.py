"""API tests for the events endpoints (offline, mocked infrastructure)."""
import app.routers.events as events
from tests.conftest import make_row


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_create_event_persists_and_publishes(client, fake_pool, published):
    fake_pool.row = make_row()
    resp = client.post(
        "/api/v1/events",
        json={"event_type": "order.created", "payload": {"order_id": "abc123"}},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["event_type"] == "order.created"
    assert body["status"] == "queued"
    # The event was published exactly once.
    assert len(published) == 1
    assert published[0][0] == "order.created"


def test_create_event_marks_failed_when_publish_errors(client, fake_pool, monkeypatch):
    fake_pool.row = make_row()

    async def boom(*args, **kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(events, "publish_event", boom)

    resp = client.post(
        "/api/v1/events",
        json={"event_type": "order.created", "payload": {"x": 1}},
    )
    assert resp.status_code == 502
    # The event row was updated to failed with the error message.
    assert any("status='failed'" in q for q, _ in fake_pool.executed)


def test_list_events_returns_pagination_envelope(client, fake_pool):
    fake_pool.count = 2
    fake_pool.rows = [
        make_row(id=1),
        make_row(id=2, event_id="22222222-2222-2222-2222-222222222222"),
    ]
    resp = client.get("/api/v1/events?limit=20&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["data"]) == 2
    assert body["limit"] == 20 and body["offset"] == 0


def test_get_event_not_found(client, fake_pool):
    fake_pool.row = None
    resp = client.get("/api/v1/events/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 404


def test_get_event_found(client, fake_pool):
    fake_pool.row = make_row()
    resp = client.get("/api/v1/events/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 200
    assert resp.json()["event_id"] == "11111111-1111-1111-1111-111111111111"
