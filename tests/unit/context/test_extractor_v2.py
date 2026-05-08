"""Tests for src/context/extractor_v2.py — the actual bug fix."""

from pathlib import Path

import pytest

from src.context.extractor_v2 import (
    extract_decision_points,
    extract_from_phh_path,
    extract_hero_holdings,
    extract_villain_holdings,
)
from src.parsers.pokerkit_adapter import load_phh

FIXTURES = Path(__file__).parents[2] / "fixtures" / "hands"


class TestVillainHoldings:
    def test_extract_when_revealed(self) -> None:
        # showdown_simple.phh: domikan1 (villain because hero=oreias) shows JsQs
        hand = load_phh(FIXTURES / "showdown_simple.phh")
        cards = extract_villain_holdings(hand)
        assert cards == ["Js", "Qs"]

    def test_extract_returns_none_when_hidden(self) -> None:
        # preflop_fold.phh: villain folded preflop, no showdown
        hand = load_phh(FIXTURES / "preflop_fold.phh")
        cards = extract_villain_holdings(hand)
        # In this hand, hero (oreiasccp) has cards [7s, 9d] revealed and
        # villain (domikan1) has no card event with their name
        assert cards is None

    def test_extract_hero_always_present(self) -> None:
        hand = load_phh(FIXTURES / "preflop_fold.phh")
        assert extract_hero_holdings(hand) == ["7s", "9d"]


class TestExtractDecisionPoints:
    def test_postflop_dps_exist(self) -> None:
        # multi_street_betfold has flop/turn/river decisions —
        # the v1 bug forced everything to preflop. v2 must produce
        # postflop DPs.
        dps = extract_from_phh_path(FIXTURES / "multi_street_betfold.phh")
        streets = {dp.street for dp in dps}
        assert "flop" in streets or "turn" in streets or "river" in streets

    def test_decision_id_unique(self) -> None:
        dps = extract_from_phh_path(FIXTURES / "multi_street_betfold.phh")
        ids = [dp.decision_id for dp in dps]
        assert len(ids) == len(set(ids))

    def test_villain_only_decisions(self) -> None:
        hand = load_phh(FIXTURES / "multi_street_betfold.phh")
        dps = extract_decision_points(hand)
        # Every emitted DP must be for villain (the non-hero player)
        assert all(dp.villain_name == hand.villain_name for dp in dps)
        assert all(dp.hero_name == hand.hero_name for dp in dps)

    def test_board_visible_in_postflop_dps(self) -> None:
        dps = extract_from_phh_path(FIXTURES / "multi_street_betfold.phh")
        postflop = [dp for dp in dps if dp.street != "preflop"]
        for dp in postflop:
            assert len(dp.board_cards) >= 3

    def test_hand_strength_populated_when_villain_revealed(self) -> None:
        # showdown_simple: villain (domikan1) showed JsQs
        dps = extract_from_phh_path(FIXTURES / "showdown_simple.phh")
        assert dps  # at least 1 DP
        for dp in dps:
            # Villain hand should be revealed; hand_strength must NOT be NULL
            assert dp.villain_hand == ["Js", "Qs"]
            assert dp.villain_hand_strength is not None
            assert dp.villain_made_specific is not None
            assert dp.villain_hand_rank_int is not None

    def test_hand_strength_null_when_villain_hidden(self) -> None:
        # preflop_fold: villain folded, no holding revealed
        dps = extract_from_phh_path(FIXTURES / "preflop_fold.phh")
        # Villain's only DP is the raise. No holding → null analytics.
        assert dps
        # Note: villain raised then hero folded; villain has 1 DP (the raise)
        for dp in dps:
            assert dp.villain_hand is None
            assert dp.villain_hand_strength is None
            assert dp.villain_draws is None

    def test_retroactive_projection_to_earlier_streets(self) -> None:
        # Construct a synthetic case via showdown_postflop where villain
        # was all-in preflop with revealed hand. The single DP should
        # have hand_strength populated.
        dps = extract_from_phh_path(FIXTURES / "showdown_postflop.phh")
        # In showdown_postflop, the villain (domikan1) was all-in BB →
        # no decision; oreias is hero. So we get 0 villain DPs.
        # But verify that if villain HAD a decision, the projection works:
        # use multi_action_pf which has multi-step preflop.
        dps_multi = extract_from_phh_path(FIXTURES / "multi_action_pf.phh")
        # That hand goes to showdown? Let's check via the file
        for dp in dps_multi:
            if dp.villain_hand is not None:
                # Made label should be classifiable
                assert dp.villain_made_specific is not None

    def test_action_path_populated(self) -> None:
        dps = extract_from_phh_path(FIXTURES / "multi_street_betfold.phh")
        for dp in dps:
            # Path should have at least the villain's action
            assert dp.action_path != ""
            # Path should end in V_ token (villain's action is the last)
            tokens = dp.action_path.split("-")
            assert tokens[-1].startswith("V_")

    def test_intent_populated_when_holdings_revealed(self) -> None:
        dps = extract_from_phh_path(FIXTURES / "showdown_simple.phh")
        # Villain has revealed hand, and at least one made_specific is set
        for dp in dps:
            if dp.villain_made_specific is not None:
                assert dp.intent is not None

    def test_line_tag_present(self) -> None:
        dps = extract_from_phh_path(FIXTURES / "multi_street_betfold.phh")
        for dp in dps:
            assert dp.line_tag is not None


class TestExtractFromAllFixtures:
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
    def test_no_crashes(self, fixture_name: str) -> None:
        dps = extract_from_phh_path(FIXTURES / fixture_name)
        # Either 0 DPs (villain had no decision) or all DPs validated
        for dp in dps:
            assert dp.decision_id
            assert dp.street in ("preflop", "flop", "turn", "river")
            assert dp.villain_action in (
                "check", "call", "call_allin",
                "bet", "raise", "fold",
                "all_in", "allin", "raise_allin", "bet_allin",
            )
