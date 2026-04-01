from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.common import Language, UserRole


class UserCreate(BaseModel):
    email: str
    name: str
    phone: str | None = None
    role: UserRole = UserRole.HOMEOWNER
    language: Language = Language.EN


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    language: Language | None = None
    firebase_token: str | None = None
    notification_push: bool | None = None
    notification_sms: bool | None = None
    notification_email: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    angeleno_id: str | None
    email: str
    name: str
    phone: str | None
    role: UserRole
    language: Language
    notification_push: bool
    notification_sms: bool
    notification_email: bool

    model_config = {"from_attributes": True}


class NotificationPreferences(BaseModel):
    notification_push: bool
    notification_sms: bool
    notification_email: bool
    language: Language
