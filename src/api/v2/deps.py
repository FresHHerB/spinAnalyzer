"""FastAPI dependency providers for the v2 API.

All heavy resources (DuckDB connections, FAISS indices, Polars DFs)
are lazy-loaded once and cached. Tests can override by monkeypatching
the module-level globals.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import duckdb
import polars as pl

from src.config.settings import settings as _settings
from src.indexing.build_indices import IndexBuilder

# These globals exist primarily so tests can override them by writing
# to `src.api.v2.deps.DPS_DIR = ...` before any request is handled.
DPS_DIR: Path = _settings.dps_dir
INDICES_DIR: Path = _settings.indices_dir
PROFILES_PATH: Path = _settings.profiles_path
SIZING_PATH: Path = _settings.data_dir / "sizing_histograms.parquet"


def get_dps_dir() -> Path:
    return DPS_DIR


def get_indices_dir() -> Path:
    return INDICES_DIR


@lru_cache(maxsize=1)
def get_index_builder() -> IndexBuilder:
    return IndexBuilder(indices_dir=INDICES_DIR, dimension=99)


def reset_caches() -> None:
    """Test helper: clear all cached resources."""
    get_index_builder.cache_clear()


def load_dps(villain: str | None = None) -> pl.DataFrame:
    """Read DPs from Hive-partitioned parquet via DuckDB.

    Filters to the given villain if provided. Returns an empty
    DataFrame if no parquet partitions exist yet.
    """
    base = Path(DPS_DIR)
    if villain is not None:
        glob = str(base / f"villain_name={villain}" / "*.parquet")
    else:
        glob = str(base / "**" / "*.parquet")

    con = duckdb.connect()
    try:
        arrow = con.sql(
            f"SELECT * FROM read_parquet('{glob}', hive_partitioning=true)"
        ).arrow()
    except duckdb.IOException:
        # No parquet files match — return empty DF.
        return pl.DataFrame()
    return pl.from_arrow(arrow)


def load_villain_profiles() -> pl.DataFrame:
    """Read the cached villain_profiles.parquet (one row per villain)."""
    p = Path(PROFILES_PATH)
    if not p.exists():
        return pl.DataFrame()
    return pl.read_parquet(p)


def load_sizing_histograms() -> pl.DataFrame:
    """Read the cached sizing_histograms.parquet."""
    p = Path(SIZING_PATH)
    if not p.exists():
        return pl.DataFrame()
    return pl.read_parquet(p)
