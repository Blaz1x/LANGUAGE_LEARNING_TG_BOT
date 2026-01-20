-- 002_multilang.sql
-- Universal multi-language support: selected languages, levels, daily plan items, progress.

CREATE TABLE IF NOT EXISTS user_languages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  lang_code TEXT NOT NULL,
  level TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, lang_code)
);

CREATE TABLE IF NOT EXISTS plan_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  day_date TEXT NOT NULL,          -- YYYY-MM-DD
  slot TEXT NOT NULL,              -- morning|evening
  lang_code TEXT NOT NULL,          -- es|it|de|fr
  kind TEXT NOT NULL,               -- learn|review
  topic TEXT NOT NULL,
  tasks_json TEXT NOT NULL,         -- JSON array string
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, day_date, slot)
);

CREATE TABLE IF NOT EXISTS progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  day_date TEXT NOT NULL,
  slot TEXT NOT NULL,               -- morning|evening
  done INTEGER NOT NULL DEFAULT 0,
  done_at TEXT,
  UNIQUE(user_id, day_date, slot)
);

CREATE INDEX IF NOT EXISTS idx_plan_items_user_date ON plan_items(user_id, day_date);
CREATE INDEX IF NOT EXISTS idx_progress_user_date ON progress(user_id, day_date);
