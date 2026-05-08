"""Tests for src/context/line_tagger.py."""

from pathlib import Path

from src.context.line_tagger import identify_preflop_aggressor, tag_line
from src.context.street_detector import detect_streets
from src.parsers.pokerkit_adapter import load_phh

FIXTURES = Path(__file__).parents[2] / "fixtures" / "hands"


def test_identify_preflop_aggressor_betfold() -> None:
    # multi_street_betfold: hero limps (call), villain checks → no raiser
    hand = load_phh(FIXTURES / "multi_street_betfold.phh")
    buckets = detect_streets(hand)
    pf_agg = identify_preflop_aggressor(buckets["preflop"])
    assert pf_agg is None


def test_identify_preflop_aggressor_simple_showdown() -> None:
    # showdown_simple: hero raises 725 → hero is pf aggressor
    hand = load_phh(FIXTURES / "showdown_simple.phh")
    buckets = detect_streets(hand)
    pf_agg = identify_preflop_aggressor(buckets["preflop"])
    assert pf_agg == hand.hero_name  # oreiasccp


def test_probe_tag_after_check() -> None:
    # multi_street_betfold: no preflop raiser.
    #   turn: domikan1 check, oreias bet → bet after check = "probe"
    hand = load_phh(FIXTURES / "multi_street_betfold.phh")
    buckets = detect_streets(hand)
    pf_agg = identify_preflop_aggressor(buckets["preflop"])
    assert pf_agg is None
    turn_bet = next(s for s in buckets["turn"] if s.action == "bet")
    tag = tag_line(turn_bet, street_history=buckets, preflop_aggressor=pf_agg)
    assert tag == "probe"


def test_donk_tag_first_action_no_pf_match() -> None:
    # River first action by non-pf-aggressor with bet → donk
    from src.parsers.pokerkit_adapter import StepSnapshot
    snap = StepSnapshot(
        step_idx=0, street="river", street_pokerkit="river",
        actor_index=0, actor_name="defender",
        action="bet", amount=100.0, pot_before=200,
        stacks_before=(800, 800),
        board=("Kh", "9d", "4c", "Ts", "2d"),
    )
    history = {"preflop": [], "flop": [], "turn": [], "river": [snap]}
    tag = tag_line(snap, street_history=history, preflop_aggressor="aggressor")
    assert tag == "donk"


def test_check_raise_tag() -> None:
    # We need a hand with check, then bet, then raise on the same street.
    # None of our fixtures have that explicitly, so build a synthetic
    # snap list to test the function.
    from src.parsers.pokerkit_adapter import StepSnapshot

    snap_check = StepSnapshot(
        step_idx=0, street="flop", street_pokerkit="flop",
        actor_index=0, actor_name="A",
        action="check", amount=0.0, pot_before=100,
        stacks_before=(1000, 1000), board=("Kh", "9d", "4c"),
    )
    snap_bet = StepSnapshot(
        step_idx=1, street="flop", street_pokerkit="flop",
        actor_index=1, actor_name="B",
        action="bet", amount=50.0, pot_before=100,
        stacks_before=(1000, 950), board=("Kh", "9d", "4c"),
    )
    snap_xr = StepSnapshot(
        step_idx=2, street="flop", street_pokerkit="flop",
        actor_index=0, actor_name="A",
        action="raise", amount=200.0, pot_before=150,
        stacks_before=(950, 950), board=("Kh", "9d", "4c"),
    )
    history = {"preflop": [], "flop": [snap_check, snap_bet, snap_xr], "turn": [], "river": []}
    tag = tag_line(snap_xr, street_history=history, preflop_aggressor="B")
    assert tag == "xr"


def test_cbet_tag() -> None:
    # PF aggressor opens; postflop they bet first → cbet
    from src.parsers.pokerkit_adapter import StepSnapshot
    snap_cbet = StepSnapshot(
        step_idx=0, street="flop", street_pokerkit="flop",
        actor_index=0, actor_name="A",
        action="bet", amount=50.0, pot_before=100,
        stacks_before=(950, 950), board=("Kh", "9d", "4c"),
    )
    history = {"preflop": [], "flop": [snap_cbet], "turn": [], "river": []}
    tag = tag_line(snap_cbet, street_history=history, preflop_aggressor="A")
    assert tag == "cbet"


def test_second_barrel_tag() -> None:
    from src.parsers.pokerkit_adapter import StepSnapshot
    flop_cbet = StepSnapshot(
        step_idx=0, street="flop", street_pokerkit="flop",
        actor_index=0, actor_name="A",
        action="bet", amount=50.0, pot_before=100,
        stacks_before=(950, 950), board=("Kh", "9d", "4c"),
    )
    flop_call = StepSnapshot(
        step_idx=1, street="flop", street_pokerkit="flop",
        actor_index=1, actor_name="B",
        action="call", amount=50.0, pot_before=150,
        stacks_before=(950, 950), board=("Kh", "9d", "4c"),
    )
    turn_bet = StepSnapshot(
        step_idx=2, street="turn", street_pokerkit="turn",
        actor_index=0, actor_name="A",
        action="bet", amount=120.0, pot_before=200,
        stacks_before=(900, 900), board=("Kh", "9d", "4c", "Ts"),
    )
    history = {
        "preflop": [],
        "flop": [flop_cbet, flop_call],
        "turn": [turn_bet],
        "river": [],
    }
    tag = tag_line(turn_bet, street_history=history, preflop_aggressor="A")
    assert tag == "second_barrel"
