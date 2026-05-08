"""Redis wrapper for cache + pub/sub.

Used for:
    - Villain stats cache (TTL'd, invalidated on rebuild).
    - ARQ task progress events (pub/sub channel `jobs:{job_id}`).

Uses a single Redis client instantiated lazily. Tests can monkeypatch
`get_client` to substitute a fake.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import redis
from loguru import logger

from src.config.settings import settings


@lru_cache(maxsize=1)
def get_client() -> redis.Redis:
    """Lazy singleton Redis client (decode_responses=True for str API)."""
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def reset_client() -> None:
    """Test helper: clear the cached client."""
    get_client.cache_clear()


# ── Cache primitives ─────────────────────────────────────────────────


def cache_get(key: str) -> Any | None:
    """Get a JSON-serialized value, or None if missing / Redis down."""
    try:
        raw = get_client().get(key)
    except redis.RedisError as e:
        logger.warning(f"redis get failed: {e}")
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def cache_set(key: str, value: Any, ttl: int | None = None) -> bool:
    """Set a value (JSON-serialized) with optional TTL (seconds).

    Falls back gracefully if Redis is unavailable: returns False.
    """
    try:
        payload = json.dumps(value, default=str)
        return bool(
            get_client().set(
                key, payload, ex=ttl or settings.cache_ttl_seconds,
            )
        )
    except redis.RedisError as e:
        logger.warning(f"redis set failed: {e}")
        return False


def cache_delete(*keys: str) -> int:
    """Delete keys; returns number actually removed."""
    if not keys:
        return 0
    try:
        return int(get_client().delete(*keys))
    except redis.RedisError as e:
        logger.warning(f"redis delete failed: {e}")
        return 0


def invalidate_villain(villain_name: str) -> int:
    """Drop all cache entries for a villain (called after rebuild)."""
    pattern = f"villain:{villain_name}:*"
    try:
        client = get_client()
        keys = list(client.scan_iter(match=pattern))
        if not keys:
            return 0
        return int(client.delete(*keys))
    except redis.RedisError as e:
        logger.warning(f"redis invalidate failed: {e}")
        return 0


# ── Pub/sub for ARQ task progress ────────────────────────────────────


def publish_progress(job_id: str, event: dict[str, Any]) -> int:
    """Publish a progress event on `jobs:{job_id}` channel.

    Returns subscriber count, or 0 if Redis is down.
    """
    channel = f"jobs:{job_id}"
    try:
        return int(get_client().publish(channel, json.dumps(event, default=str)))
    except redis.RedisError as e:
        logger.warning(f"redis publish failed: {e}")
        return 0
