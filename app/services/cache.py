import json
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_cached_url(short_code: str) -> tuple[int, str] | None:
    try:
        raw = await redis_client.get(f"url:{short_code}")
        if not raw:
            return None
        payload = json.loads(raw)
        return int(payload["url_id"]), str(payload["original_url"])
    except Exception:
        return None


async def set_cached_url(short_code: str, url_id: int, original_url: str) -> None:
    try:
        payload = json.dumps({"url_id": url_id, "original_url": original_url})
        await redis_client.setex(
            f"url:{short_code}",
            settings.cache_ttl_seconds,
            payload,
        )
    except Exception:
        pass


async def delete_cached_url(short_code: str) -> None:
    try:
        await redis_client.delete(f"url:{short_code}")
    except Exception:
        pass
