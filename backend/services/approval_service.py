from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.file_version import FileVersion

class ApprovalService:

        async def get_next_version_number(
                        self, db: AsyncSession ,location_id: UUID
        ) -> int:
            """
            Find the highest version number for this location and add 1.
            If no versions exist yet, returns 1.
        
            func.coalesce() is SQL's way of saying "if this is NULL, use
            this default instead." Without it, MAX of an empty table returns 
            NULL, and NULL + 1 = NULL.
            """
            result = await db.execute(
                  select(
                        func.coalesce(func.max(FileVersion.version_number), 0) + 1
                  ).where(FileVersion.location_id == location_id)
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
            """Create a new file version with status='pending'."""
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

approval_service = ApprovalService()