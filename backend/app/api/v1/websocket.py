"""WebSocket endpoint for real-time project updates.

Provides per-project real-time feeds for clearance changes,
permit status changes, and inspection scheduling events.
"""

import asyncio
import json

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import settings
from app.core.redis import get_redis

logger = structlog.get_logger()

router = APIRouter(tags=["websocket"])

HEARTBEAT_INTERVAL = 30  # seconds


async def _authenticate_ws(token: str | None) -> dict | None:
    """Authenticate WebSocket connection via query param token.

    In mock auth mode, returns a mock user. Otherwise validates the JWT.
    """
    if settings.MOCK_AUTH:
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "role": "admin",
        }

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["RS256"],
        )
        return {
            "id": payload.get("sub"),
            "role": payload.get("role", "homeowner"),
        }
    except JWTError:
        return None


@router.websocket("/ws/{project_id}")
async def project_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str | None = Query(None),
):
    """Per-project real-time feed via WebSocket.

    Subscribes to Redis pub/sub channels for the project and forwards
    events (clearance_changed, permit_changed, inspection_scheduled)
    as JSON messages.

    Query params:
        token: Authentication token.
    """
    # Authenticate
    user = await _authenticate_ws(token)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    await websocket.accept()
    logger.info("WebSocket connected", project_id=project_id, user_id=user["id"])

    redis = await get_redis()
    pubsub = redis.pubsub()

    # Subscribe to project-specific channels
    channels = [
        f"project:{project_id}:clearance_changed",
        f"project:{project_id}:permit_changed",
        f"project:{project_id}:inspection_scheduled",
    ]

    try:
        await pubsub.subscribe(*channels)

        # Create tasks for message listening and heartbeat
        async def listen_messages():
            """Listen for Redis pub/sub messages and forward to WebSocket."""
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message["type"] == "message":
                    channel = message["channel"]
                    # Extract event type from channel name
                    event_type = channel.split(":")[-1]
                    try:
                        data = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = {"raw": message["data"]}

                    await websocket.send_json({
                        "event": event_type,
                        "project_id": project_id,
                        "data": data,
                    })
                else:
                    await asyncio.sleep(0.1)

        async def heartbeat():
            """Send ping every HEARTBEAT_INTERVAL seconds to keep connection alive."""
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    await websocket.send_json({"event": "ping", "project_id": project_id})
                except Exception:
                    break

        # Run both tasks concurrently
        listen_task = asyncio.create_task(listen_messages())
        heartbeat_task = asyncio.create_task(heartbeat())

        try:
            # Wait for incoming messages from client (to detect disconnection)
            while True:
                data = await websocket.receive_text()
                # Handle client pong or other messages
                try:
                    msg = json.loads(data)
                    if msg.get("event") == "pong":
                        continue
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", project_id=project_id, user_id=user["id"])
        finally:
            listen_task.cancel()
            heartbeat_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error("WebSocket error", project_id=project_id, error=str(e))
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()
        logger.info("WebSocket cleanup complete", project_id=project_id)
