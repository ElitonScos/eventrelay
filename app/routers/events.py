import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Pool

from app.database import get_pool
from app.publisher import publish_event
from app.schemas import EventCreate, EventListResponse, EventResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/events", tags=["events"])


async def _db(pool: Pool = Depends(get_pool)):
    return pool


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(body: EventCreate, pool: Pool = Depends(get_pool)):
    row = await pool.fetchrow(
        """
        INSERT INTO events (event_type, payload)
        VALUES ($1, $2::jsonb)
        RETURNING id, event_id, event_type, payload, status, error_msg, retry_count, created_at, processed_at
        """,
        body.event_type,
        json.dumps(body.payload),
    )
    try:
        await publish_event(body.event_type, str(row["event_id"]), body.payload)
    except Exception as exc:
        logger.error("failed to publish event: %s", exc)
        await pool.execute(
            "UPDATE events SET status='failed', error_msg=$1 WHERE id=$2",
            str(exc), row["id"],
        )
        raise HTTPException(status_code=502, detail="failed to enqueue event")

    return _row_to_dict(row)


@router.get("", response_model=EventListResponse)
async def list_events(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    pool: Pool = Depends(get_pool),
):
    filters = ""
    args: list[Any] = [limit, offset]
    if status:
        filters = "WHERE status=$3"
        args.append(status)

    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM events {filters.replace('$3', '$1') if status else ''}",
        *([status] if status else []),
    )
    rows = await pool.fetch(
        f"""
        SELECT id, event_id, event_type, payload, status, error_msg, retry_count, created_at, processed_at
        FROM events {filters}
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        *args,
    )
    return {"data": [_row_to_dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, pool: Pool = Depends(get_pool)):
    row = await pool.fetchrow(
        """
        SELECT id, event_id, event_type, payload, status, error_msg, retry_count, created_at, processed_at
        FROM events WHERE event_id=$1
        """,
        event_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="event not found")
    return _row_to_dict(row)


def _row_to_dict(row) -> dict:
    d = dict(row)
    if isinstance(d.get("payload"), str):
        d["payload"] = json.loads(d["payload"])
    return d
