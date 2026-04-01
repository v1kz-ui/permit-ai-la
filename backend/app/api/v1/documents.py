"""Document upload / download / list / delete API."""

import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db_session
from app.core.s3 import generate_presigned_download_url, get_s3_client
from app.middleware.auth import get_current_user
from app.models.document import Document
from app.models.project import Project
from app.schemas.common import DocumentType

router = APIRouter(prefix="/documents", tags=["documents"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "heic", "dwg"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

CONTENT_TYPE_MAP = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "heic": "image/heic",
    "dwg": "application/acad",
}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    content_type: str | None
    file_size_bytes: int | None
    document_type: str

    model_config = {"from_attributes": True}


class DownloadURLResponse(BaseModel):
    url: str
    filename: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_file(file: UploadFile) -> str:
    """Validate extension and return the normalised extension."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def _get_project_for_user(
    project_id: UUID, db: AsyncSession, current_user
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role not in ("staff", "admin") and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/upload/{project_id}", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Upload a document for a project (multipart file upload, max 25 MB)."""

    project = await _get_project_for_user(project_id, db, current_user)
    ext = _validate_file(file)

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 25 MB limit")

    # Build S3 key
    doc_id = uuid_mod.uuid4()
    s3_key = f"projects/{project_id}/documents/{doc_id}.{ext}"
    content_type = CONTENT_TYPE_MAP.get(ext, "application/octet-stream")

    # Upload to S3
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.S3_BUCKET_DOCUMENTS,
        Key=s3_key,
        Body=content,
        ContentType=content_type,
    )

    # Save metadata
    document = Document(
        id=doc_id,
        project_id=project.id,
        uploaded_by=current_user.id,
        s3_key=s3_key,
        filename=file.filename or "unnamed",
        content_type=content_type,
        file_size_bytes=len(content),
        document_type=DocumentType.OTHER,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    return document


@router.get("/{project_id}", response_model=list[DocumentResponse])
async def list_documents(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """List all documents for a project."""

    await _get_project_for_user(project_id, db, current_user)

    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}/download", response_model=DownloadURLResponse)
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Get a presigned download URL for a document."""

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify project ownership
    await _get_project_for_user(document.project_id, db, current_user)

    url = generate_presigned_download_url(
        bucket=settings.S3_BUCKET_DOCUMENTS,
        key=document.s3_key,
    )

    return DownloadURLResponse(url=url, filename=document.filename)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Delete a document and its S3 object."""

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify project ownership
    await _get_project_for_user(document.project_id, db, current_user)

    # Delete from S3
    s3 = get_s3_client()
    s3.delete_object(Bucket=settings.S3_BUCKET_DOCUMENTS, Key=document.s3_key)

    # Delete from DB
    await db.delete(document)
    await db.flush()
