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
from backend.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_approve_version_returns_success_and_records_audit(monkeypatch):
    db = MagicMock(spec=AsyncSession)
    admin = SimpleNamespace(email="admin@example.com")

    version = SimpleNamespace(
        id=uuid4(),
        status="approved",
        reviewed_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
    )
    location = SimpleNamespace(slug="documents")

    approve_version = AsyncMock(return_value=(version, location))
    monkeypatch.setattr(
        approval.approval_service,
        "approve_version",
        approve_version,
    )

    # Use the real audit method so invalid arguments cannot pass unnoticed.
    audit_service = AuditService()
    monkeypatch.setattr(approval, "audit_service", audit_service)

    app = FastAPI()
    app.include_router(approval.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_admin] = lambda: admin

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/admin/versions/{version.id}/approve",
            json={"notes": "Ready to publish"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(version.id)
    assert body["status"] == "approved"
    assert body["location_slug"] == "documents"
    assert body["now_serving"] is True

    approve_version.assert_awaited_once_with(
        db=db,
        version_id=str(version.id),
        reviewed_by=admin.email,
        notes="Ready to publish",
    )

    db.add.assert_called_once()
    audit_entry = db.add.call_args.args[0]
    assert audit_entry.action == "approve"
    assert audit_entry.entity_type == "file_version"
    assert audit_entry.entity_id == version.id
    assert audit_entry.actor == admin.email
    assert audit_entry.details == {
        "location_slug": "documents",
        "notes": "Ready to publish",
    }
    db.flush.assert_awaited_once()
