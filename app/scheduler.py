# app/scheduler.py
import json
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from app.config import settings
from app.keyboards import LANGS

logger = logging.getLogger("mentor_bot")

def _format_plan_message(plan: dict) -> str:
    tasks = []
    try:
        tasks = json.loads(plan["tasks_json"])
    except Exception:
        tasks = []

    title = LANGS.get(plan["lang_code"], plan["lang_code"])
    kind = "🧠 Учим" if plan["kind"] == "learn" else "🔁 Повторение"
    header = f"{kind} — {title}\nТема: *{plan['topic']}*\n"
    bullets = "\n".join([f"• {t}" for t in tasks]) if tasks else "• (нет задач)"
    return header + "\n" + bullets

async def _send_slot(bot, db, user: dict, slot: str) -> None:
    tz = pytz.timezone(user["timezone"])
    today = datetime.now(tz).date().isoformat()

    plan = await db.get_plan_for_slot(user["id"], today, slot)
    if not plan:
        logger.info(f"No plan for user_id={user['id']} slot={slot} date={today}")
        return

    text = _format_plan_message(plan)
    await bot.send_message(user["chat_id"], text, parse_mode="Markdown")
    logger.info(f"Sent {slot} plan to user_id={user['id']}")

def setup_scheduler(bot, db) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TZ_DEFAULT)

    async def morning_job():
        users = await db.get_all_users()
        for u in users:
            await _send_slot(bot, db, u, "morning")

    async def evening_job():
        users = await db.get_all_users()
        for u in users:
            await _send_slot(bot, db, u, "evening")

    scheduler.add_job(
        morning_job,
        "cron",
        hour=settings.MORNING_HOUR,
        minute=0,
        id="morning_job",
        replace_existing=True,
    )
    scheduler.add_job(
        evening_job,
        "cron",
        hour=settings.EVENING_HOUR,
        minute=0,
        id="evening_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
