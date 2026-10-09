import asyncio
import contextlib

import redis.asyncio as redis

from core.config.settings import get_settings

_settings = get_settings()


async def redis_is_reachable(timeout_seconds: float) -> bool:
    """Real connectivity check used by /health — never reports success without trying."""
    client = redis.from_url(_settings.redis_url, socket_connect_timeout=timeout_seconds)
    try:
        async with asyncio.timeout(timeout_seconds):
            return bool(await client.ping())
    except Exception:
        return False
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()
