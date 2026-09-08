from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend import dependencies
from backend.dependencies import (
    get_current_admin,
    get_db,
    get_web_risk_client,
)
from backend.routers import upload
from backend.services.web_risk_client import WebRiskClient, WebRiskError


@pytest.mark.asyncio
async def test_flagged_url_does_not_create_version(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    location = SimpleNamespace(id=uuid4(), slug="handbook")
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result

    admin = SimpleNamespace(email="admin@example.com")
    web_risk = MagicMock(spec=WebRiskClient)
    web_risk.is_flagged.return_value = True

    create_version = AsyncMock()
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_web_risk_client] = lambda: web_risk

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/handbook/link",
            json={"link_url": "https://example.com"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "URL was flagged by the safety check"
    web_risk.is_flagged.assert_awaited_once_with("https://example.com")
    create_version.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost",
        "https://example..com",
    ],
)
@pytest.mark.asyncio
async def test_invalid_url_is_rejected_before_business_logic(monkeypatch, url):
    db = MagicMock(spec=AsyncSession)
    admin = SimpleNamespace(email="admin@example.com")
    web_risk = MagicMock(spec=WebRiskClient)

    create_version = AsyncMock()
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_web_risk_client] = lambda: web_risk

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/handbook/link",
            json={"link_url": url},
        )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors[0]["loc"] == ["body", "link_url"]

    db.execute.assert_not_called()
    web_risk.is_flagged.assert_not_called()
    create_version.assert_not_called()


@pytest.mark.asyncio
async def test_web_risk_failure_does_not_create_version(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    location = SimpleNamespace(id=uuid4(), slug="handbook")

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result

    admin = SimpleNamespace(email="admin@example.com")
    web_risk = MagicMock(spec=WebRiskClient)
    web_risk.is_flagged.side_effect = WebRiskError("Web Risk request timed out")

    create_version = AsyncMock()
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_web_risk_client] = lambda: web_risk

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/handbook/link",
            json={"link_url": "https://example.com"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "URL safety checking is unavailable"
    web_risk.is_flagged.assert_awaited_once_with("https://example.com")
    create_version.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_clear_url_creates_pending_version(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    location = SimpleNamespace(id=uuid4(), slug="handbook")

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = location
    db.execute.return_value = query_result

    admin = SimpleNamespace(email="admin@example.com")
    web_risk = MagicMock(spec=WebRiskClient)
    web_risk.is_flagged.return_value = False

    url = "https://example.com/handbook?lang=en#intro"
    version = SimpleNamespace(
        id=uuid4(),
        link_url=url,
        link_mode="redirect",
        version_number=3,
        status="pending",
        uploaded_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
    )

    create_version = AsyncMock(return_value=version)
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    audit_log = AsyncMock()
    monkeypatch.setattr(upload.audit_service, "log", audit_log)

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_web_risk_client] = lambda: web_risk

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/handbook/link",
            json={"link_url": f"  {url}  "},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == str(version.id)
    assert body["location_slug"] == "handbook"
    assert body["link_url"] == url
    assert body["link_mode"] == "redirect"
    assert body["version_number"] == 3
    assert body["status"] == "pending"

    web_risk.is_flagged.assert_awaited_once_with(url)
    create_version.assert_awaited_once_with(
        db=db,
        location_id=location.id,
        link_url=url,
        uploaded_by=admin.email,
    )

    audit_log.assert_awaited_once()
    audit_arguments = audit_log.await_args.kwargs
    assert audit_arguments["entity_id"] == version.id
    assert audit_arguments["actor"] == admin.email
    assert audit_arguments["action"] == "create_link"


@pytest.mark.asyncio
async def test_missing_location_does_not_create_version(monkeypatch):
    db = MagicMock(spec=AsyncSession)

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None
    db.execute.return_value = query_result

    admin = SimpleNamespace(email="admin@example.com")
    web_risk = MagicMock(spec=WebRiskClient)

    create_version = AsyncMock()
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_web_risk_client] = lambda: web_risk

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/missing/link",
            json={"link_url": "https://example.com"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Location not found"
    web_risk.is_flagged.assert_not_called()
    create_version.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_unauthenticated_request_does_not_create_version(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    web_risk = MagicMock(spec=WebRiskClient)

    create_version = AsyncMock()
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_web_risk_client] = lambda: web_risk

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/handbook/link",
            json={"link_url": "https://example.com"},
        )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    db.execute.assert_not_called()
    web_risk.is_flagged.assert_not_called()
    create_version.assert_not_called()


@pytest.mark.asyncio
async def test_missing_web_risk_key_blocks_creation(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    admin = SimpleNamespace(email="admin@example.com")

    settings = SimpleNamespace(web_risk_api_key="")
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)

    create_version = AsyncMock()
    monkeypatch.setattr(
        upload.approval_service,
        "create_pending_link_version",
        create_version,
    )

    app = FastAPI()
    app.include_router(upload.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/admin/locations/handbook/link",
            json={"link_url": "https://example.com"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "URL safety checking is unavailable"
    db.execute.assert_not_called()
    create_version.assert_not_called()
