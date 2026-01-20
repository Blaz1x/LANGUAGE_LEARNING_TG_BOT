# app/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

LANGS = {
    "es": "Испанский 🇪🇸",
    "it": "Итальянский 🇮🇹",
    "de": "Немецкий 🇩🇪",
    "fr": "Французский 🇫🇷",
}

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

def languages_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for code, title in LANGS.items():
        checked = "✅" if code in selected else "⬜️"
        rows.append([
            InlineKeyboardButton(text=f"{checked} {title}", callback_data=f"lang_toggle:{code}")
        ])
    rows.append([
        InlineKeyboardButton(text="♻️ Сброс", callback_data="lang_reset"),
        InlineKeyboardButton(text="✅ Готово", callback_data="lang_done"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def levels_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    rows = []
    # 2 columns layout
    for i in range(0, len(LEVELS), 2):
        chunk = LEVELS[i:i+2]
        row = []
        for lvl in chunk:
            row.append(InlineKeyboardButton(text=lvl, callback_data=f"lvl:{lang_code}:{lvl}"))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)
