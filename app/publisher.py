import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.config import settings

logger = logging.getLogger(__name__)

_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.RobustChannel | None = None
_exchange: aio_pika.RobustExchange | None = None


async def get_exchange() -> aio_pika.RobustExchange:
    global _connection, _channel, _exchange
    if _exchange is None:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel()
        _exchange = await _channel.declare_exchange(
            settings.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )
    return _exchange


async def publish_event(event_type: str, event_id: str, payload: dict) -> None:
    exchange = await get_exchange()
    body = json.dumps({"event_id": event_id, "event_type": event_type, "payload": payload})
    message = aio_pika.Message(
        body=body.encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await exchange.publish(message, routing_key=event_type)
    logger.info("event published", extra={"event_id": event_id, "event_type": event_type})


async def close_publisher():
    global _connection, _channel, _exchange
    if _connection:
        await _connection.close()
    _connection = _channel = _exchange = None
