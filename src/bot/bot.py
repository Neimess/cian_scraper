import asyncio
from typing import Dict, List

from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.filters import Command

from configs.config import settings
from src.utils import logger
from src.web_scraper.scraper import CianScraper

from .handlers import cancel, open_settings, process_settings_callback
from .handlers.commands import error_handler, menu_handler, search_handler, start_handler, stop_handler


class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_API_KEY)
        self.dp = Dispatcher()
        self.user_scrapers: dict[int, CianScraper] = {}
        self.user_tasks: dict[int, asyncio.Task] = {}

        self.dp.message.register(start_handler, Command("start", "help"))
        self.dp.message.register(menu_handler, Command("menu"))
        self.dp.message.register(self.handle_search, Command("search"))
        self.dp.message.register(self.handle_stop, Command("stop"))

        self.dp.callback_query.register(self.handle_search_callback, lambda c: c.data == "start_search")
        self.dp.callback_query.register(open_settings, lambda c: c.data == "settings")
        self.dp.callback_query.register(cancel, lambda c: c.data == "cancel")
        self.dp.callback_query.register(process_settings_callback)

    async def handle_search_callback(self, callback: types.CallbackQuery):
        await search_handler(callback.message, self)
        await callback.answer()

    async def handle_search(self, message: types.Message):
        await search_handler(message, self)

    async def handle_stop(self, message: types.Message):
        await stop_handler(message, self)

    @error_handler
    async def send_notification(self, listings: List[Dict], user_id: int) -> None:
        """
        Send notifications about new listings, handling flood control.

        :param listings: List of new listings to notify about.
        :param user_id: Telegram_ID user
        """
        user = await self.bot.get_chat(user_id)
        if user.type == "bot":
            return

        if not listings:
            return

        messages_to_send = []

        for item in listings:
            text_parts = []

            if "title" in item:
                text_parts.append(f"🏠 *Название:* {item['title']}")
            if "address" in item:
                text_parts.append(f"📍 *Адрес:* {item['address']}")
            if "price" in item:
                text_parts.append(f"💵 *Цена:* {item['price']}")
            if "rooms" in item:
                text_parts.append(f"🛏 *Комнат:* {item['rooms']}")
            if "area" in item:
                text_parts.append(f"📏 *Площадь:* {item['area']}")
            if "date_published" in item:
                text_parts.append(f"📅 *Опубликовано:* {item['date_published']}")
            if "description" in item:
                text_parts.append(f"📝 *Описание:* {item['description']}")
            if "url" in item:
                text_parts.append(f"🔗 [Ссылка]({item['url']})")

            text = "\n".join(text_parts)
            images = item.get("images", [])

            messages_to_send.append((text, images))

        batch_size = 5
        for i in range(0, len(messages_to_send), batch_size):
            batch = messages_to_send[i : i + batch_size]

            for text, images in batch:
                try:
                    if len(images) == 1:
                        await self.bot.send_photo(
                            chat_id=user_id,
                            photo=images[0],
                            caption=text,
                            parse_mode="Markdown",
                        )
                    elif len(images) > 1:
                        media = [types.InputMediaPhoto(media=img) for img in images[:5]]
                        media[0].caption = text
                        media[0].parse_mode = "Markdown"

                        await self.bot.send_media_group(chat_id=user_id, media=media)
                    else:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=text,
                            parse_mode="Markdown",
                        )

                    logger.info(f"Notification sent to user {user_id}")

                    await asyncio.sleep(1.5)

                except TelegramRetryAfter as e:
                    wait_time = e.retry_after
                    logger.warning(f"Flood control triggered! Waiting {wait_time} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                    continue

                except TelegramAPIError as e:
                    logger.error(f"Telegram API error: {e}")
                    break

        logger.info(f"All notifications sent to user {user_id} for {len(listings)}")

    @error_handler
    async def _run_scraper(self, scraper: CianScraper):
        """
        Run the scraper and handle errors.

        :param message: The message object from the user.
        """
        scraper.is_running = True
        try:
            await scraper.run()
        except asyncio.CancelledError:
            logger.info(f"Scraper for user {scraper.telegram_user_id} was stopped.")
        finally:
            scraper.is_running = False

    async def run(self):
        "Start the boot"
        await self.dp.start_polling(self.bot)


if __name__ == "__main__":
    bot = TelegramBot()
    asyncio.run(bot.run())
