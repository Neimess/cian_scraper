from aiogram import types

from src.bot.keyboards.settings_keyboards import get_settings_keyboard


async def start_search(callback_query: types.CallbackQuery):
    await callback_query.answer("🔍 Поиск запущен!")
    await callback_query.message.edit_text("Идёт поиск...", reply_markup=None)


async def open_settings(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("⚙ Настройки (выберите параметр):", reply_markup=get_settings_keyboard())


async def cancel(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("❌ Действие отменено.")
