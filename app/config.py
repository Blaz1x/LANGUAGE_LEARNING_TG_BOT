# app/config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5.2").strip()

    # Proxy for OpenAI (optional)
    OPENAI_PROXY: str = os.getenv("OPENAI_PROXY", "").strip()

    # SQLite
    DB_PATH: str = os.getenv("DB_PATH", "mentor.db").strip()

    # Timezone
    TZ_DEFAULT: str = os.getenv("TZ_DEFAULT", "Europe/Moscow").strip()

    # Reminders
    MORNING_HOUR: int = int(os.getenv("MORNING_HOUR", "9"))
    EVENING_HOUR: int = int(os.getenv("EVENING_HOUR", "19"))

settings = Settings()
