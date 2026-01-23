# app/db.py
from __future__ import annotations

import aiosqlite
from typing import Any, Optional, Sequence


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

        # determined at runtime based on existing schema
        self._users_chat_col: str = "chat_id"

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self._ensure_users_table()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def execute(self, sql: str, params: Sequence[Any] | None = None) -> None:
        assert self.conn
        await self.conn.execute(sql, params or [])
        await self.conn.commit()

    async def executescript(self, script: str) -> None:
        assert self.conn
        await self.conn.executescript(script)
        await self.conn.commit()

    async def fetchone(self, sql: str, params: Sequence[Any] | None = None) -> Optional[dict]:
        assert self.conn
        cur = await self.conn.execute(sql, params or [])
        row = await cur.fetchone()
        await cur.close()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: Sequence[Any] | None = None) -> list[dict]:
        assert self.conn
        cur = await self.conn.execute(sql, params or [])
        rows = await cur.fetchall()
        await cur.close()
        return [dict(r) for r in rows]

    # ---------- internal schema helpers ----------
    async def _table_columns(self, table: str) -> set[str]:
        assert self.conn
        cur = await self.conn.execute(f"PRAGMA table_info({table})")
        rows = await cur.fetchall()
        await cur.close()
        return {r["name"] for r in rows}

    async def _ensure_users_table(self) -> None:
        """
        Ensure users table exists and has required columns.
        Must be compatible with older schema that used tg_chat_id instead of chat_id.
        """
        # Create minimal table if missing
        await self.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tg_user_id INTEGER NOT NULL UNIQUE
            );
            """
        )

        cols = await self._table_columns("users")

        # detect which chat column exists (old schema used tg_chat_id)
        if "tg_chat_id" in cols:
            self._users_chat_col = "tg_chat_id"
        else:
            self._users_chat_col = "chat_id"

        # Add missing columns safely (only those not existing)
        if self._users_chat_col == "chat_id" and "chat_id" not in cols:
            await self.execute("ALTER TABLE users ADD COLUMN chat_id INTEGER")
            cols.add("chat_id")

        # If old schema has tg_chat_id but it's NOT NULL, we just use it (no need to add chat_id)
        if "timezone" not in cols:
            await self.execute("ALTER TABLE users ADD COLUMN timezone TEXT")
            cols.add("timezone")

        if "created_at" not in cols:
            await self.execute(
                "ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT (datetime('now'))"
            )
            cols.add("created_at")

        # Backfill timezone if null
        await self.execute(
            "UPDATE users SET timezone = COALESCE(timezone, ?) ",
            ["Europe/Moscow"],
        )

    # ---------- Users ----------
    async def upsert_user(self, tg_user_id: int, chat_id: int, timezone: str) -> dict:
        """
        Insert or update user. Uses tg_chat_id if present in schema, otherwise chat_id.
        """
        chat_col = self._users_chat_col

        await self.execute(
            f"""
            INSERT INTO users (tg_user_id, {chat_col}, timezone)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_user_id) DO UPDATE SET
              {chat_col}=excluded.{chat_col},
              timezone=excluded.timezone
            """,
            [tg_user_id, chat_id, timezone],
        )

        user = await self.fetchone("SELECT * FROM users WHERE tg_user_id=?", [tg_user_id])
        assert user
        return user

    async def get_user_by_tg(self, tg_user_id: int) -> Optional[dict]:
        return await self.fetchone("SELECT * FROM users WHERE tg_user_id=?", [tg_user_id])

    async def get_all_users(self) -> list[dict]:
        return await self.fetchall("SELECT * FROM users ORDER BY id")

    # ---------- Languages ----------
    async def set_user_languages(
        self,
        user_id: int,
        langs_with_levels: list[tuple[str, str]],
        order: list[str],
    ) -> None:
        sort_map = {code: i for i, code in enumerate(order)}
        selected_codes = [c for c, _ in langs_with_levels]

        if selected_codes:
            await self.execute(
                f"DELETE FROM user_languages WHERE user_id=? AND lang_code NOT IN ({','.join(['?']*len(selected_codes))})",
                [user_id] + selected_codes,
            )

        for code, level in langs_with_levels:
            await self.execute(
                """
                INSERT INTO user_languages (user_id, lang_code, level, sort_order)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, lang_code) DO UPDATE SET
                  level=excluded.level,
                  sort_order=excluded.sort_order
                """,
                [user_id, code, level, sort_map.get(code, 0)],
            )

    async def get_user_languages(self, user_id: int) -> list[dict]:
        return await self.fetchall(
            "SELECT lang_code, level, sort_order FROM user_languages WHERE user_id=? ORDER BY sort_order",
            [user_id],
        )

    # ---------- Plans ----------
    async def clear_plans_from(self, user_id: int, start_date: str) -> None:
        await self.execute("DELETE FROM plan_items WHERE user_id=? AND day_date>=?", [user_id, start_date])
        await self.execute("DELETE FROM progress WHERE user_id=? AND day_date>=?", [user_id, start_date])

    async def save_plan_items(self, user_id: int, items: list[dict]) -> None:
        for it in items:
            await self.execute(
                """
                INSERT INTO plan_items (user_id, day_date, slot, lang_code, kind, topic, tasks_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, day_date, slot) DO UPDATE SET
                  lang_code=excluded.lang_code,
                  kind=excluded.kind,
                  topic=excluded.topic,
                  tasks_json=excluded.tasks_json
                """,
                [
                    user_id,
                    it["day_date"],
                    it["slot"],
                    it["lang_code"],
                    it["kind"],
                    it["topic"],
                    it["tasks_json"],
                ],
            )

    async def get_plan_for_day(self, user_id: int, day_date: str) -> list[dict]:
        return await self.fetchall(
            "SELECT * FROM plan_items WHERE user_id=? AND day_date=? "
            "ORDER BY CASE slot WHEN 'morning' THEN 1 ELSE 2 END",
            [user_id, day_date],
        )

    async def get_plan_for_slot(self, user_id: int, day_date: str, slot: str) -> Optional[dict]:
        return await self.fetchone(
            "SELECT * FROM plan_items WHERE user_id=? AND day_date=? AND slot=?",
            [user_id, day_date, slot],
        )

    # ---------- Progress ----------
    async def mark_done(self, user_id: int, day_date: str, slot: str) -> None:
        await self.execute(
            """
            INSERT INTO progress (user_id, day_date, slot, done, done_at)
            VALUES (?, ?, ?, 1, datetime('now'))
            ON CONFLICT(user_id, day_date, slot) DO UPDATE SET
              done=1,
              done_at=datetime('now')
            """,
            [user_id, day_date, slot],
        )

    async def get_progress(self, user_id: int, day_date: str) -> list[dict]:
        return await self.fetchall("SELECT * FROM progress WHERE user_id=? AND day_date=?", [user_id, day_date])
