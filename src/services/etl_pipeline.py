"""ETL pipeline orchestrator.

Synchronous functions that move data through the v2 stages:

    parse_files     PHH/XML/TXT/ZIP → PHH files
    extract_dps     PHH files → DecisionPoint list (Pydantic)
    write_dps       DPs → Hive-partitioned parquet (dataset/dps/)
    aggregate       parquet → villain_profiles + sizing_histograms
    rebuild_indices parquet + DPs → FAISS HNSW per villain

Each stage publishes a progress event to `jobs:{job_id}` if a job_id is
provided. ARQ task definitions in `src.workers.tasks` wrap these
functions as async work items.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
from loguru import logger

from src.aggregation.sizing_histograms import compute_sizing_histograms
from src.aggregation.typology import classify_archetypes
from src.aggregation.villain_stats import compute_villain_stats
from src.api.v2 import deps
from src.config.settings import settings
from src.context.dp_schema import DecisionPoint
from src.context.extractor_v2 import (
    dps_to_records,
    extract_decision_points,
)
from src.indexing.build_indices_v2 import (
    rebuild_indices as faiss_rebuild,
    write_dps_parquet_partitioned,
)
from src.parsers.pokerkit_adapter import load_phh
from src.parsers.unified_parser import UnifiedParser
from src.services.cache import publish_progress


def _emit(job_id: str | None, stage: str, **kwargs: Any) -> None:
    """Publish a progress event if running under a job context."""
    if job_id is None:
        return
    publish_progress(job_id, {"stage": stage, **kwargs})


def stage_parse_files(
    input_paths: list[Path],
    phh_out_dir: Path,
    *,
    hu_only: bool = True,
    job_id: str | None = None,
) -> list[Path]:
    """Parse a list of XML/TXT/ZIP/PHH files into PHH files in `phh_out_dir`."""
    parser = UnifiedParser(output_dir=phh_out_dir)
    filters = {"heads_up_only": True} if hu_only else None

    out: list[Path] = []
    for i, p in enumerate(input_paths):
        out.extend(parser.parse_file(p, filters=filters))
        _emit(
            job_id, "parse",
            current=i + 1, total=len(input_paths),
            phhs_so_far=len(out), filename=p.name,
        )
    _emit(job_id, "parse_done", total_phhs=len(out))
    return out


def stage_extract_dps(
    phh_paths: list[Path],
    *,
    job_id: str | None = None,
) -> list[DecisionPoint]:
    """Extract DPs from a list of PHH files."""
    all_dps: list[DecisionPoint] = []
    errors = 0
    for i, f in enumerate(phh_paths):
        try:
            all_dps.extend(extract_decision_points(load_phh(f)))
        except Exception as e:
            errors += 1
            logger.debug(f"skipping {f.name}: {e}")
        if (i + 1) % 50 == 0 or i + 1 == len(phh_paths):
            _emit(
                job_id, "extract",
                current=i + 1, total=len(phh_paths),
                dps_so_far=len(all_dps), errors=errors,
            )
    _emit(
        job_id, "extract_done",
        total_dps=len(all_dps), errors=errors,
    )
    return all_dps


def stage_write_dps(
    dps: list[DecisionPoint],
    dps_dir: Path,
    *,
    job_id: str | None = None,
) -> Path:
    """Materialize DPs to Hive-partitioned parquet."""
    out = write_dps_parquet_partitioned(dps, dps_dir)
    _emit(
        job_id, "write_dps_done",
        path=str(out), n=len(dps),
    )
    return out


def stage_aggregate(
    dps: list[DecisionPoint],
    *,
    profiles_path: Path,
    sizing_path: Path,
    job_id: str | None = None,
) -> dict[str, int]:
    """Compute villain stats + typology + sizing histograms; persist parquet."""
    if not dps:
        _emit(job_id, "aggregate_skipped", reason="no DPs")
        return {"villains": 0, "sizing_rows": 0}

    df = pl.DataFrame(dps_to_records(dps))
    stats = classify_archetypes(compute_villain_stats(df))
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    stats.write_parquet(profiles_path)

    sizing = compute_sizing_histograms(df)
    sizing_path.parent.mkdir(parents=True, exist_ok=True)
    sizing.write_parquet(sizing_path)

    counts = {"villains": stats.height, "sizing_rows": sizing.height}
    _emit(job_id, "aggregate_done", **counts)
    return counts


def stage_rebuild_indices(
    dps_dir: Path,
    indices_dir: Path,
    *,
    villain: str | None = None,
    job_id: str | None = None,
) -> dict[str, int]:
    """Rebuild FAISS indices from parquet partitions."""
    summary = faiss_rebuild(dps_dir, indices_dir, villain=villain)
    _emit(
        job_id, "indices_done",
        villains=len(summary), total_vectors=sum(summary.values()),
    )
    return summary


def run_full_pipeline(
    input_paths: list[Path],
    *,
    phh_dir: Path | None = None,
    dps_dir: Path | None = None,
    indices_dir: Path | None = None,
    profiles_path: Path | None = None,
    sizing_path: Path | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """End-to-end pipeline: parse → extract → write → aggregate → index.

    All paths default to `settings`. Emits progress events if `job_id`
    is provided.
    """
    phh_dir = phh_dir or settings.phh_dir
    dps_dir = dps_dir or settings.dps_dir
    indices_dir = indices_dir or settings.indices_dir
    profiles_path = profiles_path or settings.profiles_path
    sizing_path = sizing_path or (settings.data_dir / "sizing_histograms.parquet")

    _emit(job_id, "pipeline_start", n_inputs=len(input_paths))

    phhs = stage_parse_files(input_paths, phh_dir, job_id=job_id)
    dps = stage_extract_dps(phhs, job_id=job_id)
    stage_write_dps(dps, dps_dir, job_id=job_id)
    agg = stage_aggregate(
        dps, profiles_path=profiles_path, sizing_path=sizing_path, job_id=job_id,
    )
    indices = stage_rebuild_indices(dps_dir, indices_dir, job_id=job_id)

    # Refresh API caches (they read from the same paths)
    deps.reset_caches()

    summary = {
        "n_input_files": len(input_paths),
        "n_phhs": len(phhs),
        "n_dps": len(dps),
        "n_villains": agg["villains"],
        "indices": indices,
    }
    _emit(job_id, "pipeline_done", **summary)
    return summary
