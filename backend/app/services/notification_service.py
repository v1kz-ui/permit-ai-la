"""Notification service -- push, SMS, email with batching and logging."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from app.schemas.common import (
    ClearanceStatus,
    DeliveryStatus,
    NotificationChannel,
    NotificationType,
)

logger = structlog.get_logger(__name__)

# ── Notification templates (EN + ES) ──────────────────────────────────────────

NOTIFICATION_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    NotificationType.CLEARANCE_STATUS_CHANGED: {
        "en": {
            "title": "Clearance Update",
            "body": "Your {department} clearance is now {status}.",
        },
        "es": {
            "title": "Actualizacion de autorizacion",
            "body": "Su autorizacion de {department} ahora esta {status}.",
        },
        "ko": {
            "title": "허가 업데이트",
            "body": "{department} 허가가 현재 {status} 상태입니다.",
        },
        "zh": {
            "title": "许可更新",
            "body": "您的{department}许可现在为{status}状态。",
        },
        "tl": {
            "title": "Update ng Clearance",
            "body": "Ang iyong {department} clearance ay ngayon {status}.",
        },
    },
    NotificationType.INSPECTION_SCHEDULED: {
        "en": {
            "title": "Inspection Scheduled",
            "body": "An inspection has been scheduled for {date} at {address}.",
        },
        "es": {
            "title": "Inspeccion programada",
            "body": "Se ha programado una inspeccion para {date} en {address}.",
        },
        "ko": {
            "title": "검사 예정",
            "body": "{address}에서 {date}에 검사가 예정되었습니다.",
        },
        "zh": {
            "title": "检查已安排",
            "body": "已安排在{date}于{address}进行检查。",
        },
        "tl": {
            "title": "Naka-iskedyul na Inspeksyon",
            "body": "May naka-iskedyul na inspeksyon sa {date} sa {address}.",
        },
    },
    NotificationType.INSPECTION_RESULT: {
        "en": {
            "title": "Inspection Result",
            "body": "Your inspection at {address} resulted in: {result}.",
        },
        "es": {
            "title": "Resultado de inspeccion",
            "body": "Su inspeccion en {address} resulto en: {result}.",
        },
        "ko": {
            "title": "검사 결과",
            "body": "{address}의 검사 결과: {result}.",
        },
        "zh": {
            "title": "检查结果",
            "body": "您在{address}的检查结果为：{result}。",
        },
        "tl": {
            "title": "Resulta ng Inspeksyon",
            "body": "Ang iyong inspeksyon sa {address} ay nagresulta sa: {result}.",
        },
    },
    NotificationType.DOCUMENT_REQUIRED: {
        "en": {
            "title": "Document Required",
            "body": "A new document is required for your project at {address}: {document_type}.",
        },
        "es": {
            "title": "Documento requerido",
            "body": "Se requiere un nuevo documento para su proyecto en {address}: {document_type}.",
        },
        "ko": {
            "title": "서류 필요",
            "body": "{address} 프로젝트에 새 서류가 필요합니다: {document_type}.",
        },
        "zh": {
            "title": "需要文件",
            "body": "您在{address}的项目需要新文件：{document_type}。",
        },
        "tl": {
            "title": "Kailangan ng Dokumento",
            "body": "Kailangan ng bagong dokumento para sa iyong proyekto sa {address}: {document_type}.",
        },
    },
    NotificationType.PERMIT_STATUS_CHANGED: {
        "en": {
            "title": "Permit Status Update",
            "body": "Your permit for {address} is now {status}.",
        },
        "es": {
            "title": "Actualizacion del estado del permiso",
            "body": "Su permiso para {address} ahora esta {status}.",
        },
        "ko": {
            "title": "허가 상태 업데이트",
            "body": "{address}의 허가가 현재 {status} 상태입니다.",
        },
        "zh": {
            "title": "许可证状态更新",
            "body": "您在{address}的许可证现在为{status}状态。",
        },
        "tl": {
            "title": "Update ng Status ng Permit",
            "body": "Ang iyong permit para sa {address} ay ngayon {status}.",
        },
    },
    NotificationType.BOTTLENECK_DETECTED: {
        "en": {
            "title": "Bottleneck Detected",
            "body": "A bottleneck has been detected in your {department} clearance for {address}.",
        },
        "es": {
            "title": "Cuello de botella detectado",
            "body": "Se ha detectado un cuello de botella en su autorizacion de {department} para {address}.",
        },
        "ko": {
            "title": "병목 감지",
            "body": "{address}의 {department} 허가에서 병목이 감지되었습니다.",
        },
        "zh": {
            "title": "检测到瓶颈",
            "body": "在{address}的{department}许可中检测到瓶颈。",
        },
        "tl": {
            "title": "May Nakitang Bottleneck",
            "body": "May nakitang bottleneck sa iyong {department} clearance para sa {address}.",
        },
    },
}

# Batching TTL -- skip duplicate notification within this window (seconds)
_BATCH_TTL_SECONDS = 3600  # 1 hour


class NotificationService:
    """Sends notifications across push / SMS / email channels with batching."""

    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self._session = session
        self._redis = redis

    # ── Public entry point ─────────────────────────────────────────────────

    async def notify(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Determine recipients and deliver across enabled channels."""
        recipients = await self._resolve_recipients(payload)

        for user in recipients:
            if await self._is_batched(user.id, event_type):
                logger.info(
                    "notification_batched",
                    user_id=str(user.id),
                    event_type=event_type,
                )
                continue

            lang = user.language if user.language in ("en", "es", "ko", "zh", "tl") else "en"
            template = NOTIFICATION_TEMPLATES.get(event_type, {}).get(lang)
            if template is None:
                logger.warning(
                    "no_template",
                    event_type=event_type,
                    lang=lang,
                )
                continue

            title = template["title"]
            body = template["body"].format_map(_SafeFormatDict(payload))

            # Deliver on each enabled channel
            if user.notification_push:
                await self._send_push(user, title, body, payload, event_type)
            if user.notification_sms:
                await self._send_sms(user, body, payload, event_type)
            if user.notification_email:
                await self._log_notification(
                    user.id,
                    event_type,
                    NotificationChannel.EMAIL,
                    title,
                    body,
                    payload,
                    DeliveryStatus.PENDING,
                    note="Email delivery delegated to async worker",
                )

            await self._mark_batched(user.id, event_type)

    # ── Recipient resolution ───────────────────────────────────────────────

    async def _resolve_recipients(self, payload: dict[str, Any]) -> list[User]:
        """Look up project owner from the event payload."""
        project_id = payload.get("project_id")
        if project_id is None:
            logger.warning("no_project_id_in_payload")
            return []

        stmt = (
            select(User)
            .join(Project, Project.owner_id == User.id)
            .where(Project.id == uuid.UUID(str(project_id)))
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return [user] if user else []

    # ── Push via Firebase Cloud Messaging ──────────────────────────────────

    async def _send_push(
        self,
        user: User,
        title: str,
        body: str,
        payload: dict[str, Any],
        event_type: str,
    ) -> None:
        if not user.firebase_token:
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.PUSH,
                title,
                body,
                payload,
                DeliveryStatus.FAILED,
                note="No Firebase token registered",
            )
            return

        try:
            from firebase_admin import messaging  # type: ignore[import-untyped]

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in payload.items()},
                token=user.firebase_token,
            )
            response = await asyncio.to_thread(messaging.send, message)
            logger.info("push_sent", user_id=str(user.id), response=response)
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.PUSH,
                title,
                body,
                payload,
                DeliveryStatus.SENT,
            )
        except ImportError:
            logger.warning("firebase_admin_not_installed")
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.PUSH,
                title,
                body,
                payload,
                DeliveryStatus.FAILED,
                note="firebase-admin SDK not installed",
            )
        except Exception as exc:
            logger.error("push_failed", user_id=str(user.id), error=str(exc))
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.PUSH,
                title,
                body,
                payload,
                DeliveryStatus.FAILED,
                note=str(exc),
            )

    # ── SMS via Twilio ─────────────────────────────────────────────────────

    async def _send_sms(
        self,
        user: User,
        body: str,
        payload: dict[str, Any],
        event_type: str,
    ) -> None:
        if not user.phone:
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.SMS,
                "",
                body,
                payload,
                DeliveryStatus.FAILED,
                note="No phone number on file",
            )
            return

        try:
            from twilio.rest import Client as TwilioClient  # type: ignore[import-untyped]

            if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                raise RuntimeError("Twilio credentials not configured")

            client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = await asyncio.to_thread(
                client.messages.create,
                to=user.phone,
                from_=settings.TWILIO_FROM_NUMBER,
                body=body,
            )
            logger.info("sms_sent", user_id=str(user.id), sid=message.sid)
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.SMS,
                "",
                body,
                payload,
                DeliveryStatus.SENT,
            )
        except ImportError:
            logger.warning("twilio_not_installed")
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.SMS,
                "",
                body,
                payload,
                DeliveryStatus.FAILED,
                note="twilio SDK not installed",
            )
        except Exception as exc:
            logger.error("sms_failed", user_id=str(user.id), error=str(exc))
            await self._log_notification(
                user.id,
                event_type,
                NotificationChannel.SMS,
                "",
                body,
                payload,
                DeliveryStatus.FAILED,
                note=str(exc),
            )

    # ── Batching helpers ───────────────────────────────────────────────────

    def _batch_key(self, user_id: uuid.UUID, event_type: str) -> str:
        return f"notif:batch:{user_id}:{event_type}"

    async def _is_batched(self, user_id: uuid.UUID, event_type: str) -> bool:
        """Return True if a notification was already sent within the TTL."""
        return bool(await self._redis.exists(self._batch_key(user_id, event_type)))

    async def _mark_batched(self, user_id: uuid.UUID, event_type: str) -> None:
        """Mark this (user, event_type) as recently notified."""
        await self._redis.set(
            self._batch_key(user_id, event_type),
            "1",
            ex=_BATCH_TTL_SECONDS,
        )

    # ── Persistence ────────────────────────────────────────────────────────

    async def _log_notification(
        self,
        user_id: uuid.UUID,
        event_type: str,
        channel: NotificationChannel,
        title: str,
        body: str,
        payload: dict[str, Any],
        delivery_status: DeliveryStatus,
        note: str | None = None,
    ) -> Notification:
        """Persist every notification attempt to the notifications table."""
        notification = Notification(
            user_id=user_id,
            type=event_type,
            channel=channel,
            title=title or "(no title)",
            body=body,
            payload=payload,
            delivery_status=delivery_status,
            delivered_at=datetime.now(timezone.utc) if delivery_status == DeliveryStatus.SENT else None,
            error_message=note if delivery_status == DeliveryStatus.FAILED else None,
        )
        self._session.add(notification)
        await self._session.flush()
        logger.info(
            "notification_logged",
            notification_id=str(notification.id),
            user_id=str(user_id),
            channel=channel,
            status=delivery_status,
        )
        return notification


# ── Helpers ────────────────────────────────────────────────────────────────────


class _SafeFormatDict(dict):
    """dict subclass that returns the key placeholder for missing keys
    so ``str.format_map`` never raises ``KeyError``."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
