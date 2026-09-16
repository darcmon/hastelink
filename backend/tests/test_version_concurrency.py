import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.models import FileVersion, Location
from backend.services.approval_service import ApprovalService


@pytest_asyncio.fixture
async def version_database():
    url = os.environ.get("PHASE1_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a migrated disposable PostgreSQL database")
    engine = create_async_engine(url, isolation_level="READ COMMITTED")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    location_id = uuid4()

    try:
        async with engine.begin() as connection:
            await connection.execute(
                insert(Location).values(
                    id=location_id,
                    slug=f"concurrency-{location_id}",
                    display_name="Concurrency test",
                )
            )

        yield engine, sessions, location_id
    finally:
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    update(Location)
                    .where(Location.id == location_id)
                    .values(current_approved_version_id=None)
                )
                await connection.execute(
                    delete(FileVersion).where(FileVersion.location_id == location_id)
                )
                await connection.execute(
                    delete(Location).where(Location.id == location_id)
                )
        finally:
            await engine.dispose()


@pytest.mark.parametrize("first_kind", ["file", "link"])
@pytest.mark.parametrize("second_kind", ["file", "link"])
@pytest.mark.asyncio
async def test_concurrent_submissions_get_distinct_numbers(
    version_database, first_kind, second_kind
):
    engine, sessions, location_id = version_database
    service = ApprovalService()

    async def create_version(db, kind, label):
        if kind == "link":
            return await service.create_pending_link_version(
                db=db,
                location_id=location_id,
                link_url=f"https://example.com/{label}",
                uploaded_by=f"{label}@example.com",
            )

        return await service.create_pending_version(
            db=db,
            location_id=location_id,
            original_filename=f"{label}.pdf",
            content_type="application/pdf",
            file_size_bytes=100,
            s3_key=f"test/{location_id}/{label}.pdf",
            uploaded_by=f"{label}@example.com",
        )

    async with sessions() as first_db, sessions() as second_db:
        first_pid = await first_db.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second_db.scalar(text("SELECT pg_backend_pid()"))

        first = await create_version(first_db, first_kind, "first")
        assert first.version_number == 1

        second_task = asyncio.create_task(
            create_version(second_db, second_kind, "second")
        )

        try:
            # Ask PostgreSQL whether A is blocking B.
            async with engine.connect() as observer:
                async with asyncio.timeout(5):
                    while True:
                        blockers = await observer.scalar(
                            text("SELECT pg_blocking_pids(:pid)"),
                            {"pid": second_pid},
                        )
                        if first_pid in blockers:
                            break

                        assert (
                            not second_task.done()
                        ), "Second submission finished without waiting"
                        await asyncio.sleep(0.05)

            assert not second_task.done()

            # Committing A releases its lock, allowing B to continue.
            await first_db.commit()

            second = await asyncio.wait_for(second_task, timeout=5)
            assert second.version_number == 2
            await second_db.commit()

        finally:
            if not second_task.done():
                second_task.cancel()
            await asyncio.gather(second_task, return_exceptions=True)

    # Verify that both versions were actually committed.
    async with sessions() as db:
        numbers = await db.scalars(
            select(FileVersion.version_number)
            .where(FileVersion.location_id == location_id)
            .order_by(FileVersion.version_number)
        )
        assert list(numbers) == [1, 2]


