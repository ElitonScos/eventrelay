# EventRelay

[![ci](https://github.com/ElitonScos/eventrelay/actions/workflows/ci.yml/badge.svg)](https://github.com/ElitonScos/eventrelay/actions/workflows/ci.yml)

Async event processing pipeline built with FastAPI, RabbitMQ, and PostgreSQL. Publishes domain events to a topic exchange, processes them through a dedicated worker with dead-letter queue support, and persists results with full retry logic.

---

## How it works

```
POST /api/v1/events
        ↓
FastAPI - persists event (status: queued)
        ↓
RabbitMQ - topic exchange (eventrelay)
        ↓
Worker - consumes, processes, updates status
        ↓
PostgreSQL - final state (processed / failed)
        ↓
Dead Letter Queue - events that exceed retry limit
```

---

## Tech Stack

- **Python 3.11** + **FastAPI**
- **aio-pika** - async RabbitMQ client
- **asyncpg** - async PostgreSQL driver
- **RabbitMQ 3.13** with Management UI
- **PostgreSQL 16**
- **Docker** + **Docker Compose**

---

## Getting Started

```bash
git clone https://github.com/ElitonScos/eventrelay.git
cd eventrelay

cp .env.example .env

docker compose up -d
```

API available at `http://localhost:8001`
RabbitMQ Management UI at `http://localhost:15672` (relay / relaypass)

---

## Environment Variables

```env
DATABASE_URL=postgresql://relayuser:relaypass@db:5432/eventrelay
RABBITMQ_URL=amqp://relay:relaypass@rabbitmq:5672/
EXCHANGE_NAME=eventrelay
QUEUE_NAME=events.processing
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/events` | Publish a new event |
| GET | `/api/v1/events` | List events (paginated, filterable by status) |
| GET | `/api/v1/events/{event_id}` | Get event by UUID |

---

## Event example

```json
{
  "event_type": "order.created",
  "payload": {
    "order_id": "abc123",
    "customer": "João Silva",
    "amount": 349.90
  }
}
```

Supported routing patterns: `order.*`, `payment.*`, `shipment.*`

---

## Reliability

- **Persistent messages** - survive RabbitMQ restarts
- **Dead Letter Queue** - failed events routed to `events.dead` after max retries
- **Retry tracking** - retry count persisted per event
- **Prefetch limit** - worker processes up to 10 messages concurrently

---

## Project Structure

```
eventrelay/
├── app/
│   ├── main.py            - FastAPI entrypoint, lifespan hooks
│   ├── config.py          - env-based configuration
│   ├── database.py        - asyncpg connection pool
│   ├── publisher.py       - RabbitMQ async publisher
│   ├── schemas.py         - Pydantic request/response models
│   └── routers/
│       └── events.py      - event endpoints
├── worker/
│   └── consumer.py        - RabbitMQ consumer with DLQ support
├── migrations/
│   └── 001_init.sql
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.worker
├── docker-compose.yml
└── .env.example
```
