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
async def test_rejecting_reviewed_version_returns_readable_error(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    admin = SimpleNamespace(email="admin@example.com")

    reject_version = AsyncMock(
        side_effect=ValueError("Cannot reject version with status 'approved'")
    )
    monkeypatch.setattr(
        approval.approval_service,
        "reject_version",
        reject_version,
    )

    audit_log = AsyncMock()
    monkeypatch.setattr(approval.audit_service, "log", audit_log)

    app = FastAPI()
    app.include_router(approval.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin

    version_id = uuid4()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(f"/admin/versions/{version_id}/reject")

    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot reject version with status 'approved'"}
    reject_version.assert_awaited_once_with(
        db=db,
        version_id=str(version_id),
        reviewed_by=admin.email,
        notes=None,
    )
    audit_log.assert_not_called()
    db.get.assert_not_called()
