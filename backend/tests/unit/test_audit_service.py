"""Tests for audit_service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.audit_log import AuditLog
from app.services import audit_service


def _make_audit_log(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "table_name": "projects",
        "record_id": str(uuid.uuid4()),
        "action": "UPDATE",
        "field_name": "status",
        "old_value": {"status": "intake"},
        "new_value": {"status": "plan_check"},
        "changed_by": uuid.uuid4(),
        "changed_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock(spec=AuditLog)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.mark.asyncio
class TestLogAction:
    async def test_log_action_creates_record(self):
        session = AsyncMock()
        session.flush = AsyncMock()

        record_id = str(uuid.uuid4())
        changed_by = uuid.uuid4()

        result = await audit_service.log_action(
            session,
            table_name="projects",
            record_id=record_id,
            action="UPDATE",
            old_value={"status": "intake"},
            new_value={"status": "plan_check"},
            changed_by=changed_by,
            field_name="status",
        )

        # Should add an AuditLog instance to the session
        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert isinstance(added, AuditLog)
        assert added.table_name == "projects"
        assert added.record_id == record_id
        assert added.action == "UPDATE"
        assert added.changed_by == changed_by
        session.flush.assert_awaited_once()


@pytest.mark.asyncio
class TestGetAuditTrail:
    async def test_get_audit_trail_returns_history(self):
        record_id = str(uuid.uuid4())
        fake_rows = [_make_audit_log(record_id=record_id) for _ in range(3)]

        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = fake_rows
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=execute_result)

        rows = await audit_service.get_audit_trail(session, record_id=record_id, limit=50)
        assert len(rows) == 3
        session.execute.assert_awaited_once()


@pytest.mark.asyncio
class TestGetUserActivity:
    async def test_get_user_activity_filters_by_user(self):
        user_id = uuid.uuid4()
        fake_rows = [_make_audit_log(changed_by=user_id) for _ in range(2)]

        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = fake_rows
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=execute_result)

        rows = await audit_service.get_user_activity(session, user_id=user_id, limit=50)
        assert len(rows) == 2
        session.execute.assert_awaited_once()
