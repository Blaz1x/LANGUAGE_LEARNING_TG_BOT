import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


# raw env values
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_PROXY = os.getenv("OPENAI_PROXY", "").strip()

DB_PATH = os.getenv("DB_PATH", "mentor.db")
TZ_DEFAULT = os.getenv("TZ_DEFAULT", "Europe/Moscow")

MORNING_HOUR = int(os.getenv("MORNING_HOUR", "9"))
EVENING_HOUR = int(os.getenv("EVENING_HOUR", "19"))


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_PROXY: str
    DB_PATH: str
    TZ_DEFAULT: str
    MORNING_HOUR: int
    EVENING_HOUR: int


settings = Settings(
    BOT_TOKEN=BOT_TOKEN or "",
    OPENAI_API_KEY=OPENAI_API_KEY or "",
    OPENAI_MODEL=OPENAI_MODEL,
    OPENAI_PROXY=OPENAI_PROXY,
    DB_PATH=DB_PATH,
    TZ_DEFAULT=TZ_DEFAULT,
    MORNING_HOUR=MORNING_HOUR,
    EVENING_HOUR=EVENING_HOUR,
)
