from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services import approval_service as approval_module
from backend.services.cache_service import CacheService


@pytest.mark.asyncio
async def test_approving_link_clears_old_cached_destination(monkeypatch):
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

    cache = CacheService()
    cache._ttl = 60
    cache.set(
        slug="handbook",
        version_id=old_version_id,
        s3_key=None,
        content_type=None,
        original_filename=None,
        kind="link",
        link_url="https://example.com/old",
        link_mode="redirect",
    )
    assert cache.get("handbook") is not None
    monkeypatch.setattr(approval_module, "cache_service", cache)

    db = MagicMock(spec=AsyncSession)
    db.get.side_effect = [version, location]

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
    assert cache.get("handbook") is None
    db.flush.assert_awaited_once()
