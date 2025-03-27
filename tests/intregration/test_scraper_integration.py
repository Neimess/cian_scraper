from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from db.database import get_session, init_db, init_engine
from src.web_scraper.scraper import CianScraper

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

init_engine(
    database_url=TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest_asyncio.fixture(scope="function")
async def test_db():
    await init_db()

    async with get_session() as session:
        async with session.begin():
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            for table in tables:
                await session.execute(text(f"DELETE FROM {table}"))
            await session.commit()

        yield session


@pytest.mark.asyncio
async def test_save_new_listings(test_db):
    dummy_detail = {
        "title": "Dummy Apt",
        "price": 1000.0,
        "description": "Test apt",
        "address": "Test address",
        "date_published": datetime.strptime("2025-03-18", "%Y-%m-%d").replace(tzinfo=timezone.utc).date(),
        "rooms": "2",
        "area": "50",
        "url": "http://example.com/listing1",
        "images": ["http://example.com/image1"],
    }

    async def fake_fetch_details(url):
        return dummy_detail.copy()

    async def fake_is_duplicate(self, url, session):
        return False

    scraper = CianScraper()
    scraper.saver._is_duplicate = fake_is_duplicate.__get__(scraper.saver)

    await scraper.saver.save(["http://example.com/listing1"], fake_fetch_details, test_db)

    result = await test_db.execute(text("SELECT COUNT(*) FROM apartments"))
    count = result.scalar()

    assert count == 1


@pytest.mark.asyncio
async def test_save_existing_listing_is_skipped(test_db):
    dummy_detail = {
        "title": "Existing Apt",
        "price": 1200.0,
        "description": "Already in DB",
        "address": "Already in DB address",
        "date_published": datetime.strptime("2025-03-18", "%Y-%m-%d").replace(tzinfo=timezone.utc).date(),
        "rooms": "3",
        "area": "60",
        "url": "http://example.com/listing2",
        "images": ["http://example.com/image2"],
    }

    async def fake_fetch_details(url):
        return dummy_detail.copy()

    call_count = {"count": 0}

    async def fake_is_duplicate(self, url, session):
        if call_count["count"] == 0:
            call_count["count"] += 1
            return False
        return True

    scraper = CianScraper()
    scraper.saver._is_duplicate = fake_is_duplicate.__get__(scraper.saver)

    await scraper.saver.save(["http://example.com/listing2"], fake_fetch_details, test_db)
    await scraper.saver.save(["http://example.com/listing2"], fake_fetch_details, test_db)

    result = await test_db.execute(text("SELECT COUNT(*) FROM apartments"))
    count = result.scalar()

    assert count == 1


@pytest.mark.asyncio
async def test_save_multiple_listings(test_db):
    details_1 = {
        "title": "Apt 1",
        "price": 2000.0,
        "description": "Test apt 1",
        "address": "Address 1",
        "date_published": datetime.strptime("2025-03-18", "%Y-%m-%d").replace(tzinfo=timezone.utc).date(),
        "rooms": "2",
        "area": "45",
        "url": "http://example.com/listing3",
        "images": ["http://example.com/image3_1", "http://example.com/image3_2"],
    }
    details_2 = {
        "title": "Apt 2",
        "price": 3000.0,
        "description": "Test apt 2",
        "address": "Address 2",
        "date_published": datetime.strptime("2025-03-18", "%Y-%m-%d").replace(tzinfo=timezone.utc).date(),
        "rooms": "1",
        "area": "30",
        "url": "http://example.com/listing4",
        "images": ["http://example.com/image4_1"],
    }

    async def fake_fetch_details(url):
        return details_1 if url.endswith("listing3") else details_2

    async def fake_is_duplicate(self, url, session):
        return False

    scraper = CianScraper()
    scraper.saver._is_duplicate = fake_is_duplicate.__get__(scraper.saver)

    await scraper.saver.save(
        [
            "http://example.com/listing3",
            "http://example.com/listing4",
        ],
        fake_fetch_details,
        test_db,
    )

    result = await test_db.execute(text("SELECT COUNT(*) FROM apartments"))
    count = result.scalar()

    assert count == 2


@pytest.mark.asyncio
async def test_save_listing_details_is_none(test_db):
    async def fake_fetch_details(url):
        return None

    async def fake_is_duplicate(self, url, session):
        return False

    scraper = CianScraper()
    scraper.saver._is_duplicate = fake_is_duplicate.__get__(scraper.saver)

    await scraper.saver.save(["http://example.com/non_parsed_listing"], fake_fetch_details, test_db)

    result = await test_db.execute(text("SELECT COUNT(*) FROM apartments"))
    count = result.scalar()

    assert count == 0
