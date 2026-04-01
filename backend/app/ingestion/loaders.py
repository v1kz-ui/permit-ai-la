"""Database loading and dead-letter handling for ingested permit records."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.project import Project

logger = structlog.get_logger(__name__)

# Columns that should be updated when a conflict on the unique permit number
# is detected.  We deliberately exclude the primary key, owner_id, and
# created_at so those remain stable.
_UPSERT_UPDATE_COLUMNS = [
    "address",
    "apn",
    "status",
    "pathway",
    "description",
    "original_sqft",
    "proposed_sqft",
    "stories",
    "is_coastal_zone",
    "is_hillside",
    "is_very_high_fire_severity",
    "is_historic",
    "application_date",
    "issued_date",
    "updated_at",
]


async def upsert_permits(
    session: AsyncSession,
    records: list[dict],
) -> int:
    """Upsert permit records into the ``projects`` table.

    Uses PostgreSQL ``INSERT ... ON CONFLICT (ladbs_permit_number) DO UPDATE``
    so that new records are inserted and existing records are updated in a
    single round-trip per batch.

    Returns the number of rows affected.
    """
    if not records:
        return 0

    # Only keep keys that exist as actual columns on the Project table.
    valid_columns = {c.key for c in sa_inspect(Project).mapper.column_attrs}

    cleaned: list[dict] = []
    for rec in records:
        row = {k: v for k, v in rec.items() if k in valid_columns}
        # Ensure the conflict key is present.
        if not row.get("ladbs_permit_number"):
            logger.warning("loader.missing_permit_number", record=rec)
            continue
        cleaned.append(row)

    if not cleaned:
        return 0

    stmt = pg_insert(Project).values(cleaned)

    # Build the SET clause for the ON CONFLICT ... DO UPDATE.
    update_dict = {
        col: getattr(stmt.excluded, col)
        for col in _UPSERT_UPDATE_COLUMNS
        if col in valid_columns
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=["ladbs_permit_number"],
        set_=update_dict,
    )

    result = await session.execute(stmt)
    await session.flush()

    rowcount = result.rowcount  # type: ignore[union-attr]
    logger.info("loader.upsert_complete", rows_affected=rowcount, batch_size=len(cleaned))
    return rowcount


async def dead_letter(
    record: dict,
    error: str,
    s3_client: object,
) -> None:
    """Serialize a failed record to the S3 dead-letter bucket for later inspection.

    The object key encodes the UTC timestamp and permit number (if available)
    so operators can locate failures quickly.
    """
    now = datetime.now(timezone.utc)
    permit_nbr = record.get("ladbs_permit_number") or record.get("permit_nbr") or "unknown"
    key = f"dead-letters/{now:%Y/%m/%d}/{now:%H%M%S}_{permit_nbr}.json"

    body = json.dumps(
        {
            "record": record,
            "error": error,
            "timestamp": now.isoformat(),
        },
        default=str,
    )

    try:
        s3_client.put_object(  # type: ignore[union-attr]
            Bucket=settings.S3_BUCKET_DEAD_LETTERS,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("loader.dead_letter_written", key=key)
    except Exception:
        logger.exception("loader.dead_letter_failed", key=key)
