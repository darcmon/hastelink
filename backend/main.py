import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.db.session import Base, engine, async_session_factory
from backend.dependencies import hash_password
from backend.routers.auth import router as auth_router
from backend.routers.locations import router as locations_router
from backend.routers.upload import router as upload_router
from backend.config import get_settings
from backend.models import AdminUser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at startup and once at shutdown.
    
    The code BEFORE `yield` runs at startup.
    The code AFTER `yield` runs at shutdown.
    """
    settings = get_settings()

    # Create all database tables (replace with Alembic migrations later)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    # Seed an admin user if none exists
    async with async_session_factory() as db:
        from sqlalchemy import select
        result = await db.execute(select(AdminUser).limit(1))
        if not result.scalar_one_or_none():
            admin = AdminUser(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                display_name="Admin"
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Seeded admin user: {settings.admin_email}")
    yield

    await engine.dispose()
    logger.info("Shut down")

def create_app() -> FastAPI:
    app = FastAPI(
        title="klinkrr",
        version="0.1.0",
        lifespan=lifespan
    )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
    
    app.include_router(auth_router)
    app.include_router(locations_router)
    app.include_router(upload_router)
    
    return app

app = create_app()