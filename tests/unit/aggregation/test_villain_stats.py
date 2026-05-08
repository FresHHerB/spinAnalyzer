"""Tests for src/aggregation/villain_stats.py."""

import polars as pl
import pytest

from src.aggregation.villain_stats import compute_villain_stats


def _dp_row(**overrides):
    """Build a synthetic DP-shaped dict with required defaults."""
    base = {
        "villain_name": "V",
        "hand_id": "H1",
        "street": "preflop",
        "villain_action": "fold",
        "villain_position": "BB",
        "villain_bet_size_pot_pct": None,
        "preflop_aggressor": None,
        "current_aggressor": None,
        "action_number_in_street": 0,
        "line_tag": "none",
        "went_to_showdown": False,
        "villain_won": None,
    }
    base.update(overrides)
    return base


def _df(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


class TestEmptyInput:
    def test_empty_df_returns_empty(self) -> None:
        empty = pl.DataFrame(schema={"villain_name": pl.Utf8})
        out = compute_villain_stats(empty)
        assert out.is_empty()


class TestVPIPAndPFR:
    def test_villain_folds_every_hand_vpip_zero(self) -> None:
        rows = [_dp_row(hand_id=f"H{i}") for i in range(10)]
        out = compute_villain_stats(_df(rows))
        v = out.filter(pl.col("villain_name") == "V").to_dicts()[0]
        assert v["vpip"] == 0.0
        assert v["pfr"] == 0.0

    def test_villain_raises_every_hand_vpip_pfr_100(self) -> None:
        rows = [
            _dp_row(hand_id=f"H{i}", villain_action="raise") for i in range(5)
        ]
        out = compute_villain_stats(_df(rows))
        v = out.filter(pl.col("villain_name") == "V").to_dicts()[0]
        assert v["vpip"] == 100.0
        assert v["pfr"] == 100.0

    def test_villain_calls_only_vpip_100_pfr_0(self) -> None:
        rows = [_dp_row(hand_id=f"H{i}", villain_action="call") for i in range(4)]
        out = compute_villain_stats(_df(rows))
        v = out.filter(pl.col("villain_name") == "V").to_dicts()[0]
        assert v["vpip"] == 100.0
        assert v["pfr"] == 0.0


class TestCounts:
    def test_n_hands_and_n_decisions(self) -> None:
        rows = [
            _dp_row(hand_id="H1", action_number_in_street=0),
            _dp_row(hand_id="H1", street="flop", action_number_in_street=0),
            _dp_row(hand_id="H2", action_number_in_street=0),
        ]
        out = compute_villain_stats(_df(rows))
        v = out.to_dicts()[0]
        assert v["n_hands"] == 2
        assert v["n_decisions"] == 3


class TestSBLimp:
    def test_sb_limp_pct(self) -> None:
        rows = [
            _dp_row(hand_id="H1", villain_action="call", villain_position="BTN"),
            _dp_row(hand_id="H2", villain_action="raise", villain_position="BTN"),
            _dp_row(hand_id="H3", villain_action="call", villain_position="BB"),
        ]
        out = compute_villain_stats(_df(rows))
        v = out.to_dicts()[0]
        # 1 of 3 first-actions is BTN+call = 33.3%
        assert abs(v["sb_limp_pct"] - 33.333) < 0.5


class TestThreeBet:
    def test_3bet_pct(self) -> None:
        rows = [
            # Facing hero raise, villain raises (3bet)
            _dp_row(
                hand_id="H1", villain_action="raise",
                current_aggressor="hero", action_number_in_street=1,
            ),
            # Facing hero raise, villain folds
            _dp_row(
                hand_id="H2", villain_action="fold",
                current_aggressor="hero", action_number_in_street=1,
            ),
            # Facing hero raise, villain calls
            _dp_row(
                hand_id="H3", villain_action="call",
                current_aggressor="hero", action_number_in_street=1,
            ),
        ]
        out = compute_villain_stats(_df(rows))
        v = out.to_dicts()[0]
        # 1 / 3 = 33.3%
        assert abs(v["threebet_pct"] - 33.333) < 0.5


class TestCbet:
    def test_cbet_flop_pct(self) -> None:
        rows = [
            # Villain is PF agg, first to act on flop, bets → cbet
            _dp_row(
                hand_id="H1", street="flop", villain_action="bet",
                preflop_aggressor="villain", action_number_in_street=0,
                villain_bet_size_pot_pct=66.0,
            ),
            # Villain is PF agg, first to act on flop, checks
            _dp_row(
                hand_id="H2", street="flop", villain_action="check",
                preflop_aggressor="villain", action_number_in_street=0,
            ),
        ]
        out = compute_villain_stats(_df(rows))
        v = out.to_dicts()[0]
        assert v["cbet_flop_pct"] == 50.0


class TestShowdownPct:
    def test_showdown_pct(self) -> None:
        rows = [
            _dp_row(hand_id="H1", went_to_showdown=True),
            _dp_row(hand_id="H2", went_to_showdown=False),
        ]
        out = compute_villain_stats(_df(rows))
        v = out.to_dicts()[0]
        assert v["showdown_pct"] == 50.0


class TestMissingColumnRaises:
    def test_missing_required_column_raises(self) -> None:
        df = pl.DataFrame({"villain_name": ["V"]})
        with pytest.raises(ValueError):
            compute_villain_stats(df)


class TestMultipleVillains:
    def test_two_villains_aggregated_separately(self) -> None:
        rows = [
            _dp_row(villain_name="A", hand_id="H1", villain_action="raise"),
            _dp_row(villain_name="B", hand_id="H1", villain_action="fold"),
        ]
        out = compute_villain_stats(_df(rows))
        names = sorted(out["villain_name"].to_list())
        assert names == ["A", "B"]
        a = out.filter(pl.col("villain_name") == "A").to_dicts()[0]
        b = out.filter(pl.col("villain_name") == "B").to_dicts()[0]
        assert a["pfr"] == 100.0
        assert b["pfr"] == 0.0
