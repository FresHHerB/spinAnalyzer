"""Tests for src/parsers/pokerkit_adapter.py against real PHH fixtures."""

from pathlib import Path

import pytest

from src.parsers.pokerkit_adapter import (
    PHHHand,
    create_state,
    load_phh,
    replay_to_list,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "hands"


@pytest.fixture
def preflop_fold_hand() -> PHHHand:
    return load_phh(FIXTURES / "preflop_fold.phh")


@pytest.fixture
def multi_street_betfold_hand() -> PHHHand:
    return load_phh(FIXTURES / "multi_street_betfold.phh")


@pytest.fixture
def showdown_simple_hand() -> PHHHand:
    return load_phh(FIXTURES / "showdown_simple.phh")


@pytest.fixture
def showdown_postflop_hand() -> PHHHand:
    return load_phh(FIXTURES / "showdown_postflop.phh")


class TestLoadPHH:
    def test_metadata_extracted(self, multi_street_betfold_hand: PHHHand) -> None:
        h = multi_street_betfold_hand
        assert h.hand_id == "11514545395"
        assert h.sb == 20
        assert h.bb == 40
        assert h.ante == 5
        assert h.hero_name == "oreiasccp"

    def test_btn_and_bb_identified(self, multi_street_betfold_hand: PHHHand) -> None:
        # In this fixture: oreiasccp has is_btn=true, domikan1 is BB
        h = multi_street_betfold_hand
        assert h.btn_player_name == "oreiasccp"
        assert h.bb_player_name == "domikan1"
        # Plan invariant: villain == non-hero
        assert h.villain_name == "domikan1"

    def test_player_to_pokerkit_index(self, multi_street_betfold_hand: PHHHand) -> None:
        h = multi_street_betfold_hand
        assert h.player_to_pokerkit_index(h.bb_player_name) == 0
        assert h.player_to_pokerkit_index(h.btn_player_name) == 1
        with pytest.raises(ValueError):
            h.player_to_pokerkit_index("ghost")


class TestCreateState:
    def test_blinds_and_antes_posted(self, multi_street_betfold_hand: PHHHand) -> None:
        h = multi_street_betfold_hand
        state = create_state(h)
        # Pot = 2 antes + sb + bb = 5+5+20+40 = 70
        assert state.total_pot_amount == 70
        # idx 0 = BB player (domikan1, original stack 595): 595 - 5 ante - 40 BB = 550
        # idx 1 = BTN/SB (oreiasccp, 905): 905 - 5 - 20 = 880
        assert state.stacks[0] == 550
        assert state.stacks[1] == 880


class TestReplay:
    def test_preflop_fold_hand(self, preflop_fold_hand: PHHHand) -> None:
        # Preflop only: domikan1 raise all-in, oreiasccp fold
        snaps = replay_to_list(preflop_fold_hand)
        assert len(snaps) == 2
        assert snaps[0].action == "raise"
        assert snaps[0].actor_name == "domikan1"
        assert snaps[0].street == "preflop"
        assert snaps[0].board == ()
        assert snaps[1].action == "fold"
        assert snaps[1].actor_name == "oreiasccp"

    def test_multi_street_betfold(self, multi_street_betfold_hand: PHHHand) -> None:
        snaps = replay_to_list(multi_street_betfold_hand)
        # Action sequence in this PHH:
        #   preflop: oreiasccp call 20, domikan1 check
        #   flop: domikan1 check, oreiasccp check
        #   turn: domikan1 check, oreiasccp bet 40, domikan1 call 40
        #   river: domikan1 bet 212, oreiasccp fold
        actions = [s.action for s in snaps]
        assert actions == [
            "call", "check",                # preflop
            "check", "check",               # flop
            "check", "bet", "call",         # turn
            "bet", "fold",                  # river
        ]
        # Streets must reflect native PHH tags
        streets = [s.street for s in snaps]
        assert streets == [
            "preflop", "preflop",
            "flop", "flop",
            "turn", "turn", "turn",
            "river", "river",
        ]

    def test_board_visible_at_each_step(
        self, multi_street_betfold_hand: PHHHand
    ) -> None:
        snaps = replay_to_list(multi_street_betfold_hand)
        # Preflop snapshots: empty board
        preflop = [s for s in snaps if s.street == "preflop"]
        assert all(s.board == () for s in preflop)
        # Flop snapshots: 3-card board
        flop = [s for s in snaps if s.street == "flop"]
        assert all(len(s.board) == 3 for s in flop)
        # Turn: 4 cards
        turn = [s for s in snaps if s.street == "turn"]
        assert all(len(s.board) == 4 for s in turn)
        # River: 5 cards
        river = [s for s in snaps if s.street == "river"]
        assert all(len(s.board) == 5 for s in river)

    def test_pot_grows_monotonically_within_street(
        self, multi_street_betfold_hand: PHHHand
    ) -> None:
        snaps = replay_to_list(multi_street_betfold_hand)
        # Within a single street, pot_before is non-decreasing (modulo
        # bet collection at street boundaries which clears bets to pot)
        for i in range(1, len(snaps)):
            if snaps[i].street == snaps[i - 1].street:
                assert snaps[i].pot_before >= snaps[i - 1].pot_before

    def test_streets_match_native(self, multi_street_betfold_hand: PHHHand) -> None:
        snaps = replay_to_list(multi_street_betfold_hand)
        # pokerkit's reported street matches PHH native tag
        for s in snaps:
            assert s.street == s.street_pokerkit, (
                f"step {s.step_idx}: native={s.street}, pokerkit={s.street_pokerkit}"
            )

    def test_showdown_postflop_no_postflop_actions(
        self, showdown_postflop_hand: PHHHand
    ) -> None:
        # In this hand, BB is all-in from the BB post (stack 40 < BB 35 +
        # ante 5 leaves only 0 effective). After hero limps, runout ensues
        # with no postflop decision points.
        snaps = replay_to_list(showdown_postflop_hand)
        actions = [s.action for s in snaps]
        # Only preflop call from oreiasccp
        assert actions == ["call"]
        assert snaps[0].street == "preflop"

    def test_showdown_simple(self, showdown_simple_hand: PHHHand) -> None:
        # All-in preflop battle.
        snaps = replay_to_list(showdown_simple_hand)
        actions = [s.action for s in snaps]
        # PHH: domikan1 call 20, oreiasccp raise 725, domikan1 call 685
        assert actions == ["call", "raise", "call"]
        # All preflop
        assert all(s.street == "preflop" for s in snaps)


class TestReplayInvariants:
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
    def test_replay_all_fixtures_without_error(self, fixture_name: str) -> None:
        hand = load_phh(FIXTURES / fixture_name)
        snaps = replay_to_list(hand)
        # Step indices are contiguous from 0
        assert [s.step_idx for s in snaps] == list(range(len(snaps)))
        # Board cards are in canonical 2-char format
        for s in snaps:
            for card in s.board:
                assert len(card) == 2

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
    def test_actor_alternates_correctly(self, fixture_name: str) -> None:
        hand = load_phh(FIXTURES / fixture_name)
        snaps = replay_to_list(hand)
        # Within a street, actors alternate (HU)
        for i in range(1, len(snaps)):
            if snaps[i].street == snaps[i - 1].street:
                if snaps[i - 1].action != "fold":
                    assert snaps[i].actor_name != snaps[i - 1].actor_name
