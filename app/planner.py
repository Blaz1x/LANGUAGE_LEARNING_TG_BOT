import json
from datetime import date, timedelta
from app.openai_client import generate_text
from app.prompts import PLAN_INSTRUCTIONS
from app.logger import setup_logger

logger = setup_logger()

def _extract_json_array(text: str):
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in OpenAI output")
    return json.loads(text[start:end+1])

async def generate_month_plan(db, user_row, start_day: date):
    memory = await db.get_memory_map(user_row["id"])

    payload_base = {
        "spanish_level": user_row["spanish_level"],
        "italian_level": user_row["italian_level"],
        "preferences": memory,
        "start_date": start_day.isoformat(),
    }

    # Генерим план пачками по неделям — надежнее через прокси
    ranges = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 30)]

    for a, b in ranges:
        payload = dict(payload_base)
        payload["range_start"] = a
        payload["range_end"] = b

        logger.info(f"Generating plan chunk: days {a}-{b}")
        raw = await generate_text(
            system=PLAN_INSTRUCTIONS,
            user=json.dumps(payload, ensure_ascii=False),
        )
        plan = _extract_json_array(raw)

        for item in plan:
            d = start_day + timedelta(days=int(item["day_index"]) - 1)
            await db.insert_plan_day(
                user_id=user_row["id"],
                day=d.isoformat(),
                es_topic=item["spanish_topic"],
                es_tasks_json=json.dumps(item["spanish_tasks"], ensure_ascii=False),
                it_topic=item["italian_topic"],
                it_tasks_json=json.dumps(item["italian_tasks"], ensure_ascii=False),
            )

    logger.info("30-day plan saved to SQLite")
