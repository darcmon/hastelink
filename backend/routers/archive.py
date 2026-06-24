from fastapi import APIRouter, Depends, HTTPException, Query

from fastapi.responses import StreamingResponse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.dependencies import get_current_admin
from backend.models.admin_user import AdminUser
from backend.models.location import Location
from backend.models.file_version import FileVersion
from backend.schemas.file_version import VersionArchiveResponse, FileVersionResponse
from backend.services.approval_service import approval_service
from backend.services.file_service import file_service

router = APIRouter(prefix="/admin", tags=["archive"])


@router.get("/locations/{slug}/versions", response_model=VersionArchiveResponse)
async def list_versions(
    slug: str,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    # Find the location
    result = await db.execute(
        select(Location).where(Location.slug == slug, Location.deleted_at.is_(None))
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    versions, total = await approval_service.get_versions_for_location(
        db=db,
        location_id=location.id,
        status=status,
        page=page,
        per_page=per_page,
    )

    return VersionArchiveResponse(
        location_slug=location.slug,
        location_display_name=location.display_name,
        versions=versions,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/versions/{version_id}/download")
async def download_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    version = await db.get(FileVersion, version_id)
    if not version or version.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Version not found")

    return StreamingResponse(
        file_service.stream_file(version.s3_key),
        media_type=version.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{version.original_filename}"',
        },
    )


@router.delete("/versions/{version_id}", status_code=204)
async def delete_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    try:
        await approval_service.soft_delete_version(db=db, version_id=version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
