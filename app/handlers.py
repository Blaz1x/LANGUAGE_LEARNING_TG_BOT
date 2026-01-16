from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
import pytz
import json

from app.states import Onboarding
from app.keyboards import level_kb
from app.planner import generate_month_plan
from app.logger import setup_logger

logger = setup_logger()

router = Router()

def today_for_user(timezone: str):
    tz = pytz.timezone(timezone)
    return datetime.now(tz).date()

@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext, db, settings):
    logger.info(f"/start from user {message.from_user.id}")

    user = await db.upsert_user(message.from_user.id, message.chat.id, settings.TZ_DEFAULT)

    await message.answer(
        "Я твой куратор 👇\n"
        "Сейчас быстро настроим уровни, чтобы план был точный.\n\n"
        "🇪🇸 Какой у тебя уровень испанского?",
        reply_markup=level_kb("lvl_es"),
    )
    await state.set_state(Onboarding.choosing_es)

@router.callback_query(F.data.startswith("lvl_es:"))
async def pick_es(callback: CallbackQuery, state: FSMContext, db):
    lvl = callback.data.split(":")[1]
    logger.info(f"Spanish level selected: {lvl}")

    await db.set_levels(callback.from_user.id, es_level=lvl)

    await callback.message.edit_text(
        f"🇪🇸 Испанский: *{lvl}* ✅\n\n🇮🇹 Теперь уровень итальянского?",
        parse_mode="Markdown",
        reply_markup=level_kb("lvl_it"),
    )
    await state.set_state(Onboarding.choosing_it)
    await callback.answer("Принял ✅ Делаю план…")


@router.callback_query(F.data.startswith("lvl_it:"))
async def pick_it(callback: CallbackQuery, state: FSMContext, db):
    lvl = callback.data.split(":")[1]
    logger.info(f"Italian level selected: {lvl}")

    # ✅ ВАЖНО: ответить на callback сразу, чтобы не протух
    await callback.answer("Принял ✅ Генерирую план…")

    user = await db.set_levels(callback.from_user.id, it_level=lvl)

    await callback.message.edit_text(
        f"🇮🇹 Итальянский: *{lvl}* ✅\n\n"
        "Генерирую твой план на 30 дней и включаю напоминания…",
        parse_mode="Markdown",
    )

    # Память
    await db.upsert_memory(user["id"], "format", "Утром испанский (актив), вечером итальянский (легкий)")
    await db.upsert_memory(user["id"], "rule", "Не смешивать языки в одной сессии")

    tz = user["timezone"]
    start_day = datetime.now(pytz.timezone(tz)).date()

    logger.info(f"Generating 30-day plan for user_id={user['id']}")
    try:
        await generate_month_plan(db, user, start_day)
    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Не смог достучаться до OpenAI (таймаут/сеть через прокси).\n"
            "Попробуй ещё раз через минуту или временно отключи прокси.\n"
            "Если хочешь — добавлю команду /regenerate."
        )
        await state.clear()
        return

    await callback.message.answer(
        "Готово ✅\n"
        "Теперь каждое утро будет 🇪🇸 испанский, каждый вечер — 🇮🇹 итальянский.\n\n"
        "Команды:\n"
        "/today — план на сегодня\n"
        "/done es — отметил испанский\n"
        "/done it — отметил итальянский"
    )
    await state.clear()


@router.message(F.text == "/today")
async def today(message: Message, db):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        return await message.answer("Нажми /start")

    day = today_for_user(user["timezone"]).isoformat()
    plan = await db.get_plan_day(user["id"], day)
    if not plan:
        return await message.answer("На сегодня плана нет. Нажми /start — пересоздам план.")

    es_tasks = json.loads(plan["spanish_tasks"])
    it_tasks = json.loads(plan["italian_tasks"])

    def fmt(tasks):
        return "\n".join([f"• {t.get('title','Задание')} ({t.get('minutes',10)} мин)" for t in tasks])

    await message.answer(
        f"📌 План на сегодня ({day}):\n\n"
        f"🇪🇸 *{plan['spanish_topic']}*\n{fmt(es_tasks)}\n\n"
        f"🇮🇹 *{plan['italian_topic']}*\n{fmt(it_tasks)}\n\n"
        f"/done es  /done it",
        parse_mode="Markdown",
    )

@router.message(F.text.startswith("/done"))
async def done(message: Message, db):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        return await message.answer("Нажми /start")

    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Формат: /done es или /done it")

    lang = parts[1].strip().lower()
    day = today_for_user(user["timezone"]).isoformat()
    await db.mark_done(user["id"], day, lang)
    await message.answer("Отметил ✅")
