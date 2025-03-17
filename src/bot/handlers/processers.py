from aiogram import types

from db.crud.manager_users import update_user_config
from db.database import database
from src.bot.keyboards.settings_keyboards import (
    get_area_keyboard,
    get_only_foot_keyboard,
    get_price_keyboard,
    get_region_keyboard,
    get_rooms_keyboard,
    get_settings_keyboard,
    get_year_keyboard,
)


async def process_settings_callback(callback: types.CallbackQuery):
    data = callback.data
    chat_id = callback.message.chat.id
    user_id = callback.message.chat.id

    bot_info = await callback.bot.get_me()
    if chat_id == bot_info.id:
        return

    async with database() as db:
        if data == "settings_region":
            await callback.message.edit_text("Выберите регион:", reply_markup=get_region_keyboard())

        elif data.startswith("set_region_"):
            region_id = int(data.split("_")[-1])
            await update_user_config(db, user_id, "region", region_id)
            await callback.answer("✅ Регион обновлен!")
            await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_settings_keyboard())

        elif data == "settings_rooms":
            await callback.message.edit_text("Выберите количество комнат:", reply_markup=get_rooms_keyboard())

        elif data.startswith("set_rooms_"):
            rooms = data.split("_")[-1]
            await update_user_config(db, user_id, "rooms", rooms)
            await callback.answer("✅ Количество комнат обновлено!")
            await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_settings_keyboard())

        elif data == "settings_price":
            await callback.message.edit_text("Выберите ценовой диапазон:", reply_markup=get_price_keyboard())

        elif data.startswith("set_price_"):
            parts = data.split("_")
            min_price = int(parts[2])
            max_price = None if parts[3] == "None" else int(parts[3])
            await update_user_config(db, user_id, "min_price", min_price)
            await update_user_config(db, user_id, "max_price", max_price)
            await callback.answer("✅ Ценовой диапазон обновлен!")
            await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_settings_keyboard())

        elif data == "settings_only_foot":
            await callback.message.edit_text("Выберите опцию по доступности метро:", reply_markup=get_only_foot_keyboard())

        elif data.startswith("set_only_foot_"):
            only_foot_value = int(data.split("_")[-1])
            await update_user_config(db, user_id, "only_foot", only_foot_value)
            await callback.answer("✅ Опция по доступности метро обновлена!")
            await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_settings_keyboard())

        elif data == "settings_set_area":
            await callback.message.edit_text("Выберите квадратуру квартиры", reply_markup=get_area_keyboard())

        elif data.startswith("set_area_"):
            area_value = data.split("_")[-1]
            await update_user_config(db, user_id, "min_area", area_value)
            await callback.answer(f"Площадь обновлена: {area_value} м²")
            await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_settings_keyboard())

        elif data == "setting_house_year":
            await callback.message.edit_text("Выберите от какого года смотреть", reply_markup=get_year_keyboard())

        elif data.startswith("set_year_"):
            year_value = data.split("_")[-1]
            await update_user_config(db, user_id, "min_house_year", year_value)
            await callback.answer(f"Год обновлен: {year_value} м²")
            await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_settings_keyboard())

        elif data == "settings_done":
            await callback.message.edit_text("✅ Параметры сохранены.")
            await callback.answer("Настройки сохранены!")
