import asyncio
import itertools
import random
import time
from typing import Dict, Tuple
from urllib.parse import urlencode

import aiohttp
import requests

from configs.config import settings
from src.utils.loggers import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]


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


class Requester:
    def __init__(self, url: str, params: dict = None, freeze_time: int = 0, max_retries: int = 3):
        """
        :param url: Целевой URL
        :param params: GET-параметры
        :param freeze_time: Задержка перед запросом (сек)
        :param max_retries: Максимальное число повторных попыток
        """
        self.headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://www.cian.ru/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.params = params if params else {}
        self.url = f"{url.rstrip('/')}/cat.php?{urlencode(self.params)}" if self.params else url
        self.timer = freeze_time
        self.max_retries = max_retries
        self.proxy_manager = ProxyManager(settings.PROXIES)
        self.proxy = self.proxy_manager.get_proxy()

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if self.proxy:
            self.session.proxies.update(self.proxy)
            logger.info(f"Using proxy {self.proxy.get('http', self.proxy.get('https'))}")
        else:
            logger.info("Using local IP (no proxy)")

    async def fetch(self) -> Tuple[str, int, Dict[str, str]]:
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Waiting {self.timer} seconds before request...")
                time.sleep(self.timer)

                request_kwargs = {
                    "timeout": 15,
                    "allow_redirects": True,
                    "verify": bool(not self.proxy),
                }

                logger.info(f"Attempt {attempt}/{self.max_retries}: Requesting {self.url} with {request_kwargs}")

                response = self.session.get(self.url, **request_kwargs)
                logger.info(f"Fetched {self.url} with status {response.status_code}")

                if response.status_code == 403:
                    logger.warning("403 Forbidden: Cian blocked request. Changing User-Agent and Proxy.")

                    self.headers["User-Agent"] = random.choice(USER_AGENTS)
                    self.session.headers.update(self.headers)

                    self.proxy = self.proxy_manager.get_proxy()
                    if self.proxy:
                        self.session.proxies.update(self.proxy)
                        logger.info(f"Switched to new proxy {self.proxy.get('http', self.proxy.get('https'))}")
                    else:
                        logger.info("Switched to local IP (no proxy)")

                    continue

                if response.status_code == 200:
                    return response.text, response.status_code, response.headers

                logger.warning(f"Unexpected response code {response.status_code}. Retrying...")

            except requests.exceptions.SSLError:
                logger.error("SSL Error: Возможно, используется HTTP-прокси для HTTPS-запроса. Меняем прокси.")
            except requests.exceptions.ProxyError:
                logger.error("Proxy Error: Прокси не работает. Меняем прокси.")
            except requests.exceptions.Timeout:
                logger.error(f"Timeout: Запрос к {self.url} превысил лимит времени. Повторяем попытку.")
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error: {e}. Повторяем попытку.")

            self.proxy = self.proxy_manager.get_proxy()
            if self.proxy:
                self.session.proxies.update(self.proxy)
                logger.info(f"Switched to new proxy {self.proxy.get('http', self.proxy.get('https'))}")
            else:
                logger.info("Switched to local IP (no proxy)")

        logger.error(f"Giving up on {self.url} after {self.max_retries} attempts.")
        return "", 500, {}


class AsyncRequester:
    def __init__(self, url: str, params: dict[str, str] = None, freeze_time: int = 0, max_retries: int = 3):
        """
        :param url: Target URL
        :param params: Query parameters
        :param freeze_time: Delay before request
        :param max_retries: Maximum retry attempts for failed requests
        """
        self.headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://www.cian.ru/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.params = params if params else {}
        self.url = f"{url.rstrip('/')}/cat.php?{urlencode(self.params)}" if self.params else url
        self.timer = freeze_time
        self.max_retries = max_retries
        self.proxy_manager = ProxyManager(settings.PROXIES)
        self.proxy = self.proxy_manager.get_proxy()

        if self.proxy:
            logger.info(f"Using proxy {self.proxy}")
        else:
            logger.info("Using local IP (no proxy)")

    async def fetch(self) -> Tuple[str, int, Dict[str, str]]:
        """
        Makes a GET request to self.url, handles retries, proxy rotation, and user-agent changes.
        """
        for _ in range(1, self.max_retries + 1):
            try:
                logger.info(f"Waiting {self.timer} seconds before request...")
                await asyncio.sleep(self.timer)

                proxy_url = self.proxy if self.proxy else None

                async with (
                    aiohttp.ClientSession() as session,
                    session.get(
                        self.url,
                        headers=self.headers,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=15),
                        allow_redirects=True,
                    ) as response,
                ):
                    logger.info(f"Fetched {self.url} with status {response.status}")

                    if response.status == 403:
                        logger.warning("403 Forbidden: Cian blocked request. Changing User-Agent and Proxy.")
                        self.headers["User-Agent"] = random.choice(USER_AGENTS)

                        self.proxy = self.proxy_manager.get_proxy()
                        if self.proxy:
                            logger.info(f"Switched to new proxy {self.proxy}")
                        else:
                            logger.info("Switched to local IP (no proxy)")

                        continue

                    if response.status == 200:
                        return await response.text(), response.status, dict(response.headers)

                    logger.warning(f"Unexpected response code {response.status}. Retrying...")

            except aiohttp.ClientSSLError:
                logger.error("SSL Error: Probably using HTTP proxy for HTTPS request. Switching proxy.")
            except aiohttp.ClientProxyConnectionError:
                logger.error("Proxy Error: Proxy is not working. Switching proxy.")
            except asyncio.TimeoutError:
                logger.error(f"Timeout: Request timed out for {self.url}. Retrying...")
            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e}. Retrying...")

            self.proxy = self.proxy_manager.get_proxy()
            if self.proxy:
                logger.info(f"Switched to new proxy {self.proxy}")
            else:
                logger.info("Switched to local IP (no proxy)")

        logger.error(f"Giving up on {self.url} after {self.max_retries} attempts.")
        return "", 500, {}
