import asyncio
import random
from typing import Dict, List, Optional

import aiohttp

from db.database import database
from src.loggers import log, logger
from src.web_scraper.parser import DetailParser, ListingParser
from src.web_scraper.requester import RequesterMode, create_requester
from src.web_scraper.saver import ListingSaver


class CianScraper:
    def __init__(
        self,
        telegram_user_id: Optional[int] = None,
        params: Optional[Dict[str, str]] = None,
        freeze_time: int = 0,
    ):
        self.telegram_user_id = telegram_user_id
        self.params = params or {"deal_type": "sale", "engine_version": "2", "region": "1"}
        self.freeze_time = freeze_time
        self.is_running = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.listing_parser: ListingParser = ListingParser
        self.detail_parser: DetailParser = DetailParser
        self.saver: ListingSaver = ListingSaver()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _fetch(self, url: str, params: dict = None) -> Optional[str]:
        session = await self._get_session()
        requester = create_requester(
            url,
            params=params,
            freeze_time=self.freeze_time,
            session=session,
            mode=RequesterMode.Async,
        )
        text, status_code, _ = await requester.fetch()
        await asyncio.sleep(random.uniform(0, self.freeze_time))
        return text if status_code == 200 else None

    @log
    async def fetch_listings(self) -> List[str]:
        html = await self._fetch("https://www.cian.ru", self.params)
        return self.listing_parser(html).parse_apartment_links() if html else []

    @log
    async def fetch_listing_details(
        self, url: str, max_retries: int = 5, backoff_factor: float = 2.0
    ) -> Optional[Dict[str, str]]:
        session = await self._get_session()
        requester = create_requester(
            url,
            freeze_time=self.freeze_time,
            max_retries=max_retries,
            session=session,
            mode=RequesterMode.Async,
        )
        for attempt in range(1, max_retries + 1):
            try:
                text, status_code, _ = await requester.fetch()
                if status_code == 200:
                    details = self.detail_parser(text).parse_apartment_details()
                    if details:
                        details.setdefault("url", url)
                        await asyncio.sleep(random.uniform(0, self.freeze_time))
                        return details
                    return None
                elif status_code == 429:
                    wait = random.uniform(backoff_factor**attempt, backoff_factor ** (attempt + 1))
                    await asyncio.sleep(wait)
            except Exception as e:
                logger.exception(f"Error fetching {url}: {e}")
        return None

    async def save_new_listings(self, urls: List[str]) -> None:
        logger.info("SAVING DATA")
        async with database() as db_session:
            await self.saver.save(urls, self.fetch_listing_details, db_session, concurrency_limit=3)

    async def run(self) -> None:
        self.is_running = True
        try:
            while self.is_running:
                logger.info(f"Running scraper for user {self.telegram_user_id}")
                urls = await self.fetch_listings()
                await self.save_new_listings(urls)
                logger.info(f"Sleeping {self.telegram_user_id}")
                await asyncio.sleep(random.uniform(60, 100))
                logger.info(f"Continue {self.telegram_user_id}")
        finally:
            await self._close_session()

    def stop(self) -> None:
        self.is_running = False
