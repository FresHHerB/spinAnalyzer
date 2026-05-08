"""Canonical string representation of a per-street action sequence.

Used by Mode-A / Linha-2 search to filter candidate decision points
before the FAISS step. Two DPs that share an action_path are in the
same spot up to that point.

Format
------
Each token is `<actor>_<verb>[<size>]` separated by `-`:
    actor:  H (hero) or V (villain)
    verb:   X (check), C (call), F (fold), B<pct> (bet of pct%pot),
            R<pct> (raise to total = pct% of pre-action pot),
            A (all-in)
    size:   percentage of the pot (or, on preflop, multiples of BB)
            rounded to the nearest integer

Examples
--------
    `H_R3-V_C`        — preflop hero raise to ~3bb, villain calls
    `V_X-H_X`         — flop check-check
    `V_B50-H_RR`      — flop villain bets 50%pot, hero raises (RR
                        = raise here is reusing R prefix)

Determinism: identical (street, actor sequence, integer-rounded sizes)
always produces the same string.
"""

from __future__ import annotations

from src.parsers.pokerkit_adapter import StepSnapshot


def _actor_token(snap: StepSnapshot, hero_name: str) -> str:
    if snap.actor_name == hero_name:
        return "H"
    return "V"


def _round_pct(numerator: float, denominator: float) -> int:
    """Integer percentage with safe divide-by-zero guard."""
    if denominator <= 0:
        return 0
    return int(round((numerator / denominator) * 100))


def _verb_token(snap: StepSnapshot, street: str, bb: int) -> str:
    """Build the action verb segment for one snapshot."""
    a = snap.action
    if a == "fold":
        return "F"
    if a == "check":
        return "X"
    if a == "call":
        return "C"
    if a in ("bet",):
        # Postflop opening bet: size as % of pot before the bet.
        pct = _round_pct(snap.amount, snap.pot_before)
        return f"B{pct}"
    if a in ("raise", "all_in", "allin"):
        # Total stake target on the street. Express preflop as bb-multiple
        # to match poker convention; postflop as % of pre-action pot.
        if street == "preflop" and bb > 0:
            mult = max(1, int(round(snap.amount / bb)))
            return f"R{mult}"
        pct = _round_pct(snap.amount, snap.pot_before)
        return f"R{pct}"
    # Defensive default: include the verb verbatim, uppercased.
    return a.upper()


def canonicalize_path(
    snapshots: list[StepSnapshot],
    *,
    hero_name: str,
    bb: int,
    street: str,
) -> str:
    """Build the canonical path string for one street's snapshots.

    Args:
        snapshots: ordered list of snapshots from a single street.
        hero_name: identifies which actor maps to the `H` prefix.
        bb: big blind amount (used to express preflop raises in bb).
        street: the street these snapshots belong to. Affects sizing
            convention (preflop uses bb multiples; postflop uses %pot).

    Returns:
        Canonical path string. Empty string when `snapshots` is empty.
    """
    if not snapshots:
        return ""
    tokens: list[str] = []
    for snap in snapshots:
        actor = _actor_token(snap, hero_name)
        verb = _verb_token(snap, street, bb)
        tokens.append(f"{actor}_{verb}")
    return "-".join(tokens)
