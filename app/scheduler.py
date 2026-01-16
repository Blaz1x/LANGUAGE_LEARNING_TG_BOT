from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import json

from app.logger import setup_logger
logger = setup_logger()

def _fmt_tasks(tasks: list[dict]) -> str:
    lines = []
    for t in tasks:
        title = t.get("title", "Задание")
        minutes = t.get("minutes", 10)
        lines.append(f"• {title} ({minutes} мин)")
        steps = t.get("steps", [])
        for s in steps[:3]:
            lines.append(f"   - {s}")
    return "\n".join(lines)

async def _send_morning(bot, db, user):
    tz = pytz.timezone(user["timezone"])
    today = datetime.now(tz).date().isoformat()
    plan = await db.get_plan_day(user["id"], today)
    if not plan:
        return

    es_tasks = json.loads(plan["spanish_tasks"])
    text = (
        f"🇪🇸 Утро. Сегодня испанский:\n"
        f"Тема: *{plan['spanish_topic']}*\n\n"
        f"{_fmt_tasks(es_tasks)}\n\n"
        f"/today  /done es"
    )
    await bot.send_message(user["tg_chat_id"], text, parse_mode="Markdown")

async def _send_evening(bot, db, user):
    tz = pytz.timezone(user["timezone"])
    today = datetime.now(tz).date().isoformat()
    plan = await db.get_plan_day(user["id"], today)
    if not plan:
        return

    it_tasks = json.loads(plan["italian_tasks"])
    text = (
        f"🇮🇹 Вечер. Сегодня итальянский:\n"
        f"Тема: *{plan['italian_topic']}*\n\n"
        f"{_fmt_tasks(it_tasks)}\n\n"
        f"/today  /done it"
    )
    await bot.send_message(user["tg_chat_id"], text, parse_mode="Markdown")

def setup_scheduler(bot, db, users_loader, morning_hour: int, evening_hour: int):
    scheduler = AsyncIOScheduler()

    async def morning_job():
        users = await users_loader()
        logger.info(f"Scheduler morning_job: users={len(users)}")
        for u in users:
            try:
                await _send_morning(bot, db, u)
            except Exception as e:
                logger.error(f"Morning send failed: {e}", exc_info=True)

    async def evening_job():
        users = await users_loader()
        logger.info(f"Scheduler evening_job: users={len(users)}")
        for u in users:
            try:
                await _send_evening(bot, db, u)
            except Exception as e:
                logger.error(f"Evening send failed: {e}", exc_info=True)

    # триггеры по часам, фактическую дату берём по timezone пользователя в _send_...
    scheduler.add_job(morning_job, CronTrigger(hour=morning_hour, minute=0))
    scheduler.add_job(evening_job, CronTrigger(hour=evening_hour, minute=0))

    scheduler.start()
    logger.info(f"Scheduler started: morning={morning_hour}:00 evening={evening_hour}:00")
    return scheduler
