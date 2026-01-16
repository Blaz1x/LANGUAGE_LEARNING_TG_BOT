import aiosqlite
from app.logger import setup_logger

logger = setup_logger()

class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON;")
        logger.info("DB connected")

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def execute(self, q: str, args: tuple = ()):
        assert self.conn
        await self.conn.execute(q, args)
        await self.conn.commit()

    async def executescript(self, script: str):
        assert self.conn
        logger.info("Running DB migration script")
        await self.conn.executescript(script)
        await self.conn.commit()

    async def fetchrow(self, q: str, args: tuple = ()):
        assert self.conn
        cur = await self.conn.execute(q, args)
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, q: str, args: tuple = ()):
        assert self.conn
        cur = await self.conn.execute(q, args)
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def upsert_user(self, tg_user_id: int, chat_id: int, tz: str):
        q = """
        INSERT INTO users (tg_user_id, tg_chat_id, timezone)
        VALUES (?, ?, ?)
        ON CONFLICT(tg_user_id) DO UPDATE SET
          tg_chat_id=excluded.tg_chat_id,
          timezone=excluded.timezone;
        """
        await self.execute(q, (tg_user_id, chat_id, tz))
        user = await self.fetchrow("SELECT * FROM users WHERE tg_user_id=?", (tg_user_id,))
        logger.info(f"User upserted: tg_user_id={tg_user_id}")
        return user

    async def set_levels(self, tg_user_id: int, es_level: str | None = None, it_level: str | None = None):
        user = await self.get_user_by_tg(tg_user_id)
        if not user:
            return None

        if es_level:
            await self.execute("UPDATE users SET spanish_level=? WHERE tg_user_id=?", (es_level, tg_user_id))
        if it_level:
            await self.execute("UPDATE users SET italian_level=? WHERE tg_user_id=?", (it_level, tg_user_id))

        return await self.get_user_by_tg(tg_user_id)

    async def get_user_by_tg(self, tg_user_id: int):
        return await self.fetchrow("SELECT * FROM users WHERE tg_user_id=?", (tg_user_id,))

    async def list_users(self):
        return await self.fetchall("SELECT * FROM users", ())

    async def upsert_memory(self, user_id: int, key: str, value: str):
        q = """
        INSERT INTO user_memory (user_id, key, value)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, key) DO UPDATE SET
          value=excluded.value,
          updated_at=datetime('now');
        """
        await self.execute(q, (user_id, key, value))

    async def get_memory_map(self, user_id: int) -> dict[str, str]:
        rows = await self.fetchall("SELECT key, value FROM user_memory WHERE user_id=?", (user_id,))
        return {r["key"]: r["value"] for r in rows}

    async def insert_plan_day(
        self,
        user_id: int,
        day: str,
        es_topic: str,
        es_tasks_json: str,
        it_topic: str,
        it_tasks_json: str
    ):
        q = """
        INSERT INTO daily_plans (user_id, day_date, spanish_topic, spanish_tasks, italian_topic, italian_tasks)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, day_date) DO NOTHING;
        """
        await self.execute(q, (user_id, day, es_topic, es_tasks_json, it_topic, it_tasks_json))

    async def get_plan_day(self, user_id: int, day: str):
        return await self.fetchrow("SELECT * FROM daily_plans WHERE user_id=? AND day_date=?", (user_id, day))

    async def mark_done(self, user_id: int, day: str, lang: str):
        if lang not in ("es", "it"):
            raise ValueError("lang must be 'es' or 'it'")
        col = "spanish_done" if lang == "es" else "italian_done"
        q = f"""
        INSERT INTO daily_progress (user_id, day_date, {col})
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, day_date) DO UPDATE SET
          {col}=1, updated_at=datetime('now');
        """
        await self.execute(q, (user_id, day))

    async def log_interaction(self, user_id: int, role: str, text: str):
        await self.execute(
            "INSERT INTO interactions (user_id, role, text) VALUES (?, ?, ?)",
            (user_id, role, text)
        )
