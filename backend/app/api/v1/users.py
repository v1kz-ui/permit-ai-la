from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.user import NotificationPreferences, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
async def register_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = User(
        email=data.email,
        name=data.name,
        phone=data.phone,
        role=data.role,
        language=data.language,
        angeleno_id=getattr(current_user, "angeleno_id", None),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found")

    ALLOWED_USER_FIELDS = {"name", "phone", "language", "notification_push", "notification_sms", "notification_email"}
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field not in ALLOWED_USER_FIELDS:
            continue  # Silently skip protected fields
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me/notification-preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return NotificationPreferences(
        notification_push=user.notification_push,
        notification_sms=user.notification_sms,
        notification_email=user.notification_email,
        language=user.language,
    )


@router.put("/me/notification-preferences", response_model=NotificationPreferences)
async def update_notification_preferences(
    prefs: NotificationPreferences,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.notification_push = prefs.notification_push
    user.notification_sms = prefs.notification_sms
    user.notification_email = prefs.notification_email
    user.language = prefs.language

    await db.flush()
    await db.refresh(user)
    return prefs


@router.get("/me/data-export")
async def export_my_data(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """CCPA: Export all personal data as JSON."""
    from app.models.document import Document
    from app.models.notification import Notification
    from app.models.project import Project
    from app.models.clearance import Clearance

    result = await db.execute(
        select(User)
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch projects with clearances
    projects_result = await db.execute(
        select(Project)
        .where(Project.owner_id == user.id)
        .options(selectinload(Project.clearances))
    )
    projects = projects_result.scalars().all()

    # Fetch document metadata (no S3 content)
    project_ids = [p.id for p in projects]
    documents = []
    if project_ids:
        docs_result = await db.execute(
            select(Document).where(Document.project_id.in_(project_ids))
        )
        documents = docs_result.scalars().all()

    # Fetch notifications
    notifs_result = await db.execute(
        select(Notification).where(Notification.user_id == user.id)
    )
    notifications = notifs_result.scalars().all()

    def _project_dict(p: Project) -> dict:
        return {
            "id": str(p.id),
            "address": p.address,
            "apn": p.apn,
            "status": p.status,
            "pathway": p.pathway,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "clearances": [
                {
                    "id": str(c.id),
                    "department": c.department,
                    "clearance_type": c.clearance_type,
                    "status": c.status,
                }
                for c in (p.clearances or [])
            ],
        }

    def _document_dict(d: Document) -> dict:
        return {
            "id": str(d.id),
            "project_id": str(d.project_id),
            "document_type": d.document_type,
            "filename": d.filename,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }

    def _notification_dict(n: Notification) -> dict:
        return {
            "id": str(n.id),
            "type": n.type,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }

    payload = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "language": user.language,
            "angeleno_id": user.angeleno_id,
        },
        "projects": [_project_dict(p) for p in projects],
        "documents": [_document_dict(d) for d in documents],
        "notifications": [_notification_dict(n) for n in notifications],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/me/account", status_code=204)
async def delete_my_account(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """CCPA: Delete account and all personal data."""
    import logging

    logger = logging.getLogger(__name__)

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(
        "AUDIT: Account deletion requested for user_id=%s email=%s at %s",
        user.id,
        user.email,
        datetime.now(timezone.utc).isoformat(),
    )

    await db.delete(user)
    await db.commit()
