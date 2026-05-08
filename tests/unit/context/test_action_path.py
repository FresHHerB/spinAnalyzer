"""Tests for src/context/action_path.py canonicalizer."""

from pathlib import Path

import pytest

from src.context.action_path import canonicalize_path
from src.context.street_detector import detect_streets
from src.parsers.pokerkit_adapter import load_phh

FIXTURES = Path(__file__).parents[2] / "fixtures" / "hands"


class TestCanonicalize:
    def test_empty_path(self) -> None:
        assert canonicalize_path([], hero_name="hero", bb=40, street="preflop") == ""

    def test_preflop_fold_hand(self) -> None:
        # PHH: domikan1 raise 545 (BTN/SB), oreiasccp fold
        # bb=40, hero=oreiasccp, villain=domikan1
        # raise to 545 = ~14bb
        hand = load_phh(FIXTURES / "preflop_fold.phh")
        snaps_by_street = detect_streets(hand)
        path = canonicalize_path(
            snaps_by_street["preflop"],
            hero_name=hand.hero_name,
            bb=hand.bb,
            street="preflop",
        )
        assert path == "V_R14-H_F"

    def test_multi_street_betfold(self) -> None:
        hand = load_phh(FIXTURES / "multi_street_betfold.phh")
        # bb=40, hero=oreiasccp (BTN), villain=domikan1 (BB)
        # preflop: oreiasccp call 20, domikan1 check
        # flop: domikan1 check, oreiasccp check
        # turn: domikan1 check, oreiasccp bet 40, domikan1 call
        # river: domikan1 bet 212, oreiasccp fold
        buckets = detect_streets(hand)

        pf = canonicalize_path(buckets["preflop"], hero_name=hand.hero_name, bb=hand.bb, street="preflop")
        assert pf == "H_C-V_X"

        flop = canonicalize_path(buckets["flop"], hero_name=hand.hero_name, bb=hand.bb, street="flop")
        assert flop == "V_X-H_X"

        # Turn: pot at start = 90 (10 antes + 40 SB-call + 40 BB-check).
        # domikan1 checks. Then oreiasccp bets 40 into pot 90 = 44%.
        turn = canonicalize_path(buckets["turn"], hero_name=hand.hero_name, bb=hand.bb, street="turn")
        assert turn == "V_X-H_B44-V_C"

        # River: pot 170 (after turn 90+40+40). domikan1 bets 212 / 170 = 125%
        river = canonicalize_path(buckets["river"], hero_name=hand.hero_name, bb=hand.bb, street="river")
        assert river == "V_B125-H_F"

    @pytest.mark.parametrize(
        "fixture_name,street",
        [
            ("preflop_fold.phh", "preflop"),
            ("multi_street_betfold.phh", "preflop"),
            ("multi_street_betfold.phh", "flop"),
            ("multi_street_betfold.phh", "turn"),
            ("multi_street_betfold.phh", "river"),
            ("showdown_simple.phh", "preflop"),
        ],
    )
    def test_determinism(self, fixture_name: str, street: str) -> None:
        # Same input → same output across calls.
        hand = load_phh(FIXTURES / fixture_name)
        buckets = detect_streets(hand)
        snaps = buckets[street]
        p1 = canonicalize_path(snaps, hero_name=hand.hero_name, bb=hand.bb, street=street)
        p2 = canonicalize_path(snaps, hero_name=hand.hero_name, bb=hand.bb, street=street)
        assert p1 == p2

    def test_actor_token_distinguishes_hero_villain(self) -> None:
        # Two hands from same fixture pool, same action structure; if
        # hero_name differs, the H/V tokens swap.
        hand = load_phh(FIXTURES / "multi_street_betfold.phh")
        buckets = detect_streets(hand)
        # As-is (hero=oreiasccp): preflop = "H_C-V_X"
        as_hero = canonicalize_path(
            buckets["preflop"], hero_name="oreiasccp", bb=40, street="preflop"
        )
        as_villain = canonicalize_path(
            buckets["preflop"], hero_name="domikan1", bb=40, street="preflop"
        )
        assert as_hero == "H_C-V_X"
        assert as_villain == "V_C-H_X"
