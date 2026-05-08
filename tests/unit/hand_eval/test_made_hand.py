"""Tests for src/hand_eval/made_hand.py."""

import pytest

from src.hand_eval.made_hand import classify_made


@pytest.mark.parametrize(
    "hole,board,expected",
    [
        # Top pair variants
        (["Ah", "Kc"], ["Kh", "9d", "4c"], "TPTK"),
        (["Qh", "Kc"], ["Kh", "9d", "4c"], "TPGK"),
        (["8h", "Kc"], ["Kh", "9d", "4c"], "TPWK"),
        # Pocket pairs
        (["Ah", "Ad"], ["Kh", "9d", "4c"], "overpair"),
        (["7h", "7d"], ["Kh", "9d", "4c"], "pocket_pair_under_board"),
        # Sets
        (["Kh", "Kc"], ["Kd", "9d", "4c"], "top_set"),
        (["9h", "9d"], ["Kh", "9c", "4c"], "mid_set"),
        (["4h", "4d"], ["Kh", "9d", "4c"], "bottom_set"),
        # Two pair
        (["Ah", "Kc"], ["Ad", "Kd", "2c"], "two_pair_top_top"),
        # Quads / boat
        (["7h", "7c"], ["7s", "7d", "Kh"], "quads"),
        (["Ah", "Ad"], ["Ac", "Kh", "Kd"], "boat"),
        # Flush
        (["Ah", "Qh"], ["Kh", "9h", "2h"], "nut_flush"),
        (["Kh", "Th"], ["7h", "5h", "2h"], "second_nut_flush"),
        (["7h", "5h"], ["3h", "8h", "2h"], "weak_flush"),
        # Straights
        (["Ah", "Tc"], ["Jh", "Qd", "Kc"], "nut_straight"),
        (["8h", "9c"], ["Tc", "Jd", "Qs"], "weak_straight"),
        # Straight flush
        (["Ah", "Kh"], ["Qh", "Jh", "Th"], "nut_straight_flush"),
        # Second/third pair
        (["9h", "Kc"], ["Ah", "9d", "4c"], "second_pair"),
        # High card
        (["8h", "7c"], ["Kh", "9d", "4c"], "high_card"),
        (["8h", "Ac"], ["Kh", "9d", "4c"], "ace_high"),
    ],
)
def test_classify_made_canonical_cases(
    hole: list[str], board: list[str], expected: str
) -> None:
    actual = classify_made(hole, board)
    assert actual == expected, f"hole={hole} board={board}: got {actual!r}, expected {expected!r}"


def test_preflop_pocket_pair() -> None:
    assert classify_made(["7h", "7d"], []) == "pocket_pair"


def test_preflop_high_card() -> None:
    assert classify_made(["Ah", "Kc"], []) == "high_card"
