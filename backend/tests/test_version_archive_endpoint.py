from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_admin, get_db
from backend.routers import archive


@pytest.mark.asyncio
async def test_archive_includes_link_fields(monkeypatch):
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
        status="pending",
        version_number=1,
        uploaded_by="admin@example.com",
        uploaded_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        reviewed_by=None,
        reviewed_at=None,
        review_notes=None,
    )

    db = MagicMock(spec=AsyncSession)
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result

    admin = SimpleNamespace(email="admin@example.com")
    get_versions = AsyncMock(return_value=([version], 1))
    monkeypatch.setattr(
        archive.approval_service,
        "get_versions_for_location",
        get_versions,
    )

    app = FastAPI()
    app.include_router(archive.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/admin/locations/handbook/versions")

    assert response.status_code == 200
    body = response.json()
    assert body["location_slug"] == "handbook"
    assert body["total"] == 1
    assert len(body["versions"]) == 1

    item = body["versions"][0]
    assert item["id"] == str(version.id)
    assert item["kind"] == "link"
    assert item["link_url"] == version.link_url
    assert item["link_mode"] == "redirect"
    assert item["status"] == "pending"
    assert item["original_filename"] is None
    assert item["content_type"] is None
    assert item["file_size_bytes"] is None

    get_versions.assert_awaited_once_with(
        db=db,
        location_id=location.id,
        status=None,
        page=1,
        per_page=20,
    )


@pytest.mark.asyncio
async def test_link_download_is_rejected(monkeypatch):
    version = SimpleNamespace(
        id=uuid4(),
        kind="link",
        deleted_at=None,
    )

    db = MagicMock(spec=AsyncSession)
    db.get.return_value = version
    admin = SimpleNamespace(email="admin@example.com")

    stream_file = MagicMock()
    monkeypatch.setattr(
        archive.file_service,
        "stream_file",
        stream_file,
    )

    app = FastAPI()
    app.include_router(archive.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(f"/admin/versions/{version.id}/download")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Link versions do not have a downloadable file"
    )
    stream_file.assert_not_called()
