import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    """What the client sends to create a location."""
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    reminder_email: str | None = None


class LocationUpdate(BaseModel):
    """Partial update — only send the fields you want to change."""
    display_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    reminder_email: str | None = None


class LocationResponse(BaseModel):
    """What the API returns for a location."""
    id: uuid.UUID
    slug: str
    display_name: str
    description: str | None
    reminder_email: str | None
    current_approved_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    locations: list[LocationResponse]
    total: int