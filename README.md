### 📚 Mentor Language Bot

Telegram-бот-куратор для параллельного изучения языков с помощью OpenAI.

### Бот:

спрашивает уровень каждого языка (A1–C2);

автоматически составляет персональный план на 30 дней;

утром присылает задания по испанскому, вечером — по итальянскому;

хранит данные в SQLite (без сложной инфраструктуры);

работает через OpenAI (с поддержкой proxy);

# подходит для постоянной работы на сервере (systemd).

🚀 Основные возможности

🧠 AI-куратор и ментор

🗓 План обучения на 30 дней (генерируется автоматически)

⏰ Утренние и вечерние напоминания

📊 Отметка выполненных заданий

💾 Память пользователя (SQLite)

🔐 .env для секретов (не хранится в git)

📜 Подробные логи в терминале

### 🛠 Технологии
```bash
Python 3.11+ (рекомендуется)

aiogram 3

OpenAI API

SQLite + aiosqlite

APScheduler

httpx (proxy support)
```
### 📁 Структура проекта

``md
learning_bot/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── logger.py
│   ├── db.py
│   ├── openai_client.py
│   ├── planner.py
│   ├── prompts.py
│   ├── handlers.py
│   ├── scheduler.py
│   ├── keyboards.py
│   ├── states.py
│   └── __init__.py
│
├── migrations/
│   └── 001_init.sql
│
├── mentor.db              # SQLite база (не коммитится)
├── requirements.txt
├── .env                   # секреты (не коммитится)
├── .env.example
├── .gitignore
└── README.md
``
### ⚙️ Установка (локально или на сервере)
## 1️⃣ Клонировать репозиторий
```bash
git clone <REPO_URL>
cd learning_bot
```
## 2️⃣ Создать виртуальное окружение
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

## 3️⃣ Установить зависимости
```bash
pip install -r requirements.txt
```