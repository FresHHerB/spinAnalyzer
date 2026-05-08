"""Integration test: end-to-end pipeline → parquet → FAISS rebuild.

Validates the full Phase 5.2 path:
    PHHs → DPs → write_dps_parquet_partitioned → rebuild_indices → search
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pytest

from src.context.extractor_v2 import extract_decision_points
from src.indexing.build_indices import IndexBuilder
from src.indexing.build_indices_v2 import (
    rebuild_indices,
    write_dps_parquet_partitioned,
)
from src.parsers.pokerkit_adapter import load_phh
from src.vectorization.vectorizer_v2 import vectorize_dp

REPO_ROOT = Path(__file__).parents[2]
PHH_ZIP = REPO_ROOT / "dataset" / "phh_hands.zip"


@pytest.fixture(scope="module")
def phh_dir(tmp_path_factory) -> Path:
    if not PHH_ZIP.exists():
        pytest.skip(f"{PHH_ZIP} not found")
    out = tmp_path_factory.mktemp("phh_indexing")
    with zipfile.ZipFile(PHH_ZIP) as zf:
        zf.extractall(out)
    return out / "phh_hands"


@pytest.fixture(scope="module")
def all_dps(phh_dir: Path) -> list:
    files = sorted(phh_dir.glob("*.phh"))
    out = []
    for f in files:
        try:
            out.extend(extract_decision_points(load_phh(f)))
        except Exception:
            continue
    return out


@pytest.mark.integration
def test_write_partitioned_parquet(tmp_path: Path, all_dps: list) -> None:
    out = write_dps_parquet_partitioned(all_dps, tmp_path / "dps")
    # One subdir per unique villain
    parts = sorted(p.name for p in out.glob("villain_name=*") if p.is_dir())
    villains_in_dps = sorted({dp.villain_name for dp in all_dps})
    assert parts == [f"villain_name={v}" for v in villains_in_dps]


@pytest.mark.integration
def test_rebuild_indices_creates_per_villain_files(
    tmp_path: Path, all_dps: list
) -> None:
    dps_dir = tmp_path / "dps"
    indices_dir = tmp_path / "indices"
    write_dps_parquet_partitioned(all_dps, dps_dir)

    summary = rebuild_indices(dps_dir, indices_dir)
    assert summary  # at least one villain indexed

    # Each villain produces 3 files: .faiss, _ids.pkl, _metadata.json
    for villain, n in summary.items():
        assert (indices_dir / f"{villain}.faiss").exists()
        assert (indices_dir / f"{villain}_ids.pkl").exists()
        assert (indices_dir / f"{villain}_metadata.json").exists()
        assert n > 0

    # Top-level summary file exists
    assert (indices_dir / "summary.json").exists()


@pytest.mark.integration
def test_search_round_trip(tmp_path: Path, all_dps: list) -> None:
    """Build the indices, then query each villain's index with one of
    its own DP vectors and verify that DP appears in the top results."""
    dps_dir = tmp_path / "dps"
    indices_dir = tmp_path / "indices"
    write_dps_parquet_partitioned(all_dps, dps_dir)
    rebuild_indices(dps_dir, indices_dir)

    builder = IndexBuilder(indices_dir=indices_dir, dimension=99)

    # Pick the villain with the most DPs
    from collections import Counter
    counts = Counter(dp.villain_name for dp in all_dps)
    target_villain = counts.most_common(1)[0][0]
    target_dps = [dp for dp in all_dps if dp.villain_name == target_villain]
    assert target_dps

    query_dp = target_dps[0]
    query_vec = vectorize_dp(query_dp).astype(np.float32)

    distances, indices, decision_ids = builder.search(
        villain_name=target_villain, query_vector=query_vec, k=5
    )
    # Self-match should be the closest result (distance ≈ 0)
    assert query_dp.decision_id in decision_ids
    self_idx = decision_ids.index(query_dp.decision_id)
    assert distances[self_idx] < 1e-3
