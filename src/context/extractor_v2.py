"""Decision Point extractor v2.

Replaces `src.context.context_extractor.ContextExtractor`. Fixes:

1. Streets are read from PokerKit replay (and PHH native `street`
   field), not all forced to preflop.
2. Board is reconstructed per step from the action stream's
   `event="cards"` events, not from a non-existent top-level `phh.board`.
3. Villain holdings are extracted when revealed (event=cards with
   player=villain), then projected retroactively to all earlier
   decisions in the hand for hand_strength / draws / blockers / equity.

Output is a list of validated `DecisionPoint` Pydantic models, one
per villain decision in the hand.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from src.context.action_path import canonicalize_path
from src.context.dp_schema import (
    BlockersBlock,
    BoardTexture,
    DecisionPoint,
    DrawsBlock,
)
from src.context.line_tagger import identify_preflop_aggressor, tag_line
from src.context.street_detector import detect_streets
from src.hand_eval.blockers import compute_blockers
from src.hand_eval.draws import detect_draws
from src.hand_eval.equity import equity_vs_random
from src.hand_eval.evaluator import evaluate_hand
from src.hand_eval.made_hand import classify_made
from src.intent.classifier import classify_intent
from src.parsers.pokerkit_adapter import PHHHand, StepSnapshot, load_phh, replay_to_list


def extract_villain_holdings(hand: PHHHand) -> list[str] | None:
    """Scan PHH actions for villain's revealed cards (showdown).

    Returns the 2-card list, or None if villain's hand was not revealed.
    """
    villain_name = hand.villain_name
    for ev in hand.raw.get("actions", []):
        if (
            ev.get("event") == "cards"
            and ev.get("player") == villain_name
            and ev.get("cards")
        ):
            cards = ev["cards"]
            if len(cards) == 2:
                return list(cards)
    # Also check [showdown.hands] block as fallback
    for entry in hand.raw.get("showdown", {}).get("hands", []) or []:
        if entry.get("player") == villain_name and len(entry.get("cards", [])) == 2:
            return list(entry["cards"])
    return None


def extract_hero_holdings(hand: PHHHand) -> list[str] | None:
    """Scan PHH for hero's revealed cards (always present in this repo)."""
    hero_name = hand.hero_name
    for ev in hand.raw.get("actions", []):
        if (
            ev.get("event") == "cards"
            and ev.get("player") == hero_name
            and ev.get("cards")
        ):
            cards = ev["cards"]
            if len(cards) == 2:
                return list(cards)
    return None


def _board_texture(board: list[str]) -> BoardTexture:
    """Compute texture flags for a 0..5-card board."""
    if not board:
        return BoardTexture()
    suits = [c[1] for c in board]
    ranks = [c[0] for c in board]
    # Rank classification
    rank_values = {
        "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
        "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
    }
    rank_ints = sorted([rank_values[r] for r in ranks])
    is_paired = len(ranks) != len(set(ranks))
    suit_set = set(suits)
    n_suits = len(suit_set)
    # Connectivity: max gap among 3 consecutive lowest ranks
    is_connected = False
    if len(rank_ints) >= 3:
        # Any 3 of the board within a 5-rank window
        for i in range(len(rank_ints) - 2):
            if rank_ints[i + 2] - rank_ints[i] <= 4:
                is_connected = True
                break
    has_high = any(v >= 10 for v in rank_ints)
    return BoardTexture(
        monotone=(n_suits == 1 and len(suits) >= 3),
        two_tone=(n_suits == 2 and len(suits) == 3),
        rainbow=(n_suits == 3 and len(suits) == 3),
        paired=is_paired,
        trips=(len(ranks) - len(set(ranks)) >= 2),
        connected=is_connected,
        disconnected=(not is_connected and len(rank_ints) >= 3),
        high_broadway=has_high,
        low=(all(v <= 9 for v in rank_ints) and len(rank_ints) >= 3),
        wet=(is_connected or n_suits <= 2),
    )


def _identify_aggressor_label(
    snaps: list[StepSnapshot], hero_name: str
) -> str | None:
    """Return 'hero' / 'villain' / None for the last raiser/better."""
    last_actor: str | None = None
    for s in snaps:
        if s.action in ("bet", "raise", "all_in", "allin"):
            last_actor = s.actor_name
    if last_actor is None:
        return None
    return "hero" if last_actor == hero_name else "villain"


def _action_label(actor_name: str | None, action: str, amount: float, bb: int) -> str:
    """Sequence-element string used by vectorizer encoders."""
    label = "HERO" if False else (actor_name or "?").upper()
    if action in ("bet", "raise") and amount > 0 and bb > 0:
        return f"{label}_{action}_{int(round(amount / bb))}"
    return f"{label}_{action}"


