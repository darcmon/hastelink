from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.location import Location
from backend.models.file_version import FileVersion

from backend.services.cache_service import cache_service


class ApprovalService:
    async def approve_version(
        self,
        db: AsyncSession,
        version_id: UUID,
        reviewed_by: str,
        notes: str | None = None,
    ) -> tuple[FileVersion, Location]:
        version = await db.get(FileVersion, version_id)

        if not version:
            raise ValueError("Version not found")
        if version.status != "pending":
            raise ValueError(f"Cannot approve version with status '{version.status}'")
        if version.deleted_at is not None:
            raise ValueError("Cannot approve a deleted version")

        location = await db.get(Location, version.location_id)
        if not location:
            raise ValueError("Location not found")

        await db.execute(
            update(FileVersion)
            .where(
                FileVersion.location_id == version.location_id,
                FileVersion.status == "approved",
                FileVersion.deleted_at.is_(None),
            )
            .values(status="superseded")
        )

        now = datetime.now(timezone.utc)
        version.status = "approved"
        version.reviewed_by = reviewed_by
        version.reviewed_at = now
        version.review_notes = notes

        location.current_approved_version_id = version.id
        location.updated_at = now

        await db.flush()
        cache_service.invalidate(location.slug)
        return version, location

    async def reject_version(
        self,
        db: AsyncSession,
        version_id: UUID,
        reviewed_by: str,
        notes: str | None = None,
    ) -> FileVersion:
        version = await db.get(FileVersion, version_id)
        if not version:
            raise ValueError("Version not found")
        if version.status != "pending":
            raise ValueError(f"Cannot reject version with status '{version.status}'")

        version.status = "rejected"
        version.reviewed_by = reviewed_by
        version.reviewed_at = datetime.now(timezone.utc)
        version.review_notes = notes

        await db.flush()
        return version

    async def get_pending_versions(self, db: AsyncSession) -> list[FileVersion]:
        result = await db.execute(
            select(FileVersion)
            .where(
                FileVersion.status == "pending",
                FileVersion.deleted_at.is_(None),
            )
            .order_by(FileVersion.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def get_next_version_number(self, db: AsyncSession, location_id: UUID) -> int:
        result = await db.execute(
            select(func.coalesce(func.max(FileVersion.version_number), 0) + 1).where(
                FileVersion.location_id == location_id
            )
        )
        return result.scalar()

    async def create_pending_version(
        self,
        db: AsyncSession,
        location_id: UUID,
        original_filename: str,
        content_type: str,
        file_size_bytes: int,
        s3_key: str,
        uploaded_by: str,
    ) -> FileVersion:
        version_number = await self.get_next_version_number(db, location_id)
        version = FileVersion(
            location_id=location_id,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            s3_key=s3_key,
            uploaded_by=uploaded_by,
            version_number=version_number,
            status="pending",
        )
        db.add(version)
        await db.flush()
        return version

    async def get_versions_for_location(
        self,
        db: AsyncSession,
        location_id: UUID,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[FileVersion], int]:
        """
        Returns (versions, total_count) for pagination.

        The query is built in two parts:
        1. A count query to get the total matching rows
        2. A data query to get just the current page

        Both share the same WHERE clause so the count matches the data.
        """

        # Base conditions shared by both queries
        base_conditions = [
            FileVersion.location_id == location_id,
            FileVersion.deleted_at.is_(None),
        ]

        if status:
            base_conditions.append(FileVersion.status == status)

        # Count query
        count_query = select(func.count(FileVersion.id)).where(*base_conditions)
        total = (await db.execute(count_query)).scalar()

        # Data query
        data_query = (
            select(FileVersion)
            .where(*base_conditions)
            .order_by(FileVersion.uploaded_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        versions = (await db.execute(data_query)).scalars().all()

        return versions, total

    async def soft_delete_version(
        self,
        db: AsyncSession,
        version_id: UUID,
    ) -> FileVersion:
        version = await db.get(FileVersion, version_id)
        if not version:
            raise ValueError("Version not found")
        if version.status == "approved":
            raise ValueError("Cannot delete an approved version")

        version.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return version


approval_service = ApprovalService()
