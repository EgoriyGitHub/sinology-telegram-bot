
import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

TOKEN = "7697883646:AAGwwp-DtP9oIqGWE0LI1Oza4QuJuKquFoI"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

conn = sqlite3.connect("sinology_final.db")
cursor = conn.cursor()

user_data = {}

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Школы с китайским уклоном", callback_data="schools")
    builder.button(text="Курсы китайского языка", callback_data="courses")
    builder.button(text="ВУЗы с программами по китаистике", callback_data="universities")
    builder.button(text="Дополнительное образование", callback_data="extra")
    builder.adjust(1)
    await message.answer(
        "Вас приветствует бот Ассоциации развития синологии.\nЯ помогу вам найти подходящие образовательные программы по китайскому языку в России.\nЧто вы ищете?",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "schools")
async def handle_schools(callback: CallbackQuery):
    user_data[callback.from_user.id] = {}
    builder = InlineKeyboardBuilder()
    builder.button(text="Начальная школа", callback_data="age_primary")
    builder.button(text="Средняя школа", callback_data="age_middle")
    builder.button(text="Старшая школа", callback_data="age_high")
    builder.adjust(1)
    await callback.message.edit_text("Для какого возраста вы ищете школу?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("age_"))
async def handle_age(callback: CallbackQuery):
    age_map = {
        "age_primary": "начальная",
        "age_middle": "средняя",
        "age_high": "старшая"
    }
    user_data[callback.from_user.id]["age"] = age_map[callback.data]
    builder = InlineKeyboardBuilder()
    builder.button(text="Начинающий (HSK 1-2)", callback_data="level_beginner")
    builder.button(text="Средний (HSK 3-4)", callback_data="level_intermediate")
    builder.button(text="Продвинутый (HSK 5-6)", callback_data="level_advanced")
    builder.adjust(1)
    await callback.message.edit_text("Какой уровень владения китайским языком у ребёнка?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("level_"))
async def handle_level(callback: CallbackQuery):
    level_map = {
        "level_beginner": "начинающий",
        "level_intermediate": "средний",
        "level_advanced": "продвинутый"
    }
    user_data[callback.from_user.id]["level"] = level_map[callback.data]
    user_data[callback.from_user.id]["waiting_city"] = True
    await callback.message.edit_text("В каком городе вас интересуют школы?")

async def send_schools_page(message: Message, uid: int):
    page = user_data[uid].get("page", 0)
    results = user_data[uid]["results"]
    total = len(results)
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_results = results[start:end]

    for name, data in page_results:
        reply = f"🏫 <b>{name}</b>\n"
        reply += f"📞 Контакты: {data['contact']}\n"
        reply += "🕒 Расписание:\n"
        for s in data['schedules']:
            reply += f"{s}\n\n"
        await message.answer(reply.strip(), parse_mode=ParseMode.HTML)

    if end < total:
        user_data[uid]["page"] += 1
        builder = InlineKeyboardBuilder()
        builder.button(text="Показать ещё", callback_data="next_schools")
        builder.adjust(1)
        await message.answer("Показать ещё школы?", reply_markup=builder.as_markup())
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔁 Найти другие школы", callback_data="schools")
        builder.adjust(1)
        await message.answer("Это все школы по вашему запросу. Хотите начать заново?", reply_markup=builder.as_markup())

# Обрабатывает ввод города и подготавливает постраничный список
@router.message()
async def handle_city(message: Message):
    uid = message.from_user.id
    if user_data.get(uid, {}).get("waiting_city"):
        city = message.text.strip().lower()
        age = user_data[uid]["age"]
        level = user_data[uid]["level"]

        query = """
        SELECT school_name, contact, schedule FROM schools
        WHERE LOWER(city) = ?
          AND age_group = ?
          AND level = ?
        """
        cursor.execute(query, (city, age, level))
        rows = cursor.fetchall()

        if not rows:
            await message.answer(f"К сожалению, не найдено школ в городе <b>{city.title()}</b> по заданным параметрам.", parse_mode=ParseMode.HTML)
            return

        # Группируем
        schools = {}
        for name, contact, schedule in rows:
            if name not in schools:
                schools[name] = {"contact": contact, "schedules": []}
            schools[name]["schedules"].append(schedule)

        user_data[uid]["results"] = list(schools.items())
        user_data[uid]["page"] = 0
        user_data[uid]["waiting_city"] = False

        await send_schools_page(message, uid)

    else:
        await message.answer("Пожалуйста, нажмите /start для начала.")

# Обрабатывает кнопку "Показать ещё"
@router.callback_query(F.data == "next_schools")
async def show_next_schools(callback: CallbackQuery):
    await send_schools_page(callback.message, callback.from_user.id)
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
