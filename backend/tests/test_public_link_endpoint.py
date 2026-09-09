from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models.file_version import FileVersion
from backend.routers import public
from backend.services.cache_service import CacheService


@pytest.mark.asyncio
async def test_approved_link_redirects_and_uses_cache(monkeypatch):
    url = "https://example.com/handbook?lang=en#intro"
    version = SimpleNamespace(
        id=uuid4(),
        kind="link",
        status="approved",
        deleted_at=None,
        link_url=url,
        link_mode="redirect",
        s3_key=None,
        content_type=None,
        original_filename=None,
    )
    location = SimpleNamespace(
        current_approved_version_id=version.id,
    )

    db = MagicMock(spec=AsyncSession)
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result
    db.get.return_value = version

    cache = CacheService()
    cache._ttl = 60
    monkeypatch.setattr(public, "cache_service", cache)

    audit_log = AsyncMock()
    monkeypatch.setattr(public.audit_service, "log", audit_log)

    stream_file = MagicMock()
    monkeypatch.setattr(public.file_service, "stream_file", stream_file)

    app = FastAPI()
    app.include_router(public.router)
    app.dependency_overrides[get_db] = lambda: db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        first = await client.get("/handbook")

        db.execute.assert_awaited_once()
        db.get.assert_awaited_once_with(FileVersion, version.id)

        db.execute.reset_mock()
        db.get.reset_mock()

        second = await client.get("/handbook")

    for response in (first, second):
        assert response.status_code == 302
        assert response.headers["location"] == url
        assert response.headers["cache-control"] == "no-store"

    db.execute.assert_not_called()
    db.get.assert_not_called()
    stream_file.assert_not_called()
    assert audit_log.await_count == 2


@pytest.mark.parametrize("status", ["pending", "rejected", "superseded"])
@pytest.mark.asyncio
async def test_unapproved_link_is_not_served(monkeypatch, status):
    version = SimpleNamespace(
        id=uuid4(),
        kind="link",
        status=status,
        deleted_at=None,
    )
    location = SimpleNamespace(
        current_approved_version_id=version.id,
    )

    db = MagicMock(spec=AsyncSession)
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result
    db.get.return_value = version

    cache = CacheService()
    monkeypatch.setattr(public, "cache_service", cache)

    audit_log = AsyncMock()
    monkeypatch.setattr(public.audit_service, "log", audit_log)

    stream_file = MagicMock()
    monkeypatch.setattr(public.file_service, "stream_file", stream_file)

    app = FastAPI()
    app.include_router(public.router)
    app.dependency_overrides[get_db] = lambda: db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        response = await client.get("/handbook")

    assert response.status_code == 404
    assert "location" not in response.headers
    assert cache.get("handbook") is None
    stream_file.assert_not_called()
    audit_log.assert_not_called()


@pytest.mark.asyncio
async def test_approved_file_still_streams(monkeypatch):
    version = SimpleNamespace(
        id=uuid4(),
        kind="file",
        status="approved",
        deleted_at=None,
        link_url=None,
        link_mode=None,
        s3_key="uploads/handbook.pdf",
        content_type="application/pdf",
        original_filename="handbook.pdf",
    )
    location = SimpleNamespace(
        current_approved_version_id=version.id,
    )

    db = MagicMock(spec=AsyncSession)
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result
    db.get.return_value = version

    cache = CacheService()
    cache._ttl = 60
    monkeypatch.setattr(public, "cache_service", cache)

    audit_log = AsyncMock()
    monkeypatch.setattr(public.audit_service, "log", audit_log)

    async def fake_stream(s3_key):
        assert s3_key == "uploads/handbook.pdf"
        yield b"example file contents"

    monkeypatch.setattr(public.file_service, "stream_file", fake_stream)

    app = FastAPI()
    app.include_router(public.router)
    app.dependency_overrides[get_db] = lambda: db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        response = await client.get("/handbook")

    assert response.status_code == 200
    assert response.content == b"example file contents"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'inline; filename="handbook.pdf"'
    )
    assert "location" not in response.headers
    audit_log.assert_awaited_once()