def _extract_one_dp(
    *,
    snap: StepSnapshot,
    hand: PHHHand,
    buckets: dict[str, list[StepSnapshot]],
    villain_holdings: list[str] | None,
    pf_aggressor_name: str | None,
) -> DecisionPoint | None:
    """Build a DecisionPoint for a single villain decision snapshot."""
    bb = hand.bb
    villain_name = hand.villain_name
    hero_name = hand.hero_name

    # Skip non-villain decisions
    if snap.actor_name != villain_name:
        return None

    # Compute action_number_in_street (0-indexed villain action count)
    same_street = buckets.get(snap.street, [])
    action_number = sum(
        1
        for s in same_street
        if s.step_idx < snap.step_idx and s.actor_name == villain_name
    )

    # Pot in BB; effective stack in BB; SPR
    pot_bb = snap.pot_before / bb if bb > 0 else 0.0
    eff_stack_chips = (
        min(snap.stacks_before)
        if snap.stacks_before
        else 0
    )
    eff_stack_bb = eff_stack_chips / bb if bb > 0 else 0.0
    spr = eff_stack_bb / pot_bb if pot_bb > 0 else None

    # Position labels
    is_btn = villain_name == hand.btn_player_name
    if snap.street == "preflop":
        villain_pos = "BTN" if is_btn else "BB"
        hero_pos = "BB" if is_btn else "BTN"
    else:
        # Postflop HU: BTN is IP
        villain_pos = "IP" if is_btn else "OOP"
        hero_pos = "OOP" if is_btn else "IP"

    # Sequences
    preflop_seq = [
        _action_label(s.actor_name, s.action, s.amount, bb)
        for s in buckets.get("preflop", [])
    ]
    earlier_in_street = [
        s for s in same_street if s.step_idx < snap.step_idx
    ]
    current_seq = [
        _action_label(s.actor_name, s.action, s.amount, bb)
        for s in earlier_in_street
    ]
    action_path = canonicalize_path(
        earlier_in_street + [snap], hero_name=hero_name, bb=bb, street=snap.street,
    )

    # Aggressors
    pf_aggr = _identify_aggressor_label(buckets.get("preflop", []), hero_name)
    current_aggr = _identify_aggressor_label(earlier_in_street, hero_name)

    # Board texture
    board = list(snap.board)
    texture = _board_texture(board)

    # Holdings + derived analytics (only when villain's hand is revealed)
    villain_hand = villain_holdings
    villain_hand_strength = None
    villain_made_specific = None
    villain_hand_rank_int = None
    draws_block = None
    blockers_block = None
    villain_equity = None
    intent = None

    if villain_hand:
        try:
            rank = evaluate_hand(villain_hand, board)
            villain_hand_strength = rank.category
            villain_hand_rank_int = rank.rank_int
            villain_made_specific = classify_made(villain_hand, board)
        except Exception as e:
            logger.debug(f"eval failed for {hand.hand_id}: {e}")

        try:
            draws = detect_draws(villain_hand, board)
            draws_block = DrawsBlock(
                nut_flush_draw=draws.nut_flush_draw,
                weak_flush_draw=draws.weak_flush_draw,
                has_oesd=draws.has_oesd,
                has_double_gutshot=draws.has_double_gutshot,
                has_gutshot=draws.has_gutshot,
                has_combo_draw=draws.has_combo_draw,
                has_bdfd=draws.has_bdfd,
                has_bdsd=draws.has_bdsd,
                has_overcard_draw=draws.has_overcard_draw,
                has_pair_plus_draw=draws.has_pair_plus_draw,
                outs_count=draws.outs_count,
            )
        except Exception as e:
            logger.debug(f"draws failed for {hand.hand_id}: {e}")

        try:
            b = compute_blockers(villain_hand, board)
            blockers_block = BlockersBlock(
                blocks_nut_flush=b.blocks_nut_flush,
                blocks_nut_straight=b.blocks_nut_straight,
                blocks_top_set=b.blocks_top_set,
                blocks_top_two_pair=b.blocks_top_two_pair,
                has_ace_high_blocker=b.has_ace_high_blocker,
                has_king_high_blocker=b.has_king_high_blocker,
            )
        except Exception as e:
            logger.debug(f"blockers failed for {hand.hand_id}: {e}")

        # Equity is expensive; only compute postflop with at least 3
        # board cards (preflop equity is precomputable later if needed).
        if 3 <= len(board) <= 5:
            try:
                villain_equity = equity_vs_random(
                    villain_hand, board, samples=200, seed=hash(snap.step_idx) & 0xFFFFFFFF,
                )
            except Exception as e:
                logger.debug(f"equity failed for {hand.hand_id}: {e}")

        if villain_made_specific is not None and draws_block is not None:
            from src.hand_eval.draws import Draws as DrawsDC

            draws_dc = DrawsDC(**draws_block.model_dump())
            try:
                intent = classify_intent(
                    action=snap.action,
                    made_label=villain_made_specific,
                    draws=draws_dc,
                    bet_size_pot_pct=(
                        100.0 * snap.amount / snap.pot_before
                        if snap.pot_before > 0 and snap.action in ("bet", "raise")
                        else None
                    ),
                )
            except Exception as e:
                logger.debug(f"intent failed for {hand.hand_id}: {e}")

    line = tag_line(
        snap, street_history=buckets, preflop_aggressor=pf_aggressor_name,
    )

    # Bet size in BB / %pot
    bet_bb = snap.amount / bb if (bb > 0 and snap.action in ("bet", "raise")) else None
    bet_pct = (
        100.0 * snap.amount / snap.pot_before
        if snap.pot_before > 0 and snap.action in ("bet", "raise")
        else None
    )

    # Showdown info
    sd = hand.raw.get("showdown", {}) or {}
    went_to_showdown = bool(sd.get("hands"))
    won = villain_name in (sd.get("winners", []) or [])

    try:
        return DecisionPoint(
            decision_id=f"{hand.hand_id}_{snap.step_idx}",
            hand_id=hand.hand_id,
            villain_name=villain_name,
            hero_name=hero_name,
            step_idx=snap.step_idx,
            street=snap.street,
            action_number_in_street=action_number,
            pot_bb=pot_bb,
            eff_stack_bb=eff_stack_bb,
            spr=spr,
            villain_position=villain_pos,
            hero_position=hero_pos,
            preflop_sequence=preflop_seq,
            current_street_sequence=current_seq,
            action_path=action_path,
            preflop_aggressor=pf_aggr,
            current_aggressor=current_aggr,
            board_cards=board,
            board_texture=texture,
            villain_hand=villain_hand,
            villain_hand_strength=villain_hand_strength,
            villain_made_specific=villain_made_specific,
            villain_hand_rank_int=villain_hand_rank_int,
            villain_draws=draws_block,
            villain_blockers=blockers_block,
            villain_equity_vs_random=villain_equity,
            intent=intent,
            line_tag=line,
            villain_action=snap.action,
            villain_bet_size_bb=bet_bb,
            villain_bet_size_pot_pct=bet_pct,
            went_to_showdown=went_to_showdown,
            villain_won=won if went_to_showdown else None,
        )
    except Exception as e:
        logger.warning(
            f"DP validation failed for {hand.hand_id} step {snap.step_idx}: {e}"
        )
        return None


