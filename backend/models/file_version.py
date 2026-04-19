import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, BigInteger, Integer, ForeignKey,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from backend.db.session import Base

class FileVersion(Base):
    __tablename__ = "file_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )

    # -- File metadata --

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False)

    # -- Approval workflow --
    # Status transitions: pending -> approved -> superseded
    #                     pending -> rejected
    # "superseded" means this was once approved, but a newer version replaced it.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )

    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
        )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    location = relationship(
        "Location", back_populates="versions", foreign_keys=[location_id]
    )

    __table_args__ = (
        UniqueConstraint("location_id", "version_number"),

        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'superseded')",
            name="ck_file_versions_status",
        ),

        Index(
            "idx_file_versions_location_status",
            "location_id", "status",
            postgresql_where=(deleted_at.is_(None)),
        ),

        Index(
            "idx_file_versions_pending",
            "status", "uploaded_at",
            postgresql_where=(deleted_at.is_(None)),
        ),
    )

    
