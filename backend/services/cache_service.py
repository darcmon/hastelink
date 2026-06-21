import time
import logging
from dataclasses import dataclass
from uuid import UUID

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CachedVersion:
    """Everything the public route needs to serve a file, without hitting the DB."""

    version_id: UUID
    s3_key: str
    content_type: str
    original_filename: str
    cached_at: float


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
        s3_key: str,
        content_type: str,
        original_filename: str,
    ) -> None:
        self._cache[slug] = CachedVersion(
            version_id=version_id,
            s3_key=s3_key,
            content_type=content_type,
            original_filename=original_filename,
            cached_at=time.monotonic(),
        )

    def invalidate(self, slug: str) -> None:
        self._cache.pop(slug, None)


cache_service = CacheService()
