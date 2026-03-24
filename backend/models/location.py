import uuid
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from backend.db.session import Base

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Points to the currently approved file version.
    # This is NULL when no file has been approved yet.
    # use_alter=True is needed because FileVersion also references Location (circular FK).
    current_approved_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_versions.id", use_alter=True),
        nullable=True,
    )

    reminder_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.now
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.now, onupdate=datetime.now
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    versions = relationship(
        "FileVersion",
        back_populates="location",
        foreign_keys="FileVersion.location_id",
    )

    current_approved_version = relationship(
        "FileVersion",
        foreign_keys=[current_approved_version_id],
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_locations_slug", "slug", postgresql_where(deleted_at.is_(None)))
    )