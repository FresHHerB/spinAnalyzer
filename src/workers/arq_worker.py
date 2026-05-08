"""ARQ worker entrypoint.

Run with:
    arq src.workers.arq_worker.WorkerSettings

Tasks live in `src.workers.tasks`.
"""

from __future__ import annotations

from arq.connections import RedisSettings

from src.config.settings import settings
from src.workers.tasks import process_uploaded_files


def _redis_settings() -> RedisSettings:
    """Parse settings.redis_url into ARQ's RedisSettings."""
    # Minimal parser — assumes redis://[host[:port]][/db]
    from urllib.parse import urlparse

    u = urlparse(settings.redis_url)
    db = 0
    if u.path and len(u.path) > 1:
        try:
            db = int(u.path.lstrip("/"))
        except ValueError:
            db = 0
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        database=db,
    )


class WorkerSettings:
    """ARQ worker config — tasks list, redis connection, retry policy."""

    functions = [process_uploaded_files]
    redis_settings = _redis_settings()
    max_jobs = 4
    job_timeout = 60 * 60  # 1h max per job (full pipeline on 30k PHHs ≈ 18min)
    keep_result_forever = True
