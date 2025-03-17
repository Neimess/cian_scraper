import asyncio
import logging
import sys
from functools import wraps
from pathlib import Path
from typing import Callable

from configs.config import settings

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"
if settings.LOGGER_MODE in ("file", "both"):
    LOG_DIR.mkdir(exist_ok=True)


LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s - %(name)s/%(funcName)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


logger = logging.getLogger("cian_scraper")
logger.setLevel(logging.INFO)


if settings.LOGGER_MODE in ("file", "both"):
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)


if settings.LOGGER_MODE in ("console", "both"):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(console_handler)


aiogram_logger = logging.getLogger("aiogram")
aiogram_logger.setLevel(logging.INFO)
aiogram_logger.addHandler(file_handler if settings.LOGGER_MODE in ("file", "both") else console_handler)


def log(func: Callable) -> Callable:
    """
    A decorator to log method calls, arguments, and results.

    :param func: The function to be decorated.
    :return: Wrapped function with logging.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger.debug("Calling %s with args: %s, kwargs: %s", func.__name__, args, kwargs)
        try:
            result = await func(*args, **kwargs)
            logger.debug("%s returned: %s", func.__name__, result)
            return result
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, str(e))
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger.debug("Calling %s with args: %s, kwargs: %s", func.__name__, args, kwargs)
        try:
            result = func(*args, **kwargs)
            logger.debug("%s returned: %s", func.__name__, result)
            return result
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, str(e))
            raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
