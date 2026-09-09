from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_admin, get_db
from backend.routers import approval


@pytest.mark.asyncio
async def test_pending_list_includes_link_fields(monkeypatch):
    location = SimpleNamespace(
        id=uuid4(),
        slug="handbook",
        display_name="Handbook",
    )
    version = SimpleNamespace(
        id=uuid4(),
        location_id=location.id,
        kind="link",
        link_url="https://example.com/handbook",
        link_mode="redirect",
        original_filename=None,
        content_type=None,
        file_size_bytes=None,
        version_number=1,
        uploaded_by="admin@example.com",
        uploaded_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
    )

    db = MagicMock(spec=AsyncSession)
    db.get.return_value = location
    admin = SimpleNamespace(email="admin@example.com")

    get_pending = AsyncMock(return_value=[version])
    monkeypatch.setattr(
        approval.approval_service,
        "get_pending_versions",
        get_pending,
    )

    app = FastAPI()
    app.include_router(approval.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/admin/versions/pending")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1

    item = items[0]
    assert item["id"] == str(version.id)
    assert item["location_slug"] == "handbook"
    assert item["location_display_name"] == "Handbook"
    assert item["kind"] == "link"
    assert item["link_url"] == version.link_url
    assert item["link_mode"] == "redirect"
    assert item["original_filename"] is None
    assert item["content_type"] is None
    assert item["file_size_bytes"] is None

    get_pending.assert_awaited_once_with(db)
