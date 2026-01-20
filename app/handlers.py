# app/handlers.py
import json
import logging
from datetime import datetime
import pytz

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.config import settings
from app.states import Onboarding
from app.keyboards import languages_keyboard, levels_keyboard, LANGS
from app.planner import generate_month_plan

logger = logging.getLogger("mentor_bot")
router = Router()

@router.message(Command("start"))
async def start(message: Message, state: FSMContext, db):
    user = await db.upsert_user(message.from_user.id, message.chat.id, settings.TZ_DEFAULT)

    await state.set_state(Onboarding.choosing_languages)
    await state.update_data(selected_langs=[], levels={}, level_queue=[], level_index=0)

    await message.answer(
        "Выбери языки, которые учим (можно 1–4). Потом я спрошу уровень каждого языка.",
        reply_markup=languages_keyboard([]),
    )
    logger.info(f"/start user_id={user['id']} tg={message.from_user.id}")

@router.callback_query(F.data.startswith("lang_toggle:"))
async def lang_toggle(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = list(data.get("selected_langs", []))

    code = callback.data.split(":")[1]
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)

    await state.update_data(selected_langs=selected)
    await callback.answer("Ок")
    await callback.message.edit_reply_markup(reply_markup=languages_keyboard(selected))

@router.callback_query(F.data == "lang_reset")
async def lang_reset(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_langs=[], levels={}, level_queue=[], level_index=0)
    await callback.answer("Сброшено")
    await callback.message.edit_reply_markup(reply_markup=languages_keyboard([]))

@router.callback_query(F.data == "lang_done")
async def lang_done(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    selected = list(data.get("selected_langs", []))

    if not selected:
        await callback.answer("Выбери хотя бы один язык")
        return

    # Keep chosen order as priority (click order)
    await state.update_data(level_queue=selected, level_index=0, levels={})
    await state.set_state(Onboarding.choosing_levels)

    first = selected[0]
    await callback.answer("Принял ✅")
    await callback.message.edit_text(
        f"Ок. Теперь выбери уровень для языка: *{LANGS[first]}*",
        parse_mode="Markdown",
        reply_markup=levels_keyboard(first),
    )

@router.callback_query(Onboarding.choosing_levels, F.data.startswith("lvl:"))
async def pick_level(callback: CallbackQuery, state: FSMContext, db):
    # Important: answer callback immediately to avoid Telegram timeout
    await callback.answer("Принял ✅")

    _, lang_code, level = callback.data.split(":")
    data = await state.get_data()

    levels = dict(data.get("levels", {}))
    queue = list(data.get("level_queue", []))
    idx = int(data.get("level_index", 0))

    levels[lang_code] = level

    # move forward
    idx += 1
    await state.update_data(levels=levels, level_index=idx)

    # If still have languages to ask
    if idx < len(queue):
        next_lang = queue[idx]
        await callback.message.edit_text(
            f"Уровень для языка: *{LANGS[next_lang]}*",
            parse_mode="Markdown",
            reply_markup=levels_keyboard(next_lang),
        )
        return

    # Done: save languages+levels, generate plan
    user = await db.get_user_by_tg(callback.from_user.id)
    if not user:
        user = await db.upsert_user(callback.from_user.id, callback.message.chat.id, settings.TZ_DEFAULT)

    order = queue  # chosen order
    langs_with_levels = [(code, levels[code]) for code in order]
    await db.set_user_languages(user["id"], langs_with_levels, order)

    tz = pytz.timezone(user["timezone"])
    start_day = datetime.now(tz).date()

    await callback.message.edit_text(
        "Отлично ✅ Уровни сохранил.\n\nГенерирую твой план на 30 дней… (может занять 1–3 минуты)",
        parse_mode="Markdown",
    )

    logger.info(f"Generating plan for user_id={user['id']} langs={order} levels={levels}")
    try:
        await generate_month_plan(db, user, start_day)
    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Не смог достучаться до OpenAI (таймаут/сеть).\n"
            "Попробуй ещё раз позже. Если хочешь — добавлю команду /regenerate."
        )
        await state.clear()
        return

    await callback.message.answer(
        "Готово ✅\n\n"
        "Команды:\n"
        "/today — план на сегодня\n"
        "/done morning — отметить утро\n"
        "/done evening — отметить вечер\n"
    )
    await state.clear()

@router.message(Command("today"))
async def today(message: Message, db):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    tz = pytz.timezone(user["timezone"])
    day = datetime.now(tz).date().isoformat()

    plans = await db.get_plan_for_day(user["id"], day)
    if not plans:
        await message.answer("На сегодня план не найден. Нажми /start чтобы сгенерировать.")
        return

    blocks = []
    for p in plans:
        tasks = []
        try:
            tasks = json.loads(p["tasks_json"])
        except Exception:
            tasks = []
        title = LANGS.get(p["lang_code"], p["lang_code"])
        kind = "🧠 Учим" if p["kind"] == "learn" else "🔁 Повторение"
        slot = "🌅 Утро" if p["slot"] == "morning" else "🌙 Вечер"
        bullets = "\n".join([f"• {t}" for t in tasks]) if tasks else "• (нет задач)"
        blocks.append(f"{slot} — {kind} — {title}\nТема: *{p['topic']}*\n{bullets}")

    await message.answer("\n\n".join(blocks), parse_mode="Markdown")

@router.message(Command("done"))
async def done(message: Message, db):
    parts = message.text.strip().split()
    if len(parts) < 2 or parts[1] not in ("morning", "evening"):
        await message.answer("Используй: /done morning или /done evening")
        return

    slot = parts[1]
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    tz = pytz.timezone(user["timezone"])
    day = datetime.now(tz).date().isoformat()

    await db.mark_done(user["id"], day, slot)
    await message.answer(f"✅ Отметил: {slot} за {day}")
