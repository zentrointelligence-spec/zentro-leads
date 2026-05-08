"""
Rate limiting setup for Zentro Leads.
Uses Redis as the storage backend via slowapi.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

from app.config import settings


def _rate_limit_storage_uri() -> str:
    """
    SlowAPI storage backend.

    Redis is correct for production. In DEBUG mode, default to in-memory storage so
    login and other limited routes do not return 500 when Redis is not running
    locally (SlowAPI would otherwise fail talking to Redis).
    """
    explicit = (settings.RATE_LIMIT_STORAGE_URI or "").strip()
    if explicit:
        return explicit
    if settings.DEBUG:
        return "memory://"
    return settings.REDIS_URL


# Use client IP as the default key func, but allow overriding via request.state
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_rate_limit_storage_uri(),
    strategy="fixed-window",
)


def get_limiter() -> Limiter:
    return limiter
