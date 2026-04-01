"""Chat API endpoint for AI-powered permit Q&A."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.middleware.auth import get_current_user
from app.models.project import Project
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

# ---------------------------------------------------------------------------
# Redis-backed rate limiter: 20 messages per hour per user
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW = 3600  # seconds


async def _check_rate_limit(user_id: str) -> None:
    """Redis-backed rate limit: 20 chat messages per hour per user."""
    try:
        from app.core.redis import get_redis_client
        redis = await get_redis_client()
        key = f"chat_ratelimit:{user_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, RATE_LIMIT_WINDOW)
        if count > RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. You can send up to 20 messages per hour.",
            )
    except HTTPException:
        raise
    except Exception:
        # If Redis is unavailable, allow the request (fail open)
        pass


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    sources: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

_chat_service = ChatService()


@router.post("/{project_id}", response_model=ChatResponse)
async def chat_with_project(
    project_id: UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Send a message about a project and receive an AI-powered response."""

    # Rate limit
    await _check_rate_limit(str(current_user.id))

    # Fetch project and validate ownership
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build parcel context for the AI
    clearances_data = []
    for c in project.clearances:
        clearances_data.append(
            {
                "department": c.department,
                "clearance_type": c.clearance_type,
                "status": c.status,
                "is_bottleneck": c.is_bottleneck,
            }
        )

    parcel_context = {
        "address": project.address,
        "pathway": project.pathway,
        "status": project.status,
        "is_coastal_zone": project.is_coastal_zone,
        "is_hillside": project.is_hillside,
        "is_very_high_fire_severity": project.is_very_high_fire_severity,
        "is_historic": project.is_historic,
        "original_sqft": project.original_sqft,
        "proposed_sqft": project.proposed_sqft,
        "stories": project.stories,
        "clearances": clearances_data,
    }

    result = await _chat_service.chat(
        project_id=str(project_id),
        user_message=body.message,
        conversation_history=body.conversation_history,
        parcel_context=parcel_context,
    )

    return ChatResponse(response=result["response"], sources=result["sources"])
