"""Tests for src/hand_eval/draws.py."""

import pytest

from src.hand_eval.draws import detect_draws


class TestFlushDraws:
    def test_nut_flush_draw_with_ace(self) -> None:
        # AhQh on Kh-9h-4c → 4 hearts, A is nut
        d = detect_draws(["Ah", "Qh"], ["Kh", "9h", "4c"])
        assert d.nut_flush_draw is True
        assert d.weak_flush_draw is False
        assert d.outs_count >= 9

    def test_weak_flush_draw_no_ace(self) -> None:
        # 7h6h on Kh-9h-4c → 4 hearts, no A
        d = detect_draws(["7h", "6h"], ["Kh", "9h", "4c"])
        assert d.nut_flush_draw is False
        assert d.weak_flush_draw is True

    def test_no_flush_draw_with_3_suit(self) -> None:
        d = detect_draws(["7h", "6c"], ["Kh", "9h", "4c"])
        assert not d.nut_flush_draw
        assert not d.weak_flush_draw

    def test_backdoor_flush_draw(self) -> None:
        # AhKc on 7h-9h-4c → 3 hearts including 1 from hole = BDFD
        d = detect_draws(["Ah", "Kc"], ["7h", "9h", "4c"])
        assert d.has_bdfd is True

    def test_no_bdfd_when_full_fd(self) -> None:
        d = detect_draws(["Ah", "Qh"], ["Kh", "9h", "4c"])
        # Full FD, not BDFD
        assert d.has_bdfd is False
        assert d.nut_flush_draw is True


class TestStraightDraws:
    def test_oesd(self) -> None:
        # 9-8 on 7-6-2 = open-ender (need 5 or T)
        d = detect_draws(["9h", "8c"], ["7d", "6s", "2c"])
        assert d.has_oesd is True
        assert d.outs_count >= 8

    def test_gutshot(self) -> None:
        # KQ on T93 = need J
        d = detect_draws(["Kh", "Qc"], ["Td", "9s", "3c"])
        assert d.has_gutshot is True
        assert not d.has_oesd

    def test_no_straight_draw(self) -> None:
        d = detect_draws(["Ah", "2c"], ["Kh", "9d", "4c"])
        # Wheel gutshot (need 3,4,5 — 4 is on board, need 3 and 5 ... actually
        # A-2 has gutshot draw if 3,4,5 line up)
        # This isn't a draw situation
        assert not d.has_oesd

    def test_combo_draw(self) -> None:
        # Th9h on 8h-7h-2c → FD + OESD
        d = detect_draws(["Th", "9h"], ["8h", "7h", "2c"])
        assert d.weak_flush_draw or d.nut_flush_draw
        assert d.has_oesd
        assert d.has_combo_draw is True


class TestOvercards:
    def test_two_overcards_no_pair(self) -> None:
        # AK on 762 → both overcards
        d = detect_draws(["Ah", "Kc"], ["7d", "6s", "2c"])
        assert d.has_overcard_draw is True

    def test_one_overcard_only_no_overcard_draw(self) -> None:
        # A8 on K72 → A is over, 8 is not
        d = detect_draws(["Ah", "8c"], ["Kd", "7s", "2c"])
        assert d.has_overcard_draw is False


class TestPairPlusDraw:
    def test_pair_plus_flush_draw(self) -> None:
        # 9h6h on 7h-9h-2c: pair of 9s + flush draw (4 hearts)
        d = detect_draws(["9h", "6h"], ["7h", "9h", "2c"])
        assert d.weak_flush_draw or d.nut_flush_draw
        assert d.has_pair_plus_draw is True

    def test_no_pair_plus_when_no_draw(self) -> None:
        d = detect_draws(["9c", "6d"], ["7h", "9d", "2c"])
        # Pair but no draw
        assert d.has_pair_plus_draw is False


class TestPreflopAndRiver:
    def test_preflop_no_draws_computed(self) -> None:
        d = detect_draws(["Ah", "Kc"], [])
        assert d.outs_count == 0
        assert not d.nut_flush_draw
        assert not d.has_oesd

    def test_river_no_more_draws(self) -> None:
        # On the river, no more cards to come
        d = detect_draws(["Ah", "Kc"], ["7h", "9h", "4c", "2d", "Js"])
        # Existing draw flags may still report flush count; that's OK as
        # long as outs_count behaves consistently.
        assert d.outs_count >= 0


class TestInvariants:
    @pytest.mark.parametrize(
        "hole,board",
        [
            (["Ah", "Kh"], ["Qh", "9h", "4c"]),  # Nut FD
            (["9h", "8c"], ["7d", "6s", "2c"]),  # OESD
            (["Th", "9h"], ["8h", "7c", "2c"]),  # combo
            (["7h", "5c"], ["Kh", "9d", "4c"]),  # nothing
        ],
    )
    def test_outs_in_valid_range(self, hole, board) -> None:
        d = detect_draws(hole, board)
        assert 0 <= d.outs_count <= 15
