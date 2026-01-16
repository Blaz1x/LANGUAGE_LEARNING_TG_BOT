from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

def level_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(LEVELS), 3):
        rows.append([
            InlineKeyboardButton(text=lvl, callback_data=f"{prefix}:{lvl}")
            for lvl in LEVELS[i:i+3]
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
