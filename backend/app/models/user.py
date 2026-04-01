from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.common import Language, UserRole

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.notification import Notification
    from app.models.project import Project


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    angeleno_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.HOMEOWNER,
    )
    language: Mapped[str] = mapped_column(
        ENUM(Language, name="language", create_type=True),
        nullable=False,
        default=Language.EN,
    )
    firebase_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_push: Mapped[bool] = mapped_column(default=True)
    notification_sms: Mapped[bool] = mapped_column(default=False)
    notification_email: Mapped[bool] = mapped_column(default=True)

    # Relationships
    projects: Mapped[list["Project"]] = relationship(back_populates="owner", lazy="selectin")
    documents: Mapped[list["Document"]] = relationship(back_populates="uploaded_by_user", lazy="noload")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", lazy="noload")
