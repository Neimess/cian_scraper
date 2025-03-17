import asyncio
import random
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from db.database import database
from db.models import Apartment, ApartmentImage
from src.utils.loggers import log, logger
from src.web_scraper.parser import DetailParser, ListingParser
from src.web_scraper.requester import Requester


class CianScraper:
    """
    A scraper for fetching and saving real estate listings from Cian.ru.
    """

    @log
    def __init__(self, telegram_user_id: Optional[int] = None, params: Dict[str, str] = None, freeze_time: int = 0):
        """
        Initialize the scraper with optional search parameters.

        Args:
            telegram_user_id (int): Telegram user ID who called this class.
            params (dict, optional): Dictionary of search parameters for Cian.ru.
            freeze_time (int): Whether to freeze the time. Defaults 0.
        """
        self.params = params or {"deal_type": "sale", "engine_version": "2", "region": "1"}
        self.is_running = False
        self.telegram_user_id = telegram_user_id
        self.freeze_time = freeze_time
        self.semaphore = asyncio.Semaphore(3)  # TODO if fix aiohttp

    @log
    async def fetch_listings(self) -> List[str]:
        """
        Fetch a list of listing URLs from Cian.ru.

        :return: List of URLs for individual listings.
        """
        requester = Requester("https://www.cian.ru", self.params, freeze_time=self.freeze_time)
        task = asyncio.create_task(requester.fetch())
        logger.info(f"Task created at background for user {self.telegram_user_id}")
        text, status_code, _ = await task
        await asyncio.sleep(random.uniform(0, self.freeze_time))
        logger.info("Successfully fetched listing URLs")
        return self.parse_listings(text) if status_code == 200 else []

    @log
    def parse_listings(self, html: str) -> List[str]:
        """
        Parse the HTML content to extract listing URLs.

        :param html: HTML content of the listings page.
        :return: List of parsed URLs.
        """
        logger.debug("Parsing HTML to extract listing URLs")
        return ListingParser(html).parse_apartment_links()

    @log
    async def fetch_listing_details(
        self, url: str, max_retries: int = 5, backoff_factor: float = 2.0
    ) -> Optional[Dict[str, str]]:
        """
        Fetch details for a specific listing.

        :param url: URL of the listing.
        :param max_retries: Maximum number of retry attempts on failure.
        :param backoff_factor: Exponential backoff factor for retry delay.
        :return: Dictionary containing listing details or None if failed.
        """
        logger.debug(f"Fetching details for listing: {url}")

        requester = Requester(url, freeze_time=self.freeze_time)

        for attempt in range(1, max_retries + 1):
            try:
                text, status_code, _ = await requester.fetch()

                if status_code == 200:
                    logger.debug("Successfully fetched listing details")
                    details = DetailParser(text).parse_apartment_details()

                    if details:
                        details.setdefault("url", url)
                        await asyncio.sleep(random.uniform(0, self.freeze_time))
                        return details
                    else:
                        logger.warning(f"Parsing failed for {url}. Received empty details.")
                        return None

                elif status_code == 429:
                    wait_time = random.uniform(backoff_factor**attempt, backoff_factor ** (attempt + 1))
                    logger.warning(
                        f"Received 429 Too Many Requests for {url}. "
                        f"Retrying in {wait_time:.2f} seconds... (Attempt {attempt}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)

                else:
                    logger.error(f"Failed to fetch {url}. HTTP {status_code}. No retries left.")
                    break

            except Exception as e:
                logger.exception(f"Unexpected error while fetching {url}: {e}")

        logger.error(f"Giving up on {url} after {max_retries} attempts.")
        return None

    async def save_new_listings(self, urls: List[str]) -> None:
        """
        Save new listings to the database.

        :param urls: List of URLs to fetch and save.
        """
        logger.info("Saving new listings to the database")
        async with database() as session:
            new_listings = []
            for url in urls:
                if await self._is_duplicate(url):
                    logger.info(f"Listing already exists: {url}")
                    continue
                details = await self.fetch_listing_details(url)
                if details:
                    new_listings.append(details)

            if not new_listings:
                logger.info("No new listings found.")
                return

            saved_urls = []
            for det in new_listings:
                listing = Apartment(
                    title=det.get("title"),
                    price=det.get("price"),
                    description=det.get("description"),
                    address=det.get("address"),
                    date_published=det.get("date_published"),
                    rooms=det.get("rooms"),
                    area=det.get("area"),
                    url=det.get("url"),
                )
                session.add(listing)
                await session.flush()
                if isinstance(det.get("images"), list):
                    session.add_all([ApartmentImage(listing_id=listing.id, url=img_url) for img_url in det["images"]])
                saved_urls.append(det.get("url"))

            await session.commit()
            logger.info(f"New listings saved: {', '.join(saved_urls)}")

    async def _get_existing_listing(self, url: str) -> Optional[Apartment]:
        """
        Get an existing listing from the database by URL.

        :param url: URL of the listing.
        :return: Existing Apartment object or None if not found.
        """
        async with database() as session:
            result = await session.execute(select(Apartment).filter_by(url=url))
            return result.scalars().first()

    async def _is_duplicate(self, url: str) -> bool:
        """
        Check if a listing already exists in the database.

        :param url: URL of the listing to check.
        :return: True if the listing is a duplicate, False otherwise.
        """
        logger.debug(f"Checking for duplicate listing: {url}")
        async with database() as session:
            result = await session.execute(select(Apartment).filter_by(url=url))
            return result.scalars().first() is not None

    async def _get_recent_listings(self, limit: int) -> List[Dict[str, str]]:
        """
        Get the most recently added listings.

        :param limit: Maximum number of listings to return.
        :return: List of recently added listings.
        """
        async with database() as session:
            result = await session.execute(
                select(Apartment).options(selectinload(Apartment.images)).order_by(Apartment.id.desc()).limit(limit)
            )
            listings = result.scalars().all()
            return [
                {
                    "title": listing.title,
                    "address": listing.address,
                    "price": listing.price,
                    "url": listing.url,
                    "images": [img.url for img in listing.images],
                }
                for listing in listings
            ]

    async def _get_data_size(self) -> int:
        """
        Get the current size of the data (e.g., number of listings in the database).

        :return: Number of listings in the database.
        """
        async with database() as session:
            result = await session.execute(select(func.count()).select_from(Apartment))
            return result.scalar() or 0

    async def run(self) -> None:
        """
        Start the scraper in an infinite loop.
        """
        logger.info("Starting CianScraper")
        self.is_running = True
        while self.is_running:
            logger.info("Start scrapper for user %s", {self.telegram_user_id})
            urls = await self.fetch_listings()
            await self.save_new_listings(urls)
            await asyncio.sleep(random.uniform(60, 100))

    def stop(self) -> None:
        """
        Stop the scraper.
        """
        logger.info("Stopping CianScraper")
        self.is_running = False
