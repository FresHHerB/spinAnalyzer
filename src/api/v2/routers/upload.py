"""POST /upload — accept multipart files, enqueue ARQ pipeline job.

Falls back to synchronous in-process execution if ARQ/Redis is not
available (useful for local dev and tests).
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from src.config.settings import settings
from src.services.etl_pipeline import run_full_pipeline

router = APIRouter(prefix="/upload", tags=["upload"])

# Resolved per-request inside _upload_dir() so monkeypatched settings
# are honoured in tests (no eager mkdir at import time).
ALLOWED_EXTS = {".xml", ".txt", ".log", ".zip", ".phh"}


def _upload_dir() -> Path:
    out = settings.data_dir / "uploads"
    out.mkdir(parents=True, exist_ok=True)
    return out


class UploadResponse(BaseModel):
    job_id: str
    queued_files: list[str]
    mode: str  # "arq" or "sync"


def _save_upload(file: UploadFile, dest_dir: Path) -> Path:
    """Persist a multipart upload to disk under `dest_dir`. Returns the path."""
    name = Path(file.filename or "unnamed").name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTS:
        raise HTTPException(400, f"unsupported extension: {suffix!r}")
    out = dest_dir / name
    with open(out, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return out


async def _try_enqueue_arq(job_id: str, paths: list[str]) -> bool:
    """Attempt to enqueue via ARQ. Returns True on success."""
    try:
        from arq import create_pool

        from src.workers.arq_worker import WorkerSettings

        pool = await create_pool(WorkerSettings.redis_settings)
        await pool.enqueue_job(
            "process_uploaded_files",
            paths,
            _job_id=job_id,
        )
        await pool.close()
        return True
    except Exception as e:
        logger.warning(f"ARQ enqueue failed, falling back to sync: {e}")
        return False


@router.post("", response_model=UploadResponse)
async def upload_files(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    if not files:
        raise HTTPException(400, "no files provided")

    job_id = uuid.uuid4().hex[:12]
    job_dir = _upload_dir() / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for f in files:
        paths.append(_save_upload(f, job_dir))

    # Try ARQ first; fall back to FastAPI BackgroundTasks if Redis is down.
    arq_ok = await _try_enqueue_arq(job_id, [str(p) for p in paths])
    if arq_ok:
        return UploadResponse(
            job_id=job_id,
            queued_files=[p.name for p in paths],
            mode="arq",
        )

    # Sync fallback: run in-process via BackgroundTasks
    def _run() -> dict[str, Any]:
        return run_full_pipeline(paths, job_id=job_id)

    background.add_task(_run)
    return UploadResponse(
        job_id=job_id,
        queued_files=[p.name for p in paths],
        mode="sync",
    )
