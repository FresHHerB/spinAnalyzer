"""Tests for src/intent/classifier.py."""

import pytest

from src.hand_eval.draws import Draws
from src.intent.classifier import classify_intent


def _no_draws() -> Draws:
    return Draws(
        nut_flush_draw=False,
        weak_flush_draw=False,
        has_oesd=False,
        has_double_gutshot=False,
        has_gutshot=False,
        has_combo_draw=False,
        has_bdfd=False,
        has_bdsd=False,
        has_overcard_draw=False,
        has_pair_plus_draw=False,
        outs_count=0,
    )


def _flush_draw() -> Draws:
    return Draws(
        nut_flush_draw=True,
        weak_flush_draw=False,
        has_oesd=False,
        has_double_gutshot=False,
        has_gutshot=False,
        has_combo_draw=False,
        has_bdfd=False,
        has_bdsd=False,
        has_overcard_draw=False,
        has_pair_plus_draw=False,
        outs_count=9,
    )


class TestValueIntents:
    def test_value_pure_big_bet_top_set(self) -> None:
        intent = classify_intent(
            action="bet", made_label="top_set", draws=_no_draws(),
            bet_size_pot_pct=75.0,
        )
        assert intent == "value_pure"

    def test_thin_value_small_bet_top_pair(self) -> None:
        intent = classify_intent(
            action="bet", made_label="TPGK", draws=_no_draws(),
            bet_size_pot_pct=33.0,
        )
        assert intent == "thin_value"

    def test_value_pure_overpair_call(self) -> None:
        intent = classify_intent(
            action="call", made_label="overpair", draws=_no_draws(),
            bet_size_pot_pct=None,
        )
        assert intent == "value_pure"


class TestBluffIntents:
    def test_bluff_pure_air_overbet(self) -> None:
        intent = classify_intent(
            action="bet", made_label="ace_high", draws=_no_draws(),
            bet_size_pot_pct=125.0,
        )
        assert intent == "bluff_pure"

    def test_bluff_pure_high_card(self) -> None:
        intent = classify_intent(
            action="raise", made_label="high_card", draws=_no_draws(),
            bet_size_pot_pct=80.0,
        )
        assert intent == "bluff_pure"

    def test_semi_bluff_bet_with_FD(self) -> None:
        intent = classify_intent(
            action="bet", made_label="ace_high", draws=_flush_draw(),
            bet_size_pot_pct=66.0,
        )
        assert intent == "semi_bluff"


class TestBluffCatcher:
    def test_bluff_catcher_calling_weak_made(self) -> None:
        intent = classify_intent(
            action="call", made_label="TPWK", draws=_no_draws(),
            bet_size_pot_pct=None,
        )
        assert intent == "bluff_catcher"


class TestPotControl:
    def test_pot_control_check_medium(self) -> None:
        intent = classify_intent(
            action="check", made_label="second_pair", draws=_no_draws(),
            bet_size_pot_pct=None,
        )
        assert intent == "pot_control"


class TestGiveUp:
    def test_give_up_fold_with_draw(self) -> None:
        intent = classify_intent(
            action="fold", made_label="ace_high", draws=_flush_draw(),
            bet_size_pot_pct=None,
        )
        assert intent == "give_up"


@pytest.mark.parametrize(
    "action,made_label,has_draw,bet_pct,expected",
    [
        ("bet", "boat", False, 80.0, "value_pure"),
        ("raise", "nut_flush", False, 100.0, "value_pure"),
        ("call", "top_set", False, None, "value_pure"),
        ("bet", "second_pair", False, 33.0, "thin_value"),
        ("bet", "high_card", True, 75.0, "semi_bluff"),
        ("check", "TPWK", False, None, "pot_control"),
        ("fold", "TPWK", False, None, "give_up"),
        ("call", "second_pair", False, None, "bluff_catcher"),
    ],
)
def test_intent_table(
    action: str, made_label: str, has_draw: bool,
    bet_pct: float | None, expected: str,
) -> None:
    draws = _flush_draw() if has_draw else _no_draws()
    intent = classify_intent(
        action=action, made_label=made_label, draws=draws,
        bet_size_pot_pct=bet_pct,
    )
    assert intent == expected
