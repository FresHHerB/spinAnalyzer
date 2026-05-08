"""Tests for src/hand_eval/evaluator.py."""

import pytest

from src.hand_eval.evaluator import HandRank, evaluate_hand


class TestEvaluateHand:
    def test_top_pair_top_kicker(self) -> None:
        rank = evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c"])
        assert rank.category == "ONE_PAIR"

    def test_overpair_aa(self) -> None:
        rank = evaluate_hand(["Ah", "Ad"], ["Kh", "9d", "4c"])
        assert rank.category == "ONE_PAIR"
        assert rank.rank_int > evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c"]).rank_int

    def test_top_set_beats_top_pair(self) -> None:
        top_set = evaluate_hand(["Kh", "Kc"], ["Kd", "9d", "4c"])
        top_pair = evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c"])
        assert top_set.category == "THREE_OF_A_KIND"
        assert top_set > top_pair

    def test_full_house(self) -> None:
        rank = evaluate_hand(["Ah", "Kd"], ["As", "Ks", "Ad"])
        assert rank.category == "FULL_HOUSE"

    def test_royal_flush(self) -> None:
        rank = evaluate_hand(["Ah", "Kh"], ["Qh", "Jh", "Th"])
        assert rank.category == "STRAIGHT_FLUSH"

    def test_high_card(self) -> None:
        rank = evaluate_hand(["8h", "7c"], ["Kh", "9d", "4c"])
        assert rank.category == "HIGH_CARD"

    def test_river_eval(self) -> None:
        # 5-card board, full info
        rank = evaluate_hand(["Ah", "Kh"], ["Qh", "Jh", "Th", "2c", "3d"])
        assert rank.category == "STRAIGHT_FLUSH"

    @pytest.mark.parametrize(
        "hole,board",
        [
            (["Ah", "Kc"], []),
            (["Ah", "Ad"], []),
            (["7d", "2c"], []),
            (["Ts", "9s"], []),
        ],
    )
    def test_preflop_returns_synthetic_rank(self, hole, board) -> None:
        # Preflop returns a non-null rank without crashing
        rank = evaluate_hand(hole, board)
        assert isinstance(rank, HandRank)
        assert rank.rank_int > 0

    def test_preflop_pair_outranks_high_card(self) -> None:
        pair = evaluate_hand(["7d", "7c"], [])
        high = evaluate_hand(["Ah", "Kc"], [])
        assert pair > high

    def test_preflop_aa_outranks_22(self) -> None:
        aa = evaluate_hand(["Ah", "Ad"], [])
        twos = evaluate_hand(["2h", "2d"], [])
        assert aa > twos

    def test_invalid_hole_size_raises(self) -> None:
        with pytest.raises(ValueError):
            evaluate_hand(["Ah"], ["Kh", "9d", "4c"])

    def test_invalid_board_size_raises(self) -> None:
        with pytest.raises(ValueError):
            evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c", "2c", "3d", "4d"])


class TestHandRankComparison:
    def test_equal_ranks_compare_equal(self) -> None:
        a = evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c"])
        b = evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c"])
        assert a.rank_int == b.rank_int
        assert not (a < b)
        assert a <= b

    def test_strict_ordering(self) -> None:
        # Quads > full house > flush > straight > set > 2pair > pair
        quads = evaluate_hand(["7h", "7c"], ["7s", "7d", "Kh"])
        boat = evaluate_hand(["Ah", "Ad"], ["Ac", "Kh", "Kd"])
        flush = evaluate_hand(["Ah", "Kh"], ["Qh", "9h", "2h"])
        straight = evaluate_hand(["8h", "9c"], ["Tc", "Jd", "Qs"])
        trips = evaluate_hand(["Kh", "Kc"], ["Kd", "9h", "2c"])
        two_pair = evaluate_hand(["Ah", "Kc"], ["Ad", "Kd", "2c"])
        pair = evaluate_hand(["Ah", "Kc"], ["Kh", "9d", "4c"])
        assert quads > boat > flush > straight > trips > two_pair > pair
