import asyncio
import json
import logging
import os
import time

import aio_pika
import asyncpg
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
DATABASE_URL = os.getenv("DATABASE_URL")
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "eventrelay")
QUEUE_NAME = os.getenv("QUEUE_NAME", "events.processing")
DLX_NAME = "eventrelay.dlx"
DLQ_NAME = "events.dead"
MAX_RETRIES = 3


async def process_event(event_id: str, event_type: str, payload: dict, pool: asyncpg.Pool) -> None:
    logger.info("processing event", extra={"event_id": event_id, "event_type": event_type})
    await asyncio.sleep(0.1)


async def handle_message(message: aio_pika.IncomingMessage, pool: asyncpg.Pool) -> None:
    async with message.process(requeue=False):
        try:
            data = json.loads(message.body)
            event_id = data["event_id"]
            event_type = data["event_type"]
            payload = data["payload"]

            row = await pool.fetchrow("SELECT id, retry_count FROM events WHERE event_id=$1", event_id)
            if not row:
                logger.warning("event not found in db: %s", event_id)
                return

            await process_event(event_id, event_type, payload, pool)

            await pool.execute(
                "UPDATE events SET status='processed', processed_at=now() WHERE event_id=$1",
                event_id,
            )
            logger.info("event processed: %s", event_id)

        except Exception as exc:
            logger.error("error processing event: %s", exc)
            retry_count = row["retry_count"] + 1 if row else 1
            if retry_count >= MAX_RETRIES:
                await pool.execute(
                    "UPDATE events SET status='failed', error_msg=$1, retry_count=$2 WHERE event_id=$3",
                    str(exc), retry_count, event_id,
                )
            else:
                await pool.execute(
                    "UPDATE events SET status='queued', retry_count=$1 WHERE event_id=$2",
                    retry_count, event_id,
                )
                raise


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger.info("worker starting")

    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
            break
        except Exception as exc:
            logger.warning("db not ready (%s), retrying...", exc)
            time.sleep(3)
    else:
        raise RuntimeError("could not connect to database")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    dlx = await channel.declare_exchange(DLX_NAME, ExchangeType.FANOUT, durable=True)
    dlq = await channel.declare_queue(DLQ_NAME, durable=True)
    await dlq.bind(dlx)

    exchange = await channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX_NAME},
    )
    await queue.bind(exchange, routing_key="#")

    logger.info("worker ready, consuming queue: %s", QUEUE_NAME)
    await queue.consume(lambda msg: handle_message(msg, pool))

    try:
        await asyncio.Future()
    finally:
        await connection.close()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
