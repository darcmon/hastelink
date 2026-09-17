from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services import approval_service as approval_module


@pytest.mark.asyncio
async def test_approving_link_schedules_cache_invalidation():
    location_id = uuid4()
    old_version_id = uuid4()

    location = SimpleNamespace(
        id=location_id,
        slug="handbook",
        current_approved_version_id=old_version_id,
    )
    version = SimpleNamespace(
        id=uuid4(),
        location_id=location_id,
        kind="link",
        status="pending",
        deleted_at=None,
    )

    db = MagicMock(spec=AsyncSession)
    db.info = {}
    db.get.return_value = version

    location_result = MagicMock()
    location_result.scalar_one_or_none.return_value = location

    update_result = MagicMock()
    db.execute.side_effect = [location_result, update_result]

    service = approval_module.ApprovalService()
    approved, updated_location = await service.approve_version(
        db=db,
        version_id=version.id,
        reviewed_by="admin@example.com",
    )

    assert approved.status == "approved"
    assert approved.reviewed_by == "admin@example.com"
    assert approved.reviewed_at is not None
    assert updated_location.current_approved_version_id == version.id
    assert db.info["cache_invalidation_slugs"] == {"handbook"}
    db.commit.assert_not_awaited()
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(version)
