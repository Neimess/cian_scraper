import asyncio
from typing import Awaitable, Callable, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Apartment, ApartmentImage
from src.loggers import logger


class ListingSaver:
    async def save(
        self,
        urls: List[str],
        fetch_details_fn: Callable[[str], Awaitable[Dict]],
        session: AsyncSession,
        concurrency_limit: int = 3,
    ) -> None:
        new_data = await self._collect_new_data(urls, fetch_details_fn, session, concurrency_limit)
        if not new_data:
            logger.info("No new listings to save.")
            return
        await self._commit_data(new_data, session)

    async def _collect_new_data(
        self,
        urls: List[str],
        fetch_details_fn: Callable[[str], Awaitable[Dict]],
        session: AsyncSession,
        concurrency_limit: int = 3,
    ) -> List[Dict]:
        semaphore = asyncio.Semaphore(concurrency_limit)
        existing_urls = await self.get_existing_urls(session)

        async def process_url(url: str) -> Dict[str, str] | None:
            async with semaphore:
                if url in existing_urls:
                    logger.debug(f"Duplicate listing found: {url}")
                    return None
                details = await fetch_details_fn(url)
                return details if details else None

        tasks = [process_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_data = []
        for result in results:
            if isinstance(result, dict):
                new_data.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Error in parallel processing: {result}")

        return new_data

    async def _commit_data(self, listings: List[Dict], session: AsyncSession) -> None:
        for det in listings:
            try:
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

                images = det.get("images")
                if isinstance(images, list):
                    session.add_all([ApartmentImage(listing_id=listing.id, url=img_url) for img_url in images])
            except Exception as e:
                logger.exception(f"Failed to save listing {det.get('url')}: {e}")

        await session.commit()

    @staticmethod
    async def get_recent_listings(session: AsyncSession, limit: int) -> List[Dict[str, str]]:
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

    @staticmethod
    async def get_data_size(session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(Apartment))
        return result.scalar() or 0

    @staticmethod
    async def get_existing_urls(session: AsyncSession) -> set[str]:
        result = await session.execute(select(Apartment.url))
        return set(result.scalars().all())
