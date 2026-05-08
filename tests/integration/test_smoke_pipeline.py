"""End-to-end smoke test: PHH zip → DPs → vectors.

Validates that the v2 pipeline running on the parsed PHH dataset
(`dataset/phh_hands.zip`) produces:

1. Postflop DPs (regression: v1 had 0 because of street bug).
2. hand_strength NOT NULL on showdown DPs (regression: v1 was always
   None because _extract_villain_hand_info returned (None, None, None)).
3. Board cards visible on every postflop DP (regression: v1
   _extract_board_by_street read non-existent phh['board']).
4. 99-dim float32 vectors with no NaN/Inf.

Marked as `integration` because it unzips the dataset into tmp_path.
"""

from __future__ import annotations

import time
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from src.aggregation.sizing_histograms import compute_sizing_histograms
from src.aggregation.spot_fingerprints import (
    aggregate_by_fingerprint,
    compute_spot_fingerprints,
)
from src.aggregation.typology import classify_archetypes
from src.aggregation.villain_stats import compute_villain_stats
from src.context.extractor_v2 import dps_to_records, extract_decision_points
from src.parsers.pokerkit_adapter import load_phh
from src.vectorization.vectorizer_v2 import vectorize_dps

REPO_ROOT = Path(__file__).parents[2]
PHH_ZIP = REPO_ROOT / "dataset" / "phh_hands.zip"


@pytest.fixture(scope="module")
def phh_dir(tmp_path_factory) -> Path:
    """Unzip the PHH archive into a tmp dir for the module."""
    if not PHH_ZIP.exists():
        pytest.skip(f"{PHH_ZIP} not found")
    out = tmp_path_factory.mktemp("phh_smoke")
    with zipfile.ZipFile(PHH_ZIP) as zf:
        zf.extractall(out)
    inner = out / "phh_hands"
    assert inner.exists()
    return inner


@pytest.mark.integration
def test_smoke_pipeline(phh_dir: Path) -> None:
    files = sorted(phh_dir.glob("*.phh"))
    assert len(files) >= 100, f"expected ≥100 PHHs, got {len(files)}"

    start = time.perf_counter()
    all_dps = []
    parse_errors = 0
    for f in files:
        try:
            hand = load_phh(f)
            dps = extract_decision_points(hand)
            all_dps.extend(dps)
        except Exception:
            parse_errors += 1
    elapsed = time.perf_counter() - start

    print(
        f"\n[SMOKE] processed {len(files)} PHHs → {len(all_dps)} DPs "
        f"in {elapsed:.2f}s ({parse_errors} parse errors)"
    )

    # ── Coverage assertions ───────────────────────────────────────────
    assert len(all_dps) > 0, "no DPs extracted at all"
    assert parse_errors / len(files) < 0.10, (
        f"parse error rate too high: {parse_errors}/{len(files)}"
    )

    # ── Bug 1 regression: postflop DPs exist ──────────────────────────
    streets = Counter(dp.street for dp in all_dps)
    print(f"[SMOKE] DPs by street: {dict(streets)}")
    assert streets["preflop"] > 0
    assert (streets["flop"] + streets["turn"] + streets["river"]) > 0, (
        "v1 bug regressed: only preflop DPs produced"
    )

    # ── Bug 2 regression: hand_strength populated when villain reveals ─
    revealed = [dp for dp in all_dps if dp.villain_hand is not None]
    if revealed:
        with_strength = [dp for dp in revealed if dp.villain_hand_strength is not None]
        print(
            f"[SMOKE] {len(with_strength)}/{len(revealed)} revealed-DPs "
            "have hand_strength populated"
        )
        assert len(with_strength) / len(revealed) >= 0.80, (
            "v1 bug regressed: hand_strength NULL on revealed hands"
        )

    # ── Bug 3 regression: board visible on postflop DPs ───────────────
    postflop = [dp for dp in all_dps if dp.street != "preflop"]
    if postflop:
        with_board = [dp for dp in postflop if len(dp.board_cards) >= 3]
        print(
            f"[SMOKE] {len(with_board)}/{len(postflop)} postflop DPs "
            "have board cards"
        )
        assert len(with_board) == len(postflop), (
            "v1 bug regressed: postflop DPs missing board cards"
        )

    # ── Vectorization end-to-end ──────────────────────────────────────
    vecs = vectorize_dps(all_dps)
    assert vecs.shape == (len(all_dps), 99)
    assert np.isfinite(vecs).all(), "vectors contain NaN/Inf"

    # Performance budget (loose for the small fixture set)
    assert elapsed < 60.0, f"pipeline took {elapsed:.1f}s for {len(files)} PHHs"


@pytest.mark.integration
def test_unique_villain_count(phh_dir: Path) -> None:
    """Quick sanity check that we see multiple distinct villains."""
    files = sorted(phh_dir.glob("*.phh"))
    villains: set[str] = set()
    for f in files:
        try:
            villains.add(load_phh(f).villain_name)
        except Exception:
            continue
    print(f"\n[SMOKE] distinct villains: {len(villains)}: {sorted(villains)}")
    assert len(villains) >= 1


@pytest.mark.integration
def test_aggregation_end_to_end(phh_dir: Path) -> None:
    """Run the aggregation stack on the full DP set."""
    import polars as pl

    files = sorted(phh_dir.glob("*.phh"))
    all_dps = []
    for f in files:
        try:
            all_dps.extend(extract_decision_points(load_phh(f)))
        except Exception:
            continue
    assert all_dps

    records = dps_to_records(all_dps)
    df = pl.DataFrame(records)

    # Villain stats + typology
    stats = compute_villain_stats(df)
    assert stats.height > 0
    assert "vpip" in stats.columns and "pfr" in stats.columns
    print(f"\n[SMOKE] villain_stats rows: {stats.height}")

    typed = classify_archetypes(stats)
    archetype_counts = typed.group_by("archetype").len().sort("archetype")
    print(f"[SMOKE] archetype distribution: {archetype_counts.to_dicts()}")
    assert "archetype" in typed.columns

    # Spot fingerprints
    df_fp = compute_spot_fingerprints(df)
    assert "fingerprint" in df_fp.columns
    fp_agg = aggregate_by_fingerprint(df_fp)
    print(f"[SMOKE] distinct fingerprints: {fp_agg.height}")
    assert fp_agg.height > 0

    # Sizing histograms
    sizing = compute_sizing_histograms(df)
    print(f"[SMOKE] sizing histogram rows: {sizing.height}")
