"""Tests for src/hand_eval/equity.py."""

import time

import pytest

from src.hand_eval.equity import equity_vs_random


class TestEquitySanity:
    def test_aa_preflop_high_equity(self) -> None:
        eq = equity_vs_random(["Ah", "Ad"], [], samples=400, seed=42)
        assert eq > 0.80, f"AA preflop equity {eq} should be > 0.80"

    def test_72o_preflop_low_equity(self) -> None:
        eq = equity_vs_random(["7d", "2c"], [], samples=400, seed=42)
        assert eq < 0.40, f"72o preflop equity {eq} should be < 0.40"

    def test_river_made_nuts_full_equity(self) -> None:
        # Royal flush on the river: 100% equity
        eq = equity_vs_random(
            ["Ah", "Kh"], ["Qh", "Jh", "Th", "2c", "3d"], samples=200, seed=1
        )
        assert eq == 1.0

    def test_river_dead_air(self) -> None:
        # 7-2 unimproved on a non-straight, non-flush, paired board.
        # We play 7-high; opponent plays at minimum the board pair + a kicker.
        eq = equity_vs_random(
            ["7d", "2c"], ["Kh", "Kd", "9c", "5h", "3s"], samples=200, seed=1
        )
        assert eq < 0.20

    def test_flush_draw_on_flop(self) -> None:
        # Nut flush draw + overcards: ~33-40% vs random
        eq = equity_vs_random(
            ["Ah", "Kh"], ["Qh", "9h", "2c"], samples=400, seed=7
        )
        assert 0.50 < eq < 0.85, f"AhKh on Qh9h2c equity = {eq}"


class TestEquityRange:
    @pytest.mark.parametrize(
        "hole,board",
        [
            (["Ah", "Kc"], []),
            (["7d", "2c"], []),
            (["Kh", "Kc"], ["Kd", "9d", "4c"]),
            (["Ah", "Qh"], ["Kh", "9h", "2c", "5d"]),
        ],
    )
    def test_equity_in_unit_interval(self, hole, board) -> None:
        eq = equity_vs_random(hole, board, samples=200, seed=0)
        assert 0.0 <= eq <= 1.0

    def test_seed_reproducibility(self) -> None:
        a = equity_vs_random(["Ah", "Ad"], ["7c", "2d", "4h"], samples=100, seed=99)
        b = equity_vs_random(["Ah", "Ad"], ["7c", "2d", "4h"], samples=100, seed=99)
        assert a == b


class TestPerformance:
    def test_1000_samples_under_500ms(self) -> None:
        start = time.perf_counter()
        equity_vs_random(["Ah", "Kh"], ["Qh", "9h", "2c"], samples=1000, seed=1)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"1000 samples took {elapsed:.3f}s (target < 0.5s)"


class TestInvalidInputs:
    def test_invalid_hole(self) -> None:
        with pytest.raises(ValueError):
            equity_vs_random(["Ah"], ["Kh", "9d", "4c"])

    def test_invalid_samples(self) -> None:
        with pytest.raises(ValueError):
            equity_vs_random(["Ah", "Kc"], [], samples=0)
