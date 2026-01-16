import asyncio
import httpx
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError, RateLimitError

from app.config import settings
from app.logger import setup_logger

logger = setup_logger()

timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)

http_client = httpx.AsyncClient(
    proxy=settings.OPENAI_PROXY or None,
    timeout=timeout,
)

oa = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    http_client=http_client,
)

async def generate_text(system: str, user: str, model: str | None = None) -> str:
    last_err = None
    for attempt in range(1, 4):
        try:
            logger.info(f"OpenAI request started (attempt {attempt}/3)")
            resp = await oa.responses.create(
                model=model or settings.OPENAI_MODEL,
                instructions=system,
                input=user,
            )
            logger.info("OpenAI response received")
            return resp.output_text
        except (APITimeoutError, APIConnectionError, RateLimitError) as e:
            last_err = e
            logger.warning(f"OpenAI temporary error: {type(e).__name__} — retrying...")
            await asyncio.sleep(1.5 * attempt)

    logger.error(f"OpenAI failed after retries: {last_err}", exc_info=True)
    raise last_err
