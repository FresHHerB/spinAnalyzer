"""FAISS rebuild adapted for v2: read DPs from Hive-partitioned parquet
via DuckDB, vectorize with vectorizer_v2, then build per-villain HNSW
indices using the existing v1 IndexBuilder primitives.

Layout produced:

    indices/
    ├── {villain_name}.faiss
    ├── {villain_name}_ids.pkl
    └── {villain_name}_metadata.json

DP layout consumed:

    dataset/dps/villain_name=<name>/part-*.parquet
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import polars as pl
from loguru import logger

from src.context.dp_schema import DecisionPoint
from src.indexing.build_indices import IndexBuilder
from src.vectorization.vectorizer import Vectorizer
from src.vectorization.vectorizer_v2 import vectorize_dps


def write_dps_parquet_partitioned(
    dps: list[DecisionPoint],
    out_dir: Path | str,
) -> Path:
    """Materialize DPs to a Hive-partitioned parquet dataset.

    One parquet file per villain under `out_dir/villain_name=<name>/`.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not dps:
        return out

    records = [dp.model_dump() for dp in dps]
    df = pl.DataFrame(records)
    # Convert nested Pydantic blocks to dict-typed columns serializable
    # by pyarrow. Polars handles `Struct`-typed cols out of the box; for
    # nested null Optional[Struct] we rely on the fact that empty/None
    # was already model_dumped by Pydantic into either dict or None.

    # Partition by villain
    for villain in df["villain_name"].unique().to_list():
        sub = df.filter(pl.col("villain_name") == villain)
        part_dir = out / f"villain_name={villain}"
        part_dir.mkdir(parents=True, exist_ok=True)
        sub.write_parquet(part_dir / "part-0.parquet")
    return out


def _load_dps_via_duckdb(dps_dir: Path | str, villain: str | None = None) -> pl.DataFrame:
    """Read DP parquet partitions back as a Polars DataFrame.

    If `villain` is given, only that partition is read.
    """
    dps_path = Path(dps_dir)
    if villain is not None:
        glob = str(dps_path / f"villain_name={villain}" / "*.parquet")
    else:
        glob = str(dps_path / "**" / "*.parquet")

    con = duckdb.connect()
    arrow_table = con.sql(
        f"SELECT * FROM read_parquet('{glob}', hive_partitioning=true)"
    ).arrow()
    return pl.from_arrow(arrow_table)


def _df_to_dps(df: pl.DataFrame) -> list[DecisionPoint]:
    """Reconstruct DecisionPoint Pydantic objects from a Polars DataFrame."""
    return [DecisionPoint.model_validate(r) for r in df.to_dicts()]


def rebuild_indices(
    dps_dir: Path | str,
    indices_dir: Path | str,
    *,
    villain: str | None = None,
    hnsw_m: int = 32,
) -> dict[str, int]:
    """Rebuild FAISS HNSW indices, one per villain.

    Returns:
        dict {villain_name: n_vectors}.
    """
    builder = IndexBuilder(indices_dir=Path(indices_dir), dimension=99)
    vectorizer = Vectorizer()

    # Discover villains by listing partition directories
    dps_path = Path(dps_dir)
    if villain is not None:
        villains = [villain]
    else:
        villains = sorted(
            p.name.split("=", 1)[1]
            for p in dps_path.glob("villain_name=*")
            if p.is_dir()
        )

    summary: dict[str, int] = {}
    for v in villains:
        df = _load_dps_via_duckdb(dps_path, villain=v)
        if df.is_empty():
            logger.warning(f"no DPs for villain {v}; skipping")
            continue

        dps = _df_to_dps(df)
        vecs = vectorize_dps(dps, vectorizer=vectorizer)
        decision_ids = [dp.decision_id for dp in dps]

        # Reuse v1 internal primitives
        index = builder._create_faiss_index(vecs, index_type="HNSW", hnsw_m=hnsw_m)
        builder._save_index(v, index, decision_ids, vecs)
        summary[v] = len(decision_ids)
        logger.info(f"built index for {v}: {len(decision_ids)} vectors")

    # Top-level summary file (for the API to discover available villains).
    summary_path = Path(indices_dir) / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_indices": len(summary),
                "total_vectors": sum(summary.values()),
                "villains": [{"name": k, "vectors": n} for k, n in summary.items()],
            },
            f,
            indent=2,
        )
    return summary
