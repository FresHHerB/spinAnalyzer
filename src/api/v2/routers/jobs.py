"""GET /jobs/{id} — current state.
WebSocket /jobs/{id}/stream — live progress events from Redis pub/sub.

ARQ stores job state under `arq:job:{id}` keys. We expose a thin
read-only view of that state plus the pub/sub stream from
`src.services.cache.publish_progress`.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger

from src.services.cache import get_client

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict:
    """Read ARQ job state if available; otherwise minimal status."""
    pool = None
    try:
        from arq import create_pool
        from arq.jobs import Job

        from src.workers.arq_worker import WorkerSettings

        pool = await create_pool(WorkerSettings.redis_settings)
        job = Job(job_id, pool)
        info = await job.info()
        status = await job.status()
        return {
            "job_id": job_id,
            "status": str(status),
            "function": info.function if info else None,
            "args": list(info.args) if info and info.args else [],
            "enqueue_time": info.enqueue_time.isoformat() if info and info.enqueue_time else None,
            "result": info.result if info else None,
        }
    except Exception as e:
        logger.debug(f"ARQ unreachable, returning minimal status: {e}")
        return {"job_id": job_id, "status": "unknown"}
    finally:
        if pool is not None:
            try:
                await pool.close()
            except Exception:
                pass


async def _redis_subscribe(job_id: str):
    """Async generator yielding decoded events from `jobs:{job_id}`."""
    client = get_client()
    pubsub = client.pubsub()
    pubsub.subscribe(f"jobs:{job_id}")
    try:
        while True:
            msg = pubsub.get_message(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                yield json.loads(data)
            except (TypeError, json.JSONDecodeError):
                yield {"raw": data}
    finally:
        try:
            pubsub.unsubscribe()
            pubsub.close()
        except Exception:
            pass


@router.websocket("/{job_id}/stream")
async def stream_job(websocket: WebSocket, job_id: str) -> None:
    """Stream progress events for a job until completion or disconnect.

    Each message on the WS is one JSON-encoded progress event. The
    client should close the WS when it sees a `pipeline_done` event
    (or any event with `stage` ending in `_done` for terminal stages).
    """
    await websocket.accept()
    try:
        async for event in _redis_subscribe(job_id):
            await websocket.send_json(event)
            if event.get("stage") == "pipeline_done":
                break
    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.warning(f"WS stream error for {job_id}: {e}")
        try:
            await websocket.send_json({"stage": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
