from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.schemas.file_version import (
    FileVersionResponse,
    PendingVersionResponse,
)


@pytest.mark.parametrize(
    "schema",
    [FileVersionResponse, PendingVersionResponse],
)
@pytest.mark.parametrize("kind", ["file", "link"])
def test_version_response_supports_files_and_links(schema, kind):
    is_link = kind == "link"

    payload = {
        "id": uuid4(),
        "kind": kind,
        "link_url": "https://example.com/handbook" if is_link else None,
        "link_mode": "redirect" if is_link else None,
        "original_filename": None if is_link else "handbook.pdf",
        "content_type": None if is_link else "application/pdf",
        "file_size_bytes": None if is_link else 1024,
        "version_number": 1,
        "uploaded_by": "admin@example.com",
        "uploaded_at": datetime(2026, 9, 8, tzinfo=timezone.utc),
    }

    if schema is FileVersionResponse:
        payload.update(
            {
                "location_id": uuid4(),
                "status": "pending",
                "reviewed_by": None,
                "reviewed_at": None,
                "review_notes": None,
            }
        )
    else:
        payload.update(
            {
                "location_slug": "handbook",
                "location_display_name": "Handbook",
            }
        )

    response = schema.model_validate(payload)
    body = response.model_dump(mode="json")

    assert body["kind"] == kind

    if is_link:
        assert body["link_url"] == "https://example.com/handbook"
        assert body["link_mode"] == "redirect"
        assert body["original_filename"] is None
        assert body["content_type"] is None
        assert body["file_size_bytes"] is None
    else:
        assert body["link_url"] is None
        assert body["link_mode"] is None
        assert body["original_filename"] == "handbook.pdf"
        assert body["content_type"] == "application/pdf"
        assert body["file_size_bytes"] == 1024
