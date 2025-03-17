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
    echo=True,
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
    async with get_session() as session:
        await session.rollback()


@pytest.mark.asyncio
async def test_save_new_listings(test_db, monkeypatch):
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

    async def fake_fetch_listing_details(self, url):
        return dummy_detail.copy()

    monkeypatch.setattr(CianScraper, "fetch_listing_details", fake_fetch_listing_details)

    async def fake_is_duplicate(self, url):
        return False

    monkeypatch.setattr(CianScraper, "_is_duplicate", fake_is_duplicate)

    scraper_instance = CianScraper()
    await scraper_instance.save_new_listings(["http://example.com/listing1"])

    async with test_db as session:
        result = await session.execute(text("SELECT COUNT(*) FROM apartments"))
        count = result.scalar()

    assert count > 0


@pytest.mark.asyncio
async def test_save_existing_listing_is_skipped(test_db, monkeypatch):
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

    async def fake_fetch_listing_details(self, url):
        return dummy_detail.copy()

    call_count = {"count": 0}

    async def fake_is_duplicate(self, url):
        if call_count["count"] == 0:
            call_count["count"] += 1
            return False
        return True

    monkeypatch.setattr(CianScraper, "fetch_listing_details", fake_fetch_listing_details)
    monkeypatch.setattr(CianScraper, "_is_duplicate", fake_is_duplicate)

    scraper_instance = CianScraper()

    await scraper_instance.save_new_listings(["http://example.com/listing2"])
    # Пытаемся добавить ту же запись повторно
    await scraper_instance.save_new_listings(["http://example.com/listing2"])

    async with test_db as session:
        result = await session.execute(text("SELECT COUNT(*) FROM apartments"))
        count = result.scalar()

    assert count == 1, f"Expected 1 record, but in db {count}."


@pytest.mark.asyncio
async def test_save_multiple_listings(test_db, monkeypatch):
    """
    Проверяет, что можно сохранять несколько новых записей за раз.
    """
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

    async def fake_fetch_listing_details(self, url):
        # Условно возвращаем разные детали для разных URL
        if url.endswith("listing3"):
            return details_1
        elif url.endswith("listing4"):
            return details_2
        return None

    async def fake_is_duplicate(self, url):
        return False

    monkeypatch.setattr(CianScraper, "fetch_listing_details", fake_fetch_listing_details)
    monkeypatch.setattr(CianScraper, "_is_duplicate", fake_is_duplicate)

    scraper = CianScraper()
    await scraper.save_new_listings(
        [
            "http://example.com/listing3",
            "http://example.com/listing4",
        ]
    )

    async with test_db as session:
        result = await session.execute(text("SELECT COUNT(*) FROM apartments"))
        count = result.scalar()

    assert count >= 2, f"Ожидалось минимум 2 новые записи, но найдено {count}."


@pytest.mark.asyncio
async def test_save_listing_details_is_none(test_db, monkeypatch):
    async def fake_fetch_listing_details(self, url):
        return None

    async def fake_is_duplicate(self, url):
        return False

    monkeypatch.setattr(CianScraper, "fetch_listing_details", fake_fetch_listing_details)
    monkeypatch.setattr(CianScraper, "_is_duplicate", fake_is_duplicate)

    scraper = CianScraper()
    await scraper.save_new_listings(["http://example.com/non_parsed_listing"])

    async with test_db as session:
        result = await session.execute(text("SELECT COUNT(*) FROM apartments"))
        count = result.scalar()

    assert count == 0, "Объект с None-данными не должен был добавляться в базу."


@pytest.mark.asyncio
async def test_fetch_listings_integration(monkeypatch):
    """
    Интеграционный тест метода fetch_listings. Проверяем, что метод парсит
    HTML и возвращает список URL. Здесь мы не пишем в БД, а только убеждаемся,
    что парсинг сработал правильно.
    """
    html_with_links = """
    <html>
        <body>
            <article data-name="CardComponent">
                <a class="_93444fe79c--link--eoxce" href="http://example.com/apt_101"></a>
            </article>
            <article data-name="CardComponent">
                <a class="_93444fe79c--link--eoxce" href="http://example.com/apt_102"></a>
            </article>
        </body>
    </html>
    """

    # Подменяем сетевой слой, чтобы он возвращал нашу фейковую HTML-страницу
    async def fake_fetch(self):
        return (html_with_links, 200, {"Content-Type": "text/html"})

    from src.web_scraper.requester import Requester

    monkeypatch.setattr(Requester, "fetch", fake_fetch)

    scraper = CianScraper()

    # Метод fetch_listings() внутри себя сделает Requester(...).fetch(),
    # но вызовет нашу подделку, которая вернёт html_with_links.
    urls = await scraper.fetch_listings()

    assert len(urls) == 2, f"Ожидалось 2 ссылки, но получено {len(urls)}"
    assert "http://example.com/apt_101" in urls
    assert "http://example.com/apt_102" in urls
