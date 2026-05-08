"""Tests for src/hand_eval/blockers.py."""

import pytest

from src.hand_eval.blockers import compute_blockers


class TestNutFlushBlocker:
    def test_holding_ace_of_flushed_suit(self) -> None:
        # Ah Qh on Kh-9h-2c → board has 2 hearts, but we hold AceHearts
        # so opponent can't make nut flush (yet — board only 2 hearts;
        # need 3 of suit on board for nut flush threat). Adjust test:
        b = compute_blockers(["Ah", "Qd"], ["Kh", "9h", "2h", "3c", "4d"])
        assert b.blocks_nut_flush is True

    def test_no_blocker_without_three_of_suit(self) -> None:
        b = compute_blockers(["Ah", "Qd"], ["Kh", "9h", "2c"])
        assert b.blocks_nut_flush is False

    def test_no_blocker_without_ace(self) -> None:
        b = compute_blockers(["Kh", "Qh"], ["7h", "5h", "2h"])
        assert b.blocks_nut_flush is False


class TestNutStraightBlocker:
    def test_holding_top_straight_card(self) -> None:
        # Ah on KQT board — A blocks AQK + AT* nut straight combos
        b = compute_blockers(["Ah", "2c"], ["Kh", "Qd", "Tc"])
        assert b.blocks_nut_straight is True


class TestTopSetBlocker:
    def test_holding_top_board_rank(self) -> None:
        b = compute_blockers(["Kh", "2c"], ["Kd", "9d", "4c"])
        assert b.blocks_top_set is True

    def test_no_top_set_block_when_no_match(self) -> None:
        b = compute_blockers(["Ah", "Qc"], ["Kd", "9d", "4c"])
        assert b.blocks_top_set is False


class TestKickerBlockers:
    def test_ace_high_blocker_preflop(self) -> None:
        b = compute_blockers(["Ah", "2c"], [])
        assert b.has_ace_high_blocker is True

    def test_king_high_blocker(self) -> None:
        b = compute_blockers(["Kh", "2c"], ["7h", "9d", "4c"])
        assert b.has_king_high_blocker is True


class TestInvariants:
    @pytest.mark.parametrize(
        "hole,board",
        [
            (["Ah", "Kc"], ["Qh", "Jh", "Th"]),
            (["7d", "2c"], ["8h", "5d", "3c", "4h"]),
            (["Ks", "Kd"], ["Kh", "9d", "4c"]),
            (["Ah", "2c"], []),
        ],
    )
    def test_no_crash_for_various_inputs(self, hole, board) -> None:
        b = compute_blockers(hole, board)
        assert b is not None
