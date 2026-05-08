"""Tests for spot_fingerprints and sizing_histograms."""

import polars as pl

from src.aggregation.sizing_histograms import compute_sizing_histograms
from src.aggregation.spot_fingerprints import (
    aggregate_by_fingerprint,
    compute_spot_fingerprints,
)


def _row(**kwargs):
    base = {
        "villain_name": "V", "hand_id": "H1", "street": "flop",
        "villain_action": "check", "villain_position": "OOP",
        "spr": 5.0, "action_path": "V_X",
        "board_texture": {"monotone": False, "two_tone": True, "rainbow": False, "paired": False},
        "villain_bet_size_pot_pct": None,
    }
    base.update(kwargs)
    return base


class TestFingerprint:
    def test_fingerprint_is_deterministic(self) -> None:
        df = pl.DataFrame([_row()])
        a = compute_spot_fingerprints(df)
        b = compute_spot_fingerprints(df)
        assert a["fingerprint"][0] == b["fingerprint"][0]

    def test_different_paths_different_fingerprints(self) -> None:
        df = pl.DataFrame([
            _row(action_path="V_X"),
            _row(action_path="V_B66"),
        ])
        out = compute_spot_fingerprints(df)
        fps = out["fingerprint"].to_list()
        assert fps[0] != fps[1]

    def test_same_spot_same_fingerprint(self) -> None:
        df = pl.DataFrame([_row(hand_id="H1"), _row(hand_id="H2")])
        out = compute_spot_fingerprints(df)
        fps = out["fingerprint"].to_list()
        assert fps[0] == fps[1]


class TestAggregateByFingerprint:
    def test_aggregate_pivots_actions(self) -> None:
        df = pl.DataFrame([
            _row(hand_id="H1", villain_action="check"),
            _row(hand_id="H2", villain_action="check"),
            _row(hand_id="H3", villain_action="bet"),
        ])
        out = aggregate_by_fingerprint(df)
        # 1 fingerprint, 1 row
        assert len(out) == 1
        row = out.to_dicts()[0]
        assert row["count_check"] == 2
        assert row["count_bet"] == 1
        assert row["n"] == 3


class TestSizingHistograms:
    def test_buckets_assigned(self) -> None:
        df = pl.DataFrame([
            _row(villain_action="bet", villain_bet_size_pot_pct=20),  # tiny
            _row(villain_action="bet", villain_bet_size_pot_pct=50),  # half
            _row(villain_action="bet", villain_bet_size_pot_pct=70),  # two-thirds
            _row(villain_action="bet", villain_bet_size_pot_pct=120),  # overbet
        ])
        out = compute_sizing_histograms(df)
        rows = {r["bucket"]: r["count"] for r in out.to_dicts()}
        assert rows.get("tiny_le33") == 1
        assert rows.get("half_pot") == 1
        assert rows.get("two_thirds") == 1
        assert rows.get("overbet") == 1

    def test_only_postflop_counted(self) -> None:
        df = pl.DataFrame([
            _row(street="preflop", villain_action="bet", villain_bet_size_pot_pct=200),
            _row(street="flop", villain_action="bet", villain_bet_size_pot_pct=50),
        ])
        out = compute_sizing_histograms(df)
        # Only the flop bet should be histogrammed
        assert len(out) == 1
        assert out["street"][0] == "flop"

    def test_empty_input(self) -> None:
        df = pl.DataFrame(schema={
            "villain_name": pl.Utf8, "street": pl.Utf8,
            "villain_action": pl.Utf8, "villain_bet_size_pot_pct": pl.Float64,
        })
        out = compute_sizing_histograms(df)
        assert out.is_empty()
