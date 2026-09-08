from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.approval_service import ApprovalService


@pytest.mark.asyncio
async def test_creates_pending_link_version():
    db = MagicMock(spec=AsyncSession)

    query_result = MagicMock()
    query_result.scalar.return_value = 3
    db.execute.return_value = query_result

    service = ApprovalService()
    location_id = uuid4()

    version = await service.create_pending_link_version(
        db=db,
        location_id=location_id,
        link_url="https://example.com/handbook",
        uploaded_by="admin@example.com",
    )

    assert version.location_id == location_id
    assert version.kind == "link"
    assert version.link_url == "https://example.com/handbook"
    assert version.link_mode == "redirect"
    assert version.status == "pending"
    assert version.version_number == 3
    assert version.uploaded_by == "admin@example.com"

    assert version.original_filename is None
    assert version.content_type is None
    assert version.file_size_bytes is None
    assert version.s3_key is None

    db.add.assert_called_once_with(version)
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
