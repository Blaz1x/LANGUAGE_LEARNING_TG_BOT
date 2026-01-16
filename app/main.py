import asyncio
from aiogram import Bot, Dispatcher

from app.config import settings
from app.db import Database
from app.handlers import router
from app.scheduler import setup_scheduler
from app.logger import setup_logger

logger = setup_logger()

async def run_migrations(db: Database):
    import pathlib
    sql = pathlib.Path("migrations/001_init.sql").read_text(encoding="utf-8")
    await db.executescript(sql)

async def main():
    logger.info("🚀 Starting mentor bot")

    db = Database(settings.DB_PATH)
    await db.connect()
    logger.info(f"📦 SQLite connected: {settings.DB_PATH}")

    await run_migrations(db)
    logger.info("🗄️ Database migrations applied")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    dp["db"] = db
    dp["settings"] = settings
    dp.include_router(router)

    async def users_loader():
        return await db.list_users()

    logger.info(
        f"⏰ Scheduler starting (morning={settings.MORNING_HOUR}:00, evening={settings.EVENING_HOUR}:00, tz={settings.TZ_DEFAULT})"
    )
    setup_scheduler(
        bot=bot,
        db=db,
        users_loader=users_loader,
        morning_hour=settings.MORNING_HOUR,
        evening_hour=settings.EVENING_HOUR
    )

    logger.info("🤖 Telegram polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
