"""Tests for src/context/street_detector.py."""

from pathlib import Path

import pytest

from src.context.street_detector import STREETS, detect_streets, split_by_street
from src.parsers.pokerkit_adapter import load_phh, replay_to_list

FIXTURES = Path(__file__).parents[2] / "fixtures" / "hands"


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
def test_buckets_total_equals_snapshot_total(fixture_name: str) -> None:
    hand = load_phh(FIXTURES / fixture_name)
    snaps = replay_to_list(hand)
    buckets = split_by_street(snaps)
    assert sum(len(v) for v in buckets.values()) == len(snaps)


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
def test_buckets_keyed_by_canonical_streets(fixture_name: str) -> None:
    hand = load_phh(FIXTURES / fixture_name)
    buckets = detect_streets(hand)
    assert set(buckets.keys()) == set(STREETS)


def test_multi_street_betfold_buckets() -> None:
    hand = load_phh(FIXTURES / "multi_street_betfold.phh")
    buckets = detect_streets(hand)
    assert len(buckets["preflop"]) == 2
    assert len(buckets["flop"]) == 2
    assert len(buckets["turn"]) == 3
    assert len(buckets["river"]) == 2


def test_preflop_only_hand_has_no_postflop_buckets() -> None:
    hand = load_phh(FIXTURES / "preflop_fold.phh")
    buckets = detect_streets(hand)
    assert len(buckets["preflop"]) == 2
    assert len(buckets["flop"]) == 0
    assert len(buckets["turn"]) == 0
    assert len(buckets["river"]) == 0


def test_each_snapshot_lands_in_correct_bucket() -> None:
    hand = load_phh(FIXTURES / "multi_street_betfold.phh")
    buckets = detect_streets(hand)
    for street, snaps in buckets.items():
        for snap in snaps:
            assert snap.street == street