def extract_decision_points(hand: PHHHand) -> list[DecisionPoint]:
    """Extract all villain decision points from a single PHH."""
    snapshots = replay_to_list(hand)
    buckets = {
        street: [s for s in snapshots if s.street == street]
        for street in ("preflop", "flop", "turn", "river")
    }

    villain_holdings = extract_villain_holdings(hand)
    pf_aggressor_name = identify_preflop_aggressor(buckets["preflop"])

    dps: list[DecisionPoint] = []
    for snap in snapshots:
        if snap.actor_name == hand.villain_name:
            dp = _extract_one_dp(
                snap=snap,
                hand=hand,
                buckets=buckets,
                villain_holdings=villain_holdings,
                pf_aggressor_name=pf_aggressor_name,
            )
            if dp is not None:
                dps.append(dp)
    return dps


def extract_from_phh_path(phh_path: Path | str) -> list[DecisionPoint]:
    """Convenience: load a PHH file and extract its DPs."""
    return extract_decision_points(load_phh(phh_path))


def extract_from_directory(phh_dir: Path | str) -> list[DecisionPoint]:
    """Iterate all .phh files in a directory and extract DPs from each."""
    p = Path(phh_dir)
    all_dps: list[DecisionPoint] = []
    for f in sorted(p.glob("*.phh")):
        try:
            all_dps.extend(extract_from_phh_path(f))
        except Exception as e:
            logger.warning(f"skipping {f.name}: {e}")
    return all_dps


def dps_to_records(dps: list[DecisionPoint]) -> list[dict[str, Any]]:
    """Serialize DP list to plain dicts for parquet/DataFrame storage."""
    return [dp.model_dump() for dp in dps]
