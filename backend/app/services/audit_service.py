"""Audit trail service for tracking all data changes."""

import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    session: AsyncSession,
    table_name: str,
    record_id: str,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    changed_by: uuid.UUID | None = None,
    field_name: str | None = None,
) -> AuditLog:
    """Log a single auditable action to the audit_log table."""
    entry = AuditLog(
        table_name=table_name,
        record_id=str(record_id),
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_audit_trail(
    session: AsyncSession,
    record_id: str,
    limit: int = 50,
) -> list[AuditLog]:
    """Return the audit history for a specific record."""
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.record_id == str(record_id))
        .order_by(AuditLog.changed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_activity(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[AuditLog]:
    """Return all auditable actions performed by a specific user."""
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.changed_by == user_id)
        .order_by(AuditLog.changed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_system_audit(
    session: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    table_filter: str | None = None,
    user_filter: uuid.UUID | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AuditLog]:
    """System-wide audit query with date range and optional filters."""
    query = (
        select(AuditLog)
        .where(AuditLog.changed_at >= start_date)
        .where(AuditLog.changed_at <= end_date)
    )

    if table_filter:
        query = query.where(AuditLog.table_name == table_filter)
    if user_filter:
        query = query.where(AuditLog.changed_by == user_filter)

    query = query.order_by(AuditLog.changed_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def export_audit_log(
    session: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    table_filter: str | None = None,
    user_filter: uuid.UUID | None = None,
    fmt: str = "json",
) -> str:
    """Export filtered audit data as JSON or CSV string."""
    rows = await get_system_audit(
        session,
        start_date=start_date,
        end_date=end_date,
        table_filter=table_filter,
        user_filter=user_filter,
        limit=10_000,
    )

    records = [
        {
            "id": str(r.id),
            "table_name": r.table_name,
            "record_id": r.record_id,
            "action": r.action,
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "changed_by": str(r.changed_by) if r.changed_by else None,
            "changed_at": r.changed_at.isoformat(),
        }
        for r in rows
    ]

    if fmt == "csv":
        if not records:
            return "id,table_name,record_id,action,field_name,old_value,new_value,changed_by,changed_at\n"
        header = ",".join(records[0].keys())
        lines = [header]
        for rec in records:
            values = []
            for v in rec.values():
                cell = json.dumps(v) if isinstance(v, dict) else str(v) if v is not None else ""
                # Escape commas inside cells
                if "," in cell or '"' in cell:
                    cell = '"' + cell.replace('"', '""') + '"'
                values.append(cell)
            lines.append(",".join(values))
        return "\n".join(lines)

    return json.dumps(records, indent=2)
