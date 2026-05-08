"""ARQ task definitions.

Each task is `async` (ARQ requirement) but delegates to the synchronous
orchestrator in `src.services.etl_pipeline`. Heavy work is offloaded to
a thread executor so the event loop isn't blocked.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from src.services.etl_pipeline import run_full_pipeline


async def process_uploaded_files(
    ctx: dict[str, Any],
    upload_paths: list[str],
) -> dict[str, Any]:
    """Run the full v2 pipeline on a list of uploaded XML/TXT/ZIP/PHH files.

    `ctx['job_id']` (set automatically by ARQ from the job ID) drives
    the pub/sub progress channel.
    """
    job_id = ctx.get("job_id")
    paths = [Path(p) for p in upload_paths]

    # run_full_pipeline is CPU-bound; run in a thread to keep the event
    # loop responsive for other tasks / WebSocket fan-out.
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: run_full_pipeline(paths, job_id=job_id),
    )
