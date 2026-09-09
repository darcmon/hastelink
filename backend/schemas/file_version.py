import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from backend.services.url_validator import validate_link_url


class LinkVersionCreate(BaseModel):
    """Validated input for creating a redirect link version."""

    link_url: str
    link_mode: Literal["redirect"] = "redirect"

    @field_validator("link_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_link_url(value)


class LinkVersionCreateResponse(BaseModel):
    """Returned after a link version is created for review."""

    id: uuid.UUID
    location_slug: str
    link_url: str
    link_mode: Literal["redirect"]
    version_number: int
    status: Literal["pending"]
    uploaded_at: datetime


class FileVersionResponse(BaseModel):
    """Full version details for archive views."""

    id: uuid.UUID
    location_id: uuid.UUID
    kind: Literal["file", "link"]
    link_url: str | None
    link_mode: Literal["redirect"] | None
    original_filename: str | None
    content_type: str | None
    file_size_bytes: int | None
    status: str
    version_number: int
    uploaded_by: str
    uploaded_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_notes: str | None

    model_config = {"from_attributes": True}


class FileVersionUploadResponse(BaseModel):
    """Returned after a successful upload."""

    id: uuid.UUID
    location_slug: str
    original_filename: str
    version_number: int
    status: str
    uploaded_at: datetime


class ApprovalRequest(BaseModel):
    """Optional notes when approving/rejecting."""

    notes: str | None = None


class ApprovalResponse(BaseModel):
    """Returned after approve/reject."""

    id: uuid.UUID
    status: str
    reviewed_by: str
    reviewed_at: datetime
    location_slug: str
    now_serving: bool


class PendingVersionResponse(BaseModel):
    """A pending version shown in the dashboard."""

    id: uuid.UUID
    kind: Literal["file", "link"]
    link_url: str | None
    link_mode: Literal["redirect"] | None
    location_slug: str
    location_display_name: str
    original_filename: str | None
    content_type: str | None
    file_size_bytes: int | None
    version_number: int
    uploaded_by: str
    uploaded_at: datetime


class VersionArchiveResponse(BaseModel):
    """Paginated list of versions for a location."""

    location_slug: str
    location_display_name: str
    versions: list[FileVersionResponse]
    total: int
    page: int
    per_page: int
