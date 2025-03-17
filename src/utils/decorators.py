from functools import wraps
from typing import Callable, Dict, List

from configs.config import settings
from src.utils.loggers import logger


def notify_listings_handler(callback: Callable[[List[Dict], int], None]):
    """
    A decorator to send notifications when new listings are saved.

    :param callback: A function that takes a list of new listings and sends notifications.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            size_before = await self._get_data_size()
            result = await func(self, *args, **kwargs)
            size_after = await self._get_data_size()
            if size_after > size_before:
                new_listings = await self._get_recent_listings(limit=size_after - size_before)
                if new_listings and callback and hasattr(self, "telegram_user_id") and self.telegram_user_id:
                    await callback(new_listings, self.telegram_user_id)
            return result

        return wrapper

    return decorator


def error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self = args[0]
            logger.error(f"Handled error in {func.__name__}: {str(e)}")
            await self.bot.send_message(chat_id=settings.TELEGRAM_ADMIN_ID, text=f"Error in {func.__name__}: {str(e)[:4096]}")
            raise

    return wrapper
