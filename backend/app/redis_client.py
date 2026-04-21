"""Async Redis client with zl:* key prefix."""

import json
from typing import Any, Optional

import redis.asyncio as aioredis
from loguru import logger

from app.config import settings

# TTL constants (seconds)
TTL_LEADS = 3600
TTL_EMAIL = 604800
TTL_ICP = 86400

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def get_cached(key: str) -> Optional[Any]:
    try:
        r = get_redis()
        raw = await r.get(f"zl:{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis get error for zl:{key}: {exc}")
        return None


async def set_cached(key: str, value: Any, ttl: int = TTL_LEADS) -> bool:
    try:
        r = get_redis()
        await r.set(f"zl:{key}", json.dumps(value), ex=ttl)
        return True
    except Exception as exc:
        logger.warning(f"Redis set error for zl:{key}: {exc}")
        return False


async def delete_cached(key: str) -> bool:
    try:
        r = get_redis()
        await r.delete(f"zl:{key}")
        return True
    except Exception as exc:
        logger.warning(f"Redis delete error for zl:{key}: {exc}")
        return False
