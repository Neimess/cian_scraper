import asyncio
import itertools
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Tuple
from urllib.parse import urlencode

import aiohttp
import requests

from configs.config import settings
from src.loggers import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]


class RequesterMode(Enum):
    Async = 1
    Sync = 2


class ProxyManager:
    def __init__(self, proxies_list: list[str], local_ip_probability: float = 0.3):
        """
        :param proxies_list: List of proxies
        :param local_ip_probability: Probability of sending request with local IP.
        """
        self.proxies_list = proxies_list if proxies_list else []
        self.proxy_cycle = itertools.cycle(self.proxies_list) if self.proxies_list else None
        self.local_ip_probability = local_ip_probability

    def get_proxy(self):
        """Возвращает прокси в виде словаря или None (если используется локальный IP)"""
        if random.random() < self.local_ip_probability:
            return None  # Используем локальный IP
        if self.proxy_cycle:
            proxy = next(self.proxy_cycle)
            return {"http": proxy, "https": proxy}
        return None


class Requester(ABC):
    def __init__(
        self,
        url: str,
        params: dict = None,
        freeze_time: int = 0,
        max_retries: int = 3,
    ):
        self.params = params or {}
        self.url = f"{url.rstrip('/')}/cat.php?{urlencode(self.params)}" if self.params else url
        self.timer = freeze_time
        self.max_retries = max_retries

        self.headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://www.cian.ru/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        self.proxy_manager = ProxyManager(settings.PROXIES)
        self.proxy = self.proxy_manager.get_proxy()

        if self.proxy:
            logger.info(f"Using proxy {self.proxy}")
        else:
            logger.info("Using local IP (no proxy)")

    @abstractmethod
    async def fetch(self) -> Tuple[str, int, Dict[str, str]]:
        pass


class AsyncRequester(Requester):
    def __init__(self, *args, session: aiohttp.ClientSession | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    async def fetch(self) -> Tuple[str, int, Dict[str, str]]:
        """
        Makes a GET request to self.url, handles retries, proxy rotation, and user-agent changes.
        """
        for _ in range(1, self.max_retries + 1):
            try:
                logger.info(f"Waiting {self.timer} seconds before request...")
                await asyncio.sleep(self.timer)

                self.headers["User-Agent"] = random.choice(USER_AGENTS)

                proxy_url = self.proxy if self.proxy else None
                owns_session = False

                if not self.session:
                    self.session = aiohttp.ClientSession()
                    owns_session = True

                try:
                    async with self.session.get(
                        self.url,
                        headers=self.headers,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=15),
                        allow_redirects=True,
                    ) as response:
                        logger.info(f"Fetched {self.url} with status {response.status}")

                        if response.status == 403:
                            logger.warning("403 Forbidden: Cian blocked request. Rotating User-Agent and Proxy.")
                            self.headers["User-Agent"] = random.choice(USER_AGENTS)
                            self.proxy = self.proxy_manager.get_proxy()
                            continue

                        if response.status == 200:
                            return await response.text(), response.status, dict(response.headers)

                        logger.warning(f"Unexpected response {response.status}. Retrying...")

                finally:
                    if owns_session:
                        await self.session.close()
                        self.session = None

            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e}. Retrying...")
                self.proxy = self.proxy_manager.get_proxy()

        logger.error(f"Giving up on {self.url} after {self.max_retries} attempts.")
        return "", 500, {}


class SyncRequester(Requester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if self.proxy:
            self.session.proxies.update(self.proxy)

    def _sync_fetch(self) -> Tuple[str, int, Dict[str, str]]:
        time.sleep(self.timer)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}: Requesting {self.url}")

                response = self.session.get(
                    self.url,
                    headers=self.headers,
                    timeout=15,
                    allow_redirects=True,
                    verify=not self.proxy,
                )

                logger.info(f"Fetched {self.url} with status {response.status_code}")

                if response.status_code == 403:
                    logger.warning("403 Forbidden. Rotating User-Agent and Proxy.")
                    self.headers["User-Agent"] = random.choice(USER_AGENTS)
                    self.session.headers.update(self.headers)
                    self.proxy = self.proxy_manager.get_proxy()
                    if self.proxy:
                        self.session.proxies.update(self.proxy)
                    continue

                if response.status_code == 200:
                    return response.text, response.status_code, dict(response.headers)

                logger.warning(f"Unexpected status {response.status_code}. Retrying...")

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                self.proxy = self.proxy_manager.get_proxy()
                if self.proxy:
                    self.session.proxies.update(self.proxy)

        logger.error(f"Giving up on {self.url} after {self.max_retries} attempts.")
        return "", 500, {}

    async def fetch(self) -> Tuple[str, int, Dict[str, str]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_fetch)


def create_requester(
    url: str,
    params: dict = None,
    *,
    freeze_time: int = 0,
    max_retries: int = 3,
    mode: RequesterMode = RequesterMode.Async,
    session: aiohttp.ClientSession = None,
) -> Requester:
    """
    Фабрика для создания Requester (AsyncRequester или SyncRequester).

    :param url: Целевой URL
    :param params: GET параметры
    :param freeze_time: Задержка между запросами
    :param max_retries: Кол-во попыток
    :param mode: "Async" (по умолчанию) или "RequesterMode.Sync"
    :param session: aiohttp.ClientSession (только для async)
    :return: Requester с асинхронным fetch()
    """
    if mode == RequesterMode.Async:
        return AsyncRequester(url, params=params, freeze_time=freeze_time, max_retries=max_retries, session=session)
    elif mode == RequesterMode.Sync:
        return SyncRequester(url, params=params, freeze_time=freeze_time, max_retries=max_retries)
    else:
        raise ValueError(f"Unknown requester mode: {mode}")
