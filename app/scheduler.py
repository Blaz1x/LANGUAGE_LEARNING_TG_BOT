# app/scheduler.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger("mentor_bot")


def _get_chat_id(user: dict) -> int | None:
    # совместимость со старыми/новыми схемами
    return user.get("chat_id") or user.get("tg_chat_id") or user.get("tg_chat")


def _get_tz(user: dict) -> str:
    return user.get("timezone") or getattr(settings, "TZ_DEFAULT", "Europe/Moscow")


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except Exception:
        logger.exception("Failed to send message to chat_id=%s", chat_id)


async def build_notification_text(db, user: dict, slot: str) -> str:
    """
    slot: 'morning' | 'evening'
    Формирует текст уведомления на основе плана на сегодня.
    """
    tz_name = _get_tz(user)
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date().isoformat()

    item = await db.get_plan_for_slot(user["id"], today, slot)
    if not item:
        if slot == "morning":
            return (
                "🌅 Доброе утро!\n\n"
                "Плана на сегодня пока нет.\n"
                "Нажми /start и выбери языки/уровень — я соберу план на месяц 👇"
            )
        return (
            "🌙 Вечер!\n\n"
            "Плана на сегодня пока нет.\n"
            "Можем сделать лёгкое повторение — напиши /today"
        )

    lang = (item.get("lang_code") or "").upper()
    topic = item.get("topic") or "Тема дня"

    if slot == "morning":
        return (
            f"🌅 Доброе утро!\n\n"
            f"📌 Сегодняшний фокус: {lang}\n"
            f"🎯 Тема: {topic}\n\n"
            f"Напиши /today — покажу задания."
        )
    else:
        return (
            f"🌙 Вечерний режим: отдых/повторение\n\n"
            f"🧠 Язык: {lang}\n"
            f"🔁 Повторяем тему: «{topic}»\n\n"
            f"Напиши /today — дам короткий план повторения."
        )


async def send_slot_notification(bot: Bot, db, user: dict, slot: str) -> bool:
    """
    Отправляет уведомление конкретному юзеру. Возвращает True если отправили, иначе False.
    """
    chat_id = _get_chat_id(user)
    if not chat_id:
        logger.warning("User id=%s has no chat_id/tg_chat_id, skip notify", user.get("id"))
        return False

    text = await build_notification_text(db, user, slot)
    await _safe_send(bot, int(chat_id), text)
    return True


def setup_scheduler(bot: Bot, db) -> AsyncIOScheduler:
    """
    Создаёт и стартует APScheduler.
    """
    tz_name = getattr(settings, "TZ_DEFAULT", "Europe/Moscow")
    tz = ZoneInfo(tz_name)

    scheduler = AsyncIOScheduler(timezone=tz)

    async def morning_job():
        logger.info("⏰ Morning job fired")
        users = await db.get_all_users()
        logger.info("Morning job: users=%s", len(users))
        sent = 0
        for u in users:
            if await send_slot_notification(bot, db, u, "morning"):
                sent += 1
        logger.info("Morning job done: sent=%s", sent)

    async def evening_job():
        logger.info("⏰ Evening job fired")
        users = await db.get_all_users()
        logger.info("Evening job: users=%s", len(users))
        sent = 0
        for u in users:
            if await send_slot_notification(bot, db, u, "evening"):
                sent += 1
        logger.info("Evening job done: sent=%s", sent)

    scheduler.add_job(
        lambda: asyncio.create_task(morning_job()),
        CronTrigger(hour=settings.MORNING_HOUR, minute=0),
        id="morning_job",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: asyncio.create_task(evening_job()),
        CronTrigger(hour=settings.EVENING_HOUR, minute=0),
        id="evening_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "⏰ Scheduler started (morning=%s:00, evening=%s:00, tz=%s)",
        settings.MORNING_HOUR,
        settings.EVENING_HOUR,
        tz_name,
    )
    return scheduler
