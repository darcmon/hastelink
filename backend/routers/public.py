from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.location import Location
from backend.models.file_version import FileVersion
from backend.services.file_service import file_service
from backend.services.audit_service import audit_service

router = APIRouter(tags=["public"])


@router.get("/{slug}")
async def serve_file(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Find location by the slug
    result = await db.execute(
        select(Location).where(Location.slug == slug, Location.deleted_at.is_(None))
    )
    location = result.scalar_one_or_none()
    if not location or not location.current_approved_version_id:
        raise HTTPException(status_code=404, detail="File not found")

    # 2. Get the approved file version
    version = await db.get(FileVersion, location.current_approved_version_id)
    if not version or version.deleted_at is not None:
        raise HTTPException(status_code=404, detail="File not found")

    # 3. Log the access
    await audit_service.log(
        db=db,
        action="access",
        entity_type="file_version",
        entity_id=version.id,
        request=request,
    )

    # 4. Stream the file content
    return StreamingResponse(
        file_service.stream_file(version.s3_key),
        media_type=version.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{version.original_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache, must-revalidate",
        },
    )
