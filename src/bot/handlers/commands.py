import asyncio
from types import MethodType

from aiogram import types

from db.crud.manager_users import get_or_create_user, get_user_config
from db.database import database
from src.bot.keyboards.settings_keyboards import get_main_menu
from src.utils import error_handler, log, notify_listings_handler, to_dict
from src.web_scraper.scraper import CianScraper


@log
@error_handler
async def start_handler(message: types.Message):
    """
    Обработчик команды /start.
    """
    text = (
        "🏠 Добро пожаловать! Я помогу найти недвижимость на Cian.ru.\n\n"
        "🔍 Команды:\n"
        "/search - начать поиск\n"
        "/menu - открыть главное меню\n"
        "/settings - настроить параметры поиска\n"
        "/stop - остановить поиск"
    )
    async with database() as db:
        await get_or_create_user(db, message.chat.id)

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())


@log
@error_handler
async def menu_handler(message: types.Message):
    """
    Отображает главное меню.
    """
    await message.answer("📋 Главное меню:", reply_markup=get_main_menu())


@log
@error_handler
async def search_handler(message: types.Message, bot_instance):
    user_id = message.chat.id
    if user_id in bot_instance.user_tasks and not bot_instance.user_tasks[user_id].done():
        await message.answer("❌ Поиск уже запущен. Остановите его через /stop")
        return

    async with database() as db:
        user_config = await get_user_config(db, user_id)
        user_params = to_dict(user_config)

    scraper = CianScraper(params=user_params, freeze_time=10, telegram_user_id=user_id)
    original_method = scraper.save_new_listings.__func__
    decorated_func = notify_listings_handler(bot_instance.send_notification)(original_method)
    scraper.save_new_listings = MethodType(decorated_func, scraper)

    bot_instance.user_scrapers[user_id] = scraper

    task = asyncio.create_task(bot_instance._run_scraper(scraper))
    bot_instance.user_tasks[user_id] = task
    await message.answer("🔍 Поиск запущен!")


@log
@error_handler
async def stop_handler(message: types.Message, bot_instance):
    """
    Останавливает активный поиск.
    """
    user_id = message.from_user.id

    if user_id in bot_instance.user_tasks and bot_instance.user_tasks[user_id]:
        bot_instance.user_tasks[user_id].cancel()
        del bot_instance.user_tasks[user_id]

    if user_id in bot_instance.user_scrapers:
        del bot_instance.user_scrapers[user_id]

    await message.answer("⏹ Поиск остановлен.")
