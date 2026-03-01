from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    pool_suze=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

"""
    The `yield` makes this a generator — FastAPI calls it, gets the session,
    runs your route, then comes back here for cleanup (commit or rollback).
"""
async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
