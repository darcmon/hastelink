from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.session import get_db
from backend.dependencies import get_current_admin
from backend.models.admin_user import AdminUser
from backend.models.location import Location
from backend.schemas.file_version import FileVersionUploadResponse
from backend.services.file_service import file_service
from backend.services.approval_service import approval_service
from backend.services.audit_service import audit_service

router = APIRouter(prefix="/admin", tags=["upload"])


@router.post(
    "/locations/{slug}/upload",
    response_model=FileVersionUploadResponse,
    status_code=201,
)
async def upload_file(
    slug: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    settings = get_settings()

    # 1. Find the location
    result = await db.execute(
        select(Location).where(Location.slug == slug, Location.deleted_at.is_(None))
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # 2. Validate content type
    if file.content_type not in settings.allowed_file_types_list:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' is not allowed. "
            f"Allowed: {', '.join(settings.allowed_file_types_list)}",
        )

    # 3. Read and validate size
    file_data = await file.read()
    file_size = len(file_data)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )

    # 4. Upload to S3
    s3_key = file_service.generate_s3_key(slug, file.filename)
    await file_service.upload_file(s3_key, file_data, file.content_type)

    # 5. Create pending version in DB
    version = await approval_service.create_pending_version(
        db=db,
        location_id=location.id,
        original_filename=file.filename,
        content_type=file.content_type,
        file_size_bytes=file_size,
        s3_key=s3_key,
        uploaded_by=admin.email,
    )

    # 6. Audit log
    await audit_service.log(
        db=db,
        action="upload",
        entity_type="file_version",
        entity_id=version.id,
        actor=admin.email,
        request=request,
        details={
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": file_size,
            "location_slug": slug,
        },
    )

    return FileVersionUploadResponse(
        id=version.id,
        location_slug=slug,
        original_filename=version.original_filename,
        version_number=version.version_number,
        status=version.status,
        uploaded_at=version.uploaded_at,
    )