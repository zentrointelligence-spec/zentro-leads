"""
Rate limiting setup for Zentro Leads.
Uses Redis as the storage backend via slowapi.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

from app.config import settings
from app.redis_client import get_redis


class RedisStorage:
    """Simple adapter for slowapi to use our Redis client."""

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def incr(self, key: str, expiry: int) -> int:
        r = await self._get_redis()
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, expiry)
        results = await pipe.execute()
        return results[0]

    async def get(self, key: str) -> int:
        r = await self._get_redis()
        val = await r.get(key)
        return int(val) if val else 0


# Use client IP as the default key func, but allow overriding via request.state
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
)


def get_limiter() -> Limiter:
    return limiter
