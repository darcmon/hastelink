from uuid import uuid4

from backend.services.cache_service import CacheService


def test_invalidation_prevents_early_read_refilling_cache():
    cache = CacheService()
    slug = "handbook"

    generation = cache.get_generation()

    cache.invalidate(slug)

    cache.set(
        slug=slug,
        version_id=uuid4(),
        s3_key=None,
        content_type=None,
        original_filename=None,
        kind="link",
        link_url="https://example.com/old",
        link_mode="redirect",
        expected_generation=generation,
    )

    assert cache.get(slug) is None
