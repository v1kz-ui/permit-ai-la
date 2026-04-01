import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.common import DeliveryStatus, NotificationChannel, NotificationType


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    type: Mapped[str] = mapped_column(
        ENUM(NotificationType, name="notification_type", create_type=True),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        ENUM(NotificationChannel, name="notification_channel", create_type=True),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    delivery_status: Mapped[str] = mapped_column(
        ENUM(DeliveryStatus, name="delivery_status", create_type=True),
        nullable=False,
        default=DeliveryStatus.PENDING,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
