from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.dependencies import get_current_admin
from backend.models.admin_user import AdminUser
from backend.models.location import Location
from backend.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationListResponse,
)

router = APIRouter(prefix="/admin/locations", tags=["locations"])


@router.get("", response_model=LocationListResponse)
async def list_locations(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(
        select(Location)
        .where(Location.deleted_at.is_(None))
        .order_by(Location.slug)
    )
    locations = result.scalars().all()
    count_result = await db.execute(
        select(func.count(Location.id)).where(Location.deleted_at.is_(None))
    )
    total = count_result.scalar()
    return LocationListResponse(locations=locations, total=total)


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(
    body: LocationCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    # Check slug uniqueness
    existing = await db.execute(
        select(Location).where(Location.slug == body.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Slug already exists")

    location = Location(
        slug=body.slug,
        display_name=body.display_name,
        description=body.description,
        reminder_email=body.reminder_email,
    )
    db.add(location)
    await db.flush()
    return location


@router.get("/{slug}", response_model=LocationResponse)
async def get_location(
    slug: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(
        select(Location).where(Location.slug == slug, Location.deleted_at.is_(None))
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{slug}", response_model=LocationResponse)
async def update_location(
    slug: str,
    body: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(
        select(Location).where(Location.slug == slug, Location.deleted_at.is_(None))
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)
    location.updated_at = datetime.now(timezone.utc)

    await db.flush()
    return location