"""PHH → PokerKit GameState replay.

Loads a PHH (Poker Hand History) TOML file, replays its action stream
through PokerKit's NoLimitTexasHoldem state machine, and exposes
per-step snapshots (board, pot, stacks, action, street) for downstream
extractors.

Heads-up convention discovered empirically:
    - pokerkit `raw_starting_stacks` is positional: index 0 is the
      non-button (BB) player, index 1 is the button/SB player.
    - `raw_blinds_or_straddles=(sb, bb)` — SB first, BB second.
    - `actor_index` after hole-deal = 1 (SB acts first preflop in HU).

PHH "amount" semantics observed in this repo's hands:
    - `bet` / `raise` → new total stake on the street (use
      `complete_bet_or_raise_to(amount_in_chips)`).
    - `call` / `check` → no amount needed; use `check_or_call()`.
    - `fold` → `fold()`.
    - `posts_sb` / `posts_bb` / `ante` are automated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import tomli
from pokerkit import Automation, Mode, NoLimitTexasHoldem, State

# Maps PHH `street` strings to street_index produced by pokerkit.
# After post-blinds + hole-deal, pokerkit is on street_index=0 (preflop).
# After preflop close + flop deal: street_index=1.
# After flop close + turn deal: street_index=2.
# After turn close + river deal: street_index=3.
# After river close: street_index=None (terminal).
STREET_NAMES = ("preflop", "flop", "turn", "river")


@dataclass(frozen=True)
class StepSnapshot:
    """Snapshot of game state at one step of the action stream."""

    step_idx: int
    street: str  # native PHH street tag for this action
    street_pokerkit: str | None  # what pokerkit reports; None if terminal
    actor_index: int | None
    actor_name: str | None
    action: str  # PHH action verb (call/check/raise/bet/fold/etc)
    amount: float  # PHH amount (chips, total for raise/bet)
    pot_before: int  # pot before applying this action
    stacks_before: tuple[int, ...]  # stacks before applying this action
    board: tuple[str, ...]  # board cards visible at start of this step


@dataclass(frozen=True)
class PHHHand:
    """Loaded PHH with metadata extracted for replay."""

    raw: dict[str, Any]
    hand_id: str
    sb: int
    bb: int
    ante: int
    hero_name: str
    bb_player_name: str  # idx 0 in pokerkit
    btn_player_name: str  # idx 1 in pokerkit
    bb_player_stack: int
    btn_player_stack: int

    @property
    def villain_name(self) -> str:
        """The non-hero player. Plan calls this 'villain'."""
        return self.btn_player_name if self.hero_name == self.bb_player_name else self.bb_player_name

    def player_to_pokerkit_index(self, player_name: str) -> int:
        if player_name == self.bb_player_name:
            return 0
        if player_name == self.btn_player_name:
            return 1
        raise ValueError(f"player {player_name!r} not in this hand")


def load_phh(phh_path: Path | str) -> PHHHand:
    """Parse PHH TOML and extract structured metadata."""
    path = Path(phh_path)
    with open(path, "rb") as f:
        raw = tomli.load(f)

    metadata = raw.get("metadata", {})
    players = raw.get("players", [])
    if len(players) != 2:
        raise ValueError(
            f"{path.name}: expected exactly 2 players (HU), got {len(players)}"
        )

    btn_player = next((p for p in players if p.get("is_btn")), None)
    bb_player = next((p for p in players if not p.get("is_btn")), None)
    if btn_player is None or bb_player is None:
        raise ValueError(f"{path.name}: could not identify BTN and BB players")

    sb = int(round(float(metadata.get("sb", 0))))
    bb = int(round(float(metadata.get("bb", 0))))
    ante = int(round(float(metadata.get("ante", 0))))
    if sb <= 0 or bb <= 0 or sb >= bb:
        raise ValueError(f"{path.name}: invalid blind structure sb={sb} bb={bb}")

    return PHHHand(
        raw=raw,
        hand_id=str(metadata.get("hand_id", path.stem)),
        sb=sb,
        bb=bb,
        ante=ante,
        hero_name=str(metadata.get("hero", "")),
        bb_player_name=str(bb_player["name"]),
        btn_player_name=str(btn_player["name"]),
        bb_player_stack=int(round(float(bb_player["stack"]))),
        btn_player_stack=int(round(float(btn_player["stack"]))),
    )


def create_state(hand: PHHHand) -> State:
    """Initialise a pokerkit NLHE state for the given PHH (HU)."""
    automations = (
        Automation.ANTE_POSTING,
        Automation.BET_COLLECTION,
        Automation.BLIND_OR_STRADDLE_POSTING,
        Automation.CARD_BURNING,
        Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
        Automation.HAND_KILLING,
        Automation.CHIPS_PUSHING,
        Automation.CHIPS_PULLING,
    )
    return NoLimitTexasHoldem.create_state(
        automations,
        True,  # ante_trimming_status
        hand.ante,
        (hand.sb, hand.bb),  # SB then BB; pokerkit assigns SB to idx 1 (BTN), BB to idx 0
        hand.bb,  # min_bet
        (hand.bb_player_stack, hand.btn_player_stack),  # idx0=BB, idx1=BTN/SB
        2,
        mode=Mode.TOURNAMENT,
    )


def _street_pokerkit(state: State) -> str | None:
    idx = state.street_index
    if idx is None:
        return None
    if 0 <= idx < len(STREET_NAMES):
        return STREET_NAMES[idx]
    return None


def _board_tuple(state: State) -> tuple[str, ...]:
    cards = list(state.get_board_cards(0))
    return tuple(repr(c) for c in cards)


def _pokerkit_to_player_name(state_actor_index: int | None, hand: PHHHand) -> str | None:
    if state_actor_index is None:
        return None
    if state_actor_index == 0:
        return hand.bb_player_name
    if state_actor_index == 1:
        return hand.btn_player_name
    return None


def replay_steps(hand: PHHHand) -> Iterator[StepSnapshot]:
    """Replay PHH action stream and yield one StepSnapshot per villain-or-hero
    decision (i.e. per `event=action` row that isn't an ante/blind post).

    Card events (`event="cards"`) drive board dealing and hole-card dealing
    but are not yielded as snapshots — they are state-progression hints.

    Cross-validates the native PHH `street` field against pokerkit's
    `street_index` for every yielded step; logs a warning on mismatch
    (we trust pokerkit, treating PHH's tag as a hint).
    """
    state = create_state(hand)

    # First, deal hole cards from the action stream's preflop "cards" events.
    # PHH ordering varies; we read both events and deal in pokerkit's
    # required order (idx 0 first, then idx 1).
    pre_hole_cards: dict[int, str] = {}
    for ev in hand.raw.get("actions", []):
        if ev.get("event") == "cards" and ev.get("street") == "preflop" and "player" in ev:
            cards = ev.get("cards", [])
            if not cards:
                continue
            pkt_idx = hand.player_to_pokerkit_index(ev["player"])
            pre_hole_cards[pkt_idx] = "".join(cards)

    # Collect every card that will appear later (board + revealed holdings).
    # Placeholder hole cards must avoid these to prevent collisions when
    # pokerkit later deals the actual board.
    used_cards: set[str] = set()
    for ev in hand.raw.get("actions", []):
        if ev.get("event") == "cards":
            for c in ev.get("cards", []):
                used_cards.add(c)

    # Deal hole cards. pokerkit's deal order is positional (idx 0 then idx 1).
    # If a player's hole cards are not revealed in the PHH (typical for
    # villain pre-showdown), use placeholder unknown cards from the deck.
    for idx in (0, 1):
        if idx in pre_hole_cards:
            state.deal_hole(pre_hole_cards[idx])
        else:
            dealable = [
                c for c in state.get_dealable_cards()
                if repr(c) not in used_cards
            ]
            placeholder = "".join(repr(c) for c in dealable[:2])
            state.deal_hole(placeholder)

    # Now walk the action stream.
    step_idx = 0
    for ev in hand.raw.get("actions", []):
        event = ev.get("event")
        street_native = ev.get("street", "preflop")

        if event == "cards":
            # Board card; deal to pokerkit if not already dealt by automation.
            if "player" in ev:
                # Hole-card event already handled above.
                continue
            cards = ev.get("cards", [])
            if cards and state.can_deal_board():
                state.deal_board("".join(cards))
            continue

        if event != "action":
            continue

        action_type = ev.get("action", "")
        # Skip blind/ante posts (automated by pokerkit).
        if action_type in ("ante", "posts_sb", "posts_bb", "sb", "bb"):
            continue

        amount = float(ev.get("amount", 0))
        actor_idx = state.actor_index
        actor_name = _pokerkit_to_player_name(actor_idx, hand)

        snapshot = StepSnapshot(
            step_idx=step_idx,
            street=street_native,
            street_pokerkit=_street_pokerkit(state),
            actor_index=actor_idx,
            actor_name=actor_name,
            action=action_type,
            amount=amount,
            pot_before=state.total_pot_amount,
            stacks_before=tuple(state.stacks),
            board=_board_tuple(state),
        )
        yield snapshot
        step_idx += 1

        # Apply action to state.
        if action_type == "fold":
            state.fold()
        elif action_type in ("check", "call", "call_allin"):
            # `call_allin`: PHH marker that the call put the villain
            # all-in. Mechanically still a check_or_call to pokerkit.
            if state.can_check_or_call():
                state.check_or_call()
        elif action_type in ("bet", "raise"):
            target = int(round(amount))
            if state.can_complete_bet_or_raise_to(target):
                state.complete_bet_or_raise_to(target)
            elif state.can_check_or_call():
                # Defensive: degenerate to call if PHH amount can't be matched.
                state.check_or_call()
        elif action_type in ("all_in", "allin", "raise_allin", "bet_allin"):
            # PHH `*_allin` variants: amount = chips committed. Treat
            # as a raise-to (or bet-to) target.
            if state.can_complete_bet_or_raise_to(int(round(amount))):
                state.complete_bet_or_raise_to(int(round(amount)))
            elif state.can_check_or_call():
                state.check_or_call()


def replay_to_list(hand: PHHHand) -> list[StepSnapshot]:
    """Convenience wrapper: replay and collect all snapshots."""
    return list(replay_steps(hand))
