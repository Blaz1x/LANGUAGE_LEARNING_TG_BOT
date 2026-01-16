PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_user_id    INTEGER UNIQUE NOT NULL,
  tg_chat_id    INTEGER NOT NULL,
  timezone      TEXT NOT NULL DEFAULT 'Europe/Moscow',
  spanish_level TEXT NOT NULL DEFAULT 'A2',
  italian_level TEXT NOT NULL DEFAULT 'A2',
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_memory (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL,
  key         TEXT NOT NULL,
  value       TEXT NOT NULL,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, key),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_plans (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL,
  day_date      TEXT NOT NULL,         -- YYYY-MM-DD
  spanish_topic TEXT NOT NULL,
  spanish_tasks TEXT NOT NULL,         -- JSON string
  italian_topic TEXT NOT NULL,
  italian_tasks TEXT NOT NULL,         -- JSON string
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, day_date),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_progress (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL,
  day_date      TEXT NOT NULL,
  spanish_done  INTEGER NOT NULL DEFAULT 0,
  italian_done  INTEGER NOT NULL DEFAULT 0,
  note          TEXT,
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, day_date),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interactions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL,
  role        TEXT NOT NULL,
  text        TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
