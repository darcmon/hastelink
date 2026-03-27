import uuid
from datetime import datetime
from pydantic import BaseModel


class FileVersionResponse(BaseModel):
    """Full version details for archive views."""
    id: uuid.UUID
    location_id: uuid.UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
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
    location_slug: str
    location_display_name: str
    original_filename: str
    content_type: str
    file_size_bytes: int
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