from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.dependencies import get_current_admin
from backend.models.admin_user import AdminUser
from backend.models.file_version import FileVersion
from backend.models.location import Location
from backend.schemas.file_version import (
    ApprovalRequest,
    ApprovalResponse,
    PendingVersionResponse,
)
from backend.services.approval_service import approval_service
from backend.services.audit_service import audit_service

router = APIRouter(prefix="/admin", tags=["approval"])


@router.get("/versions/pending", response_model=list[PendingVersionResponse])
async def list_pending(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """List all pending uploads across all locations."""
    versions = await approval_service.get_pending_versions(db)

    # Fetch location info for each version
    results = []
    for v in versions:
        location = await db.get(Location, v.location_id)
        results.append(
            PendingVersionResponse(
                id=v.id,
                location_slug=location.slug,
                location_display_name=location.display_name,
                original_filename=v.original_filename,
                content_type=v.content_type,
                file_size_bytes=v.file_size_bytes,
                version_number=v.version_number,
                uploaded_by=v.uploaded_by,
                uploaded_at=v.uploaded_at,
            )
        )
    return results


@router.post("/versions/{version_id}/review", response_model=ApprovalResponse)
async def approve_version(
    version_id: str,
    request: Request,
    body: ApprovalRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Approve a pending file version. It becomes the currently served file."""
    try:
        version, location = await approval_service.approve_version(
            db=db,
            version_id=version_id,
            reviewed_by=admin.email,
            notes=body.notes if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, details=str(e))

    await audit_service.log(
        db=db,
        version_id=version.id,
        actor=admin.email,
        action="approve",
        request=request,
        details={"location_slug": location.slug, "notes": body.notes if body else None},
    )

    return ApprovalResponse(
        id=version.id,
        status=version.status,
        reviewed_by=admin.email,
        reviewed_at=version.reviewed_at,
        location_slug=location.slug,
        now_serving=True,
    )


@router.post("/versions/{version_id}/approve", response_model=ApprovalResponse)
async def approve_version(
    version_id: str,
    request: Request,
    body: ApprovalRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    try:
        version, location = await approval_service.approve_version(
            db=db,
            version_id=version_id,
            reviewed_by=admin.email,
            notes=body.notes if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await audit_service.log(
        db=db,
        action="approve",
        entity_type="file_version",
        entity_id=version.id,
        actor=admin.email,
        request=request,
        details={"location_slug": location.slug, "notes": body.notes if body else None},
    )

    return ApprovalResponse(
        id=version.id,
        status=version.status,
        reviewed_by=admin.email,
        reviewed_at=version.reviewed_at,
        location_slug=location.slug,
        now_serving=True,
    )


@router.post("/versions/{version_id}/reject", response_model=ApprovalResponse)
async def reject_version(
    version_id: str,
    request: Request,
    body: ApprovalRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Reject a pending file version."""
    try:
        version = await approval_service.reject_version(
            db=db,
            version_id=version_id,
            reviewed_by=admin.email,
            notes=body.notes if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, details=str(e))

    location = await db.get(Location, version.location_id)

    await audit_service.log(
        db=db,
        version_id=version.id,
        actor=admin.email,
        action="reject",
        request=request,
        details={"location_slug": location.slug, "notes": body.notes if body else None},
    )

    return ApprovalResponse(
        id=version.id,
        status=version.status,
        reviewed_by=admin.email,
        reviewed_at=version.reviewed_at,
        location_slug=location.slug,
        now_serving=False,
    )
