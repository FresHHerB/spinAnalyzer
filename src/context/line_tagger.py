"""Tag a single decision with the conventional poker "line" descriptor.

Operates on the per-street snapshot stream (from PokerKit replay) and
the running history of who was the preflop / per-street aggressor.

Tags emitted (one per decision):

    cbet            — preflop aggressor's first postflop bet
    donk            — non-aggressor leads into the aggressor postflop
    xr              — check-raise (after a check)
    xx_then_probe   — bet on the street following a check-check
    delayed_cbet    — preflop aggressor checks flop, bets turn
    second_barrel   — preflop aggressor cbets flop, bets again on turn
    triple_barrel   — preflop aggressor barrels all three streets
    float           — defender flat-called a cbet OOP without a draw
    probe           — non-aggressor bets after the aggressor checks
    give_up         — preflop aggressor checks (no continuation)
    none            — pre/postflop action that doesn't match a tag
"""

from __future__ import annotations

from src.parsers.pokerkit_adapter import StepSnapshot

STREETS = ("preflop", "flop", "turn", "river")


def _street_idx(street: str) -> int:
    return STREETS.index(street)


def tag_line(
    snap: StepSnapshot,
    *,
    street_history: dict[str, list[StepSnapshot]],
    preflop_aggressor: str | None,
) -> str:
    """Compute the line tag for one snapshot in the context of its hand.

    Args:
        snap: the decision snapshot we're tagging.
        street_history: complete buckets-by-street produced by
            `street_detector.detect_streets`. Required because some
            tags reference earlier streets.
        preflop_aggressor: the actor name of the last preflop raiser
            (or None if no preflop raise occurred).
    """
    street = snap.street
    same_street = street_history.get(street, [])
    earlier_in_street = [s for s in same_street if s.step_idx < snap.step_idx]

    is_aggressive = snap.action in ("bet", "raise", "all_in", "allin")
    is_check = snap.action == "check"

    if street == "preflop":
        return "none"

    actor_is_pf_aggressor = (
        preflop_aggressor is not None and snap.actor_name == preflop_aggressor
    )

    # Aggressive postflop tags
    if is_aggressive:
        if not earlier_in_street:
            # First action of street
            if actor_is_pf_aggressor:
                # cbet (and barrels by street index)
                return _barrel_tag(street, street_history, preflop_aggressor)
            return "donk"
        # Not first: was there a check before? → xr / probe / 2nd-barrel
        prior_actions = [s.action for s in earlier_in_street]
        if "check" in prior_actions and "bet" not in prior_actions and "raise" not in prior_actions:
            # All earlier actions were checks
            if actor_is_pf_aggressor:
                # PF aggressor checked behind earlier? No — they wouldn't
                # have acted yet. This case is rare.
                return _barrel_tag(street, street_history, preflop_aggressor)
            return "probe"
        # There was a bet earlier this street
        if "bet" in prior_actions or "raise" in prior_actions:
            return "xr"
        return "none"

    # Passive postflop tags
    if is_check and actor_is_pf_aggressor and not earlier_in_street:
        return "give_up"

    if snap.action == "call" and actor_is_pf_aggressor is False:
        # Defender called a bet
        if street == "flop":
            return "float"

    return "none"


def _barrel_tag(
    street: str,
    street_history: dict[str, list[StepSnapshot]],
    pf_agg: str | None,
) -> str:
    """Determine cbet / second_barrel / triple_barrel based on aggressor's
    history through earlier streets."""
    if pf_agg is None:
        return "none"
    if street == "flop":
        return "cbet"
    if street == "turn":
        # Did pf aggressor cbet flop?
        flop_agg_bets = any(
            s.actor_name == pf_agg
            and s.action in ("bet", "raise", "all_in", "allin")
            for s in street_history.get("flop", [])
        )
        if flop_agg_bets:
            return "second_barrel"
        return "delayed_cbet"
    if street == "river":
        flop_agg_bets = any(
            s.actor_name == pf_agg
            and s.action in ("bet", "raise", "all_in", "allin")
            for s in street_history.get("flop", [])
        )
        turn_agg_bets = any(
            s.actor_name == pf_agg
            and s.action in ("bet", "raise", "all_in", "allin")
            for s in street_history.get("turn", [])
        )
        if flop_agg_bets and turn_agg_bets:
            return "triple_barrel"
        if turn_agg_bets:
            return "second_barrel"
        return "delayed_cbet"
    return "none"


def identify_preflop_aggressor(
    preflop_snaps: list[StepSnapshot],
) -> str | None:
    """Return the actor_name of the last preflop raiser (or None)."""
    last = None
    for s in preflop_snaps:
        if s.action in ("raise", "all_in", "allin"):
            last = s.actor_name
    return last
