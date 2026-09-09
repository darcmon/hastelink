import time
import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CachedVersion:
    """Everything the public route needs to serve a file or redirect."""

    version_id: UUID
    s3_key: str | None
    content_type: str | None
    original_filename: str | None
    cached_at: float
    kind: Literal["file", "link"] = "file"
    link_url: str | None = None
    link_mode: Literal["redirect"] | None = None


class CacheService:
    def __init__(self):
        self._cache: dict[str, CachedVersion] = {}
        self._ttl = get_settings().cache_ttl_seconds

    def get(self, slug: str) -> CachedVersion | None:
        entry = self._cache.get(slug)
        if entry and (time.monotonic() - entry.cached_at) < self._ttl:
            return entry
        if entry:
            del self._cache[slug]
        return None

    def set(
        self,
        slug: str,
        version_id: UUID,
        s3_key: str | None,
        content_type: str | None,
        original_filename: str | None,
        kind: Literal["file", "link"] = "file",
        link_url: str | None = None,
        link_mode: Literal["redirect"] | None = None,
    ) -> None:
        self._cache[slug] = CachedVersion(
            version_id=version_id,
            s3_key=s3_key,
            content_type=content_type,
            original_filename=original_filename,
            cached_at=time.monotonic(),
            kind=kind,
            link_url=link_url,
            link_mode=link_mode,
        )

    def invalidate(self, slug: str) -> None:
        self._cache.pop(slug, None)


cache_service = CacheService()
