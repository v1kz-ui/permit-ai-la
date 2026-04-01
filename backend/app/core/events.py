"""Redis pub/sub event system for real-time notifications."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)

# ── Channel names ──────────────────────────────────────────────────────────────

CHANNEL_CLEARANCE_CHANGED = "clearance_changed"
CHANNEL_PERMIT_CHANGED = "permit_changed"
CHANNEL_INSPECTION_SCHEDULED = "inspection_scheduled"

ALL_CHANNELS = (
    CHANNEL_CLEARANCE_CHANGED,
    CHANNEL_PERMIT_CHANGED,
    CHANNEL_INSPECTION_SCHEDULED,
)


# ── Publishing ─────────────────────────────────────────────────────────────────


async def emit_event(
    redis: aioredis.Redis,
    channel: str,
    payload: dict[str, Any],
) -> int:
    """Publish a JSON-serialised event to *channel*.

    Returns the number of subscribers that received the message.
    """
    message = json.dumps(payload, default=str)
    subscribers = await redis.publish(channel, message)
    logger.info(
        "event_emitted",
        channel=channel,
        payload_keys=list(payload.keys()),
        subscribers=subscribers,
    )
    return subscribers


# ── Subscribing ────────────────────────────────────────────────────────────────


async def subscribe(
    redis: aioredis.Redis,
    *channels: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Async generator that yields parsed JSON events from *channels*.

    Usage::

        async for event in subscribe(redis, CHANNEL_CLEARANCE_CHANGED):
            handle(event)
    """
    pubsub = redis.pubsub()
    await pubsub.subscribe(*channels)
    logger.info("subscribed", channels=channels)

    try:
        async for raw_message in pubsub.listen():
            if raw_message["type"] != "message":
                continue

            try:
                data = json.loads(raw_message["data"])
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "event_parse_error",
                    channel=raw_message.get("channel"),
                    data=raw_message.get("data"),
                )
                continue

            yield {
                "channel": raw_message["channel"],
                "data": data,
            }
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()
