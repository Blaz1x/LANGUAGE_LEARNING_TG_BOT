# app/planner.py
import json
import logging
from datetime import date, timedelta

from app.openai_client import generate_text
from app.prompts import SYSTEM_PLANNER, USER_PLANNER_TEMPLATE

logger = logging.getLogger("mentor_bot")

def _extract_json_array(text: str) -> list:
    # Defensive JSON extraction
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
    # find first '[' and last ']'
    l = text.find("[")
    r = text.rfind("]")
    if l == -1 or r == -1 or r <= l:
        raise ValueError("Could not find JSON array in model output.")
    raw = text[l:r+1]
    return json.loads(raw)

def compute_day_slots(langs: list[str], day_index: int) -> dict:
    """
    Returns dict:
    {
      "morning": {"lang_code": "...", "kind": "learn"},
      "evening": {"lang_code": "...", "kind": "learn"|"review"} or None
    }
    """
    n = len(langs)
    if n == 4:
        pairs = [(langs[0], langs[1]), (langs[2], langs[3])]
        a, b = pairs[(day_index - 1) % 2]
        return {
            "morning": {"lang_code": a, "kind": "learn"},
            "evening": {"lang_code": b, "kind": "learn"},
        }
    if n == 3:
        if day_index % 2 == 1:  # odd day: first two languages
            return {
                "morning": {"lang_code": langs[0], "kind": "learn"},
                "evening": {"lang_code": langs[1], "kind": "learn"},
            }
        # even day: third language learn in morning, review in evening
        return {
            "morning": {"lang_code": langs[2], "kind": "learn"},
            "evening": {"lang_code": langs[2], "kind": "review"},
        }
    if n == 2:
        return {
            "morning": {"lang_code": langs[0], "kind": "learn"},
            "evening": {"lang_code": langs[1], "kind": "learn"},
        }
    # n == 1
    return {
        "morning": {"lang_code": langs[0], "kind": "learn"},
        "evening": {"lang_code": langs[0], "kind": "review"},
    }

def build_schedule(start_day: date, langs: list[str], days: int = 30) -> list[dict]:
    schedule = []
    for i in range(1, days + 1):
        d = start_day + timedelta(days=i-1)
        slots = compute_day_slots(langs, i)
        for slot_name in ["morning", "evening"]:
            s = slots.get(slot_name)
            if not s:
                continue
            schedule.append({
                "day_index": i,
                "day_date": d.isoformat(),
                "slot": slot_name,
                "lang_code": s["lang_code"],
                "kind": s["kind"],
            })
    return schedule

async def generate_month_plan(db, user: dict, start_day: date) -> None:
    """
    Generates and saves 30-day plan for user's selected languages.
    """
    langs_rows = await db.get_user_languages(user["id"])
    if not langs_rows:
        raise RuntimeError("User has no selected languages.")
    langs_order = [r["lang_code"] for r in langs_rows]
    levels = {r["lang_code"]: r["level"] for r in langs_rows}

    schedule = build_schedule(start_day, langs_order, days=30)

    # Clear existing plan from start_day (safe overwrite)
    await db.clear_plans_from(user["id"], start_day.isoformat())

    # Chunk ranges (smaller responses, reliable through proxy)
    ranges = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 30)]
    all_items: list[dict] = []

    for a, b in ranges:
        logger.info(f"Generating plan chunk: days {a}-{b}")
        schedule_subset = [x for x in schedule if a <= x["day_index"] <= b]

        payload = USER_PLANNER_TEMPLATE.format(
            timezone=user["timezone"],
            langs_order=langs_order,
            levels=levels,
            schedule_json=json.dumps(schedule_subset, ensure_ascii=False),
            range_start=a,
            range_end=b,
        )

        raw = await generate_text(SYSTEM_PLANNER, payload)
        data = _extract_json_array(raw)

        # Normalize and validate
        items: list[dict] = []
        for it in data:
            day_date = str(it["day_date"])
            slot = str(it["slot"])
            lang_code = str(it["lang_code"])
            kind = str(it["kind"])
            topic = str(it["topic"]).strip()
            tasks = it.get("tasks", [])
            if not isinstance(tasks, list):
                tasks = [str(tasks)]
            tasks_json = json.dumps([str(x).strip() for x in tasks if str(x).strip()], ensure_ascii=False)

            items.append({
                "day_date": day_date,
                "slot": slot,
                "lang_code": lang_code,
                "kind": kind,
                "topic": topic if topic else "Тема дня",
                "tasks_json": tasks_json,
            })

        await db.save_plan_items(user["id"], items)
        all_items.extend(items)

    logger.info("30-day plan saved to SQLite")
