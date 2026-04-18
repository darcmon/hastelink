import logging
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:

    async def log(
        self,
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: UUID,
        actor: str | None = None,
        request: Request | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            details=details,
        )
        db.add(entry)
        await db.flush()
        return entry


audit_service = AuditService()