from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import session as session_module


@pytest.mark.parametrize("outcome", ["success", "route_error", "commit_error"])
@pytest.mark.asyncio
async def test_cache_invalidation_follows_transaction_outcome(monkeypatch, outcome):
    db = MagicMock(spec=AsyncSession)
    db.info = {}
    events = []

    async def commit():
        events.append("commit")
        if outcome == "commit_error":
            raise RuntimeError("Commit failed")

    async def rollback():
        events.append("rollback")

    db.commit.side_effect = commit
    db.rollback.side_effect = rollback

    factory = MagicMock()
    factory.return_value.__aenter__.return_value = db
    monkeypatch.setattr(session_module, "async_session_factory", factory)

    cache = MagicMock()
    cache.invalidate.side_effect = lambda slug: events.append(f"invalidate:{slug}")
    monkeypatch.setattr(session_module, "cache_service", cache)

    dependency = session_module.get_db()

    try:
        supplied_db = await anext(dependency)
        assert supplied_db is db

        db.info["cache_invalidation_slugs"] = {"handbook"}
        cache.invalidate.assert_not_called()

        if outcome == "route_error":
            with pytest.raises(RuntimeError, match="Route failed"):
                await dependency.athrow(RuntimeError("Route failed"))
        elif outcome == "commit_error":
            with pytest.raises(RuntimeError, match="Commit failed"):
                await anext(dependency)
        else:
            with pytest.raises(StopAsyncIteration):
                await anext(dependency)
    finally:
        await dependency.aclose()

    if outcome == "success":
        assert events == ["commit", "invalidate:handbook"]
        cache.invalidate.assert_called_once_with("handbook")
        db.rollback.assert_not_awaited()
    elif outcome == "route_error":
        assert events == ["rollback"]
        cache.invalidate.assert_not_called()
        db.commit.assert_not_awaited()
    else:
        assert events == ["commit", "rollback"]
        cache.invalidate.assert_not_called()

    assert "cache_invalidation_slugs" not in db.info
    db.close.assert_awaited()