@pytest.mark.asyncio
async def test_concurrent_approvals_leave_one_approved_version(version_database):
    engine, sessions, location_id = version_database
    service = ApprovalService()

    # Create two pending versions and make them visible to both sessions.
    async with sessions() as setup_db:
        first = await service.create_pending_link_version(
            db=setup_db,
            location_id=location_id,
            link_url="https://example.com/first",
            uploaded_by="test@example.com",
        )
        second = await service.create_pending_link_version(
            db=setup_db,
            location_id=location_id,
            link_url="https://example.com/second",
            uploaded_by="test@example.com",
        )
        await setup_db.commit()
        first_id = first.id
        second_id = second.id

    async with sessions() as first_db, sessions() as second_db:
        first_pid = await first_db.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second_db.scalar(text("SELECT pg_backend_pid()"))

        await service.approve_version(
            db=first_db,
            version_id=first_id,
            reviewed_by="first-admin@example.com",
        )

        # The first approval has not committed yet.
        second_task = asyncio.create_task(
            service.approve_version(
                db=second_db,
                version_id=second_id,
                reviewed_by="second-admin@example.com",
            )
        )

        try:
            async with engine.connect() as observer:
                async with asyncio.timeout(5):
                    while True:
                        blockers = await observer.scalar(
                            text("SELECT pg_blocking_pids(:pid)"),
                            {"pid": second_pid},
                        )
                        if first_pid in blockers:
                            break

                        assert (
                            not second_task.done()
                        ), "Second approval finished without waiting"
                        await asyncio.sleep(0.05)

            await first_db.commit()
            await asyncio.wait_for(second_task, timeout=5)
            await second_db.commit()

        finally:
            if not second_task.done():
                second_task.cancel()
            await asyncio.gather(second_task, return_exceptions=True)

    async with sessions() as db:
        approved_ids = list(
            await db.scalars(
                select(FileVersion.id).where(
                    FileVersion.location_id == location_id,
                    FileVersion.status == "approved",
                )
            )
        )
        published_id = await db.scalar(
            select(Location.current_approved_version_id).where(
                Location.id == location_id
            )
        )

        assert approved_ids == [second_id]
        assert published_id == second_id

        first_status = await db.scalar(
            select(FileVersion.status).where(FileVersion.id == first_id)
        )
        assert first_status == "superseded"


@pytest.mark.parametrize("first_action", ["approve", "reject"])
@pytest.mark.asyncio
async def test_competing_reviews_preserve_first_decision(
    version_database, first_action
):
    engine, sessions, location_id = version_database
    service = ApprovalService()

    async with sessions() as setup_db:
        version = await service.create_pending_link_version(
            db=setup_db,
            location_id=location_id,
            link_url="https://example.com/document",
            uploaded_by="test@example.com",
        )
        await setup_db.commit()
        version_id = version.id

    if first_action == "approve":
        first_method = service.approve_version
        second_method = service.reject_version
        expected_status = "approved"
    else:
        first_method = service.reject_version
        second_method = service.approve_version
        expected_status = "rejected"

    async with sessions() as first_db, sessions() as second_db:
        first_pid = await first_db.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second_db.scalar(text("SELECT pg_backend_pid()"))

        await first_method(
            db=first_db,
            version_id=version_id,
            reviewed_by="first-admin@example.com",
        )

        second_task = asyncio.create_task(
            second_method(
                db=second_db,
                version_id=version_id,
                reviewed_by="second-admin@example.com",
            )
        )

        try:
            async with engine.connect() as observer:
                async with asyncio.timeout(5):
                    while True:
                        blockers = await observer.scalar(
                            text("SELECT pg_blocking_pids(:pid)"),
                            {"pid": second_pid},
                        )
                        if first_pid in blockers:
                            break

                        assert (
                            not second_task.done()
                        ), "Second review finished without waiting"
                        await asyncio.sleep(0.05)

            await first_db.commit()

            with pytest.raises(
                ValueError,
                match=f"status '{expected_status}'",
            ):
                await asyncio.wait_for(second_task, timeout=5)

            await second_db.rollback()

        finally:
            if not second_task.done():
                second_task.cancel()
            await asyncio.gather(second_task, return_exceptions=True)

    async with sessions() as db:
        saved_version = await db.get(FileVersion, version_id)
        saved_location = await db.get(Location, location_id)

        assert saved_version.status == expected_status
        assert saved_version.reviewed_by == "first-admin@example.com"

        expected_published_id = version_id if first_action == "approve" else None
        assert saved_location.current_approved_version_id == expected_published_id
