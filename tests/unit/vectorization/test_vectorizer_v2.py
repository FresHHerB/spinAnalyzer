"""Tests for src/vectorization/vectorizer_v2.py."""

from pathlib import Path

import numpy as np
import pytest

from src.context.extractor_v2 import extract_from_phh_path
from src.vectorization.vectorizer_v2 import (
    expected_dimension,
    vectorize_dp,
    vectorize_dps,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "hands"


def test_expected_dimension_is_99() -> None:
    assert expected_dimension() == 99


def test_vectorize_single_dp() -> None:
    dps = extract_from_phh_path(FIXTURES / "showdown_simple.phh")
    assert dps
    vec = vectorize_dp(dps[0])
    assert vec.shape == (99,)
    assert vec.dtype == np.float32
    assert np.isfinite(vec).all()


def test_vectorize_batch() -> None:
    dps = extract_from_phh_path(FIXTURES / "multi_street_betfold.phh")
    arr = vectorize_dps(dps)
    assert arr.shape == (len(dps), 99)
    assert np.isfinite(arr).all()


def test_vectorization_deterministic() -> None:
    dps = extract_from_phh_path(FIXTURES / "showdown_simple.phh")
    a = vectorize_dp(dps[0])
    b = vectorize_dp(dps[0])
    np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "preflop_fold.phh",
        "multi_street_betfold.phh",
        "showdown_simple.phh",
        "showdown_postflop.phh",
        "multi_action_pf.phh",
    ],
)
def test_vectorize_all_fixtures(fixture_name: str) -> None:
    dps = extract_from_phh_path(FIXTURES / fixture_name)
    if not dps:
        pytest.skip("no DPs (villain had no decision)")
    arr = vectorize_dps(dps)
    assert arr.shape[1] == 99
    assert np.isfinite(arr).all()


def test_hand_strength_dim_populated_when_villain_revealed() -> None:
    """Regression test for v1 bug: hand_strength dim was always zero
    because _extract_villain_hand_info returned (None, None, None).
    With v2, when villain reveals at showdown, those bits should fire.
    """
    from src.vectorization.vectorizer import FeatureConfig

    cfg = FeatureConfig()
    start, end = cfg.indices["hand_strength"]
    dps = extract_from_phh_path(FIXTURES / "showdown_simple.phh")
    arr = vectorize_dps(dps)
    hs_block = arr[:, start:end]
    # At least one DP should have a non-zero hand_strength dim
    assert (hs_block.sum(axis=1) > 0).any(), (
        "v1 bug regressed: hand_strength block all zero"
    )
