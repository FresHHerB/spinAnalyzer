"""Rule-based intent classification.

Given a decision (made hand specific + draws + outs + the actual
action taken), assign one of:

    value_pure     — strong made hand, betting/raising
    thin_value     — medium made hand, betting small
    semi_bluff     — has draw, betting/raising
    bluff_pure     — air, betting/raising large
    bluff_catcher  — weak made, calling
    give_up        — had equity, check-folded
    pot_control    — medium made, checking/calling small
    unknown        — insufficient info
"""

from __future__ import annotations

from src.hand_eval.draws import Draws

# Made-hand strength tiers (from src.hand_eval.made_hand labels).
_STRONG_MADE = {
    "nut_straight_flush",
    "straight_flush",
    "quads",
    "boat",
    "nut_flush",
    "second_nut_flush",
    "nut_straight",
    "top_set",
    "mid_set",
    "bottom_set",
    "two_pair_top_top",
    "two_pair_top_other",
    "trips",
    "overpair",
    "TPTK",
}

_MEDIUM_MADE = {
    "TPGK",
    "weak_flush",
    "weak_straight",
    "two_pair_lower",
}

_WEAK_MADE = {
    "TPWK",
    "second_pair",
    "third_pair",
    "under_pair",
    "pocket_pair_under_board",
    "pocket_pair",
}

_AIR = {"high_card", "ace_high", "king_high"}

_BIG_BET_PCT = 0.66    # ≥66%pot
_SMALL_BET_PCT = 0.40  # <40%pot


def classify_intent(
    *,
    action: str,
    made_label: str,
    draws: Draws,
    bet_size_pot_pct: float | None,
) -> str:
    """Assign an intent label to one decision."""
    has_significant_draw = (
        draws.nut_flush_draw
        or draws.weak_flush_draw
        or draws.has_oesd
        or draws.has_double_gutshot
        or (draws.has_combo_draw and draws.outs_count >= 12)
    )

    is_aggressive = action in ("bet", "raise", "all_in", "allin")
    is_passive_call = action == "call"
    is_passive_check = action == "check"
    is_fold = action == "fold"

    pct = bet_size_pot_pct if bet_size_pot_pct is not None else 0.0
    is_big = pct >= _BIG_BET_PCT * 100
    is_small = pct < _SMALL_BET_PCT * 100

    if is_aggressive:
        if made_label in _STRONG_MADE:
            return "value_pure" if is_big else "thin_value"
        if made_label in _MEDIUM_MADE:
            return "thin_value" if is_small else "value_pure"
        if has_significant_draw:
            return "semi_bluff"
        if made_label in _AIR:
            return "bluff_pure"
        if made_label in _WEAK_MADE:
            return "thin_value" if is_small else "bluff_pure"
        return "unknown"

    if is_passive_call:
        if made_label in _STRONG_MADE:
            return "value_pure"  # call with strong = trap or pot-control
        if made_label in _MEDIUM_MADE or made_label in _WEAK_MADE:
            return "bluff_catcher"
        if has_significant_draw:
            return "semi_bluff"  # call with draw = pot odds chase
        return "bluff_catcher"

    if is_passive_check:
        if made_label in _STRONG_MADE:
            return "value_pure"  # slow-play
        if made_label in _MEDIUM_MADE or made_label in _WEAK_MADE:
            return "pot_control"
        return "pot_control"

    if is_fold:
        if has_significant_draw or made_label in _MEDIUM_MADE:
            return "give_up"
        return "give_up" if made_label not in _AIR else "unknown"

    return "unknown"
