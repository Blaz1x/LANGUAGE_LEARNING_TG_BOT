# app/main.py
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher

from app.config import settings
from app.db import Database
from app.handlers import router
from app.scheduler import setup_scheduler

logger = logging.getLogger("mentor_bot")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

async def run_migrations(db: Database) -> None:
    migrations_dir = Path("migrations")
    if not migrations_dir.exists():
        return
    files = sorted(migrations_dir.glob("*.sql"))
    for f in files:
        sql = f.read_text(encoding="utf-8")
        logger.info(f"Running DB migration script: {f.name}")
        await db.executescript(sql)
    logger.info("🗄️ Database migrations applied")

async def main():
    setup_logging()

    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Set it in .env")
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is empty. Set it in .env")

    logger.info("🚀 Starting mentor bot")

    db = Database(settings.DB_PATH)
    await db.connect()
    logger.info("📦 SQLite connected: %s", settings.DB_PATH)

    await run_migrations(db)

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # inject db into handlers
    dp["db"] = db
    dp.include_router(router)

    # scheduler (morning/evening)
    setup_scheduler(bot, db)

    logger.info("🤖 Telegram polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
