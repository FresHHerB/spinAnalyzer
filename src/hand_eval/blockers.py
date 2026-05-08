"""Card-removal effects: which strong opposing combos our holding blocks.

Blockers matter for hand-reading: when we hold the A of hearts on a
3-heart board, opponent cannot hold the nut flush. The extractor uses
blockers to qualify intent (e.g. value-blocker bluffs).
"""

from __future__ import annotations

from dataclasses import dataclass

_RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}


@dataclass(frozen=True)
class Blockers:
    """Card-removal flags for the given holding + board."""

    blocks_nut_flush: bool
    blocks_nut_straight: bool
    blocks_top_set: bool
    blocks_top_two_pair: bool
    has_ace_high_blocker: bool
    has_king_high_blocker: bool


def compute_blockers(hole: list[str], board: list[str]) -> Blockers:
    """Return blocker flags for a 2-card holding on a 3..5-card board."""
    if len(hole) != 2:
        raise ValueError(f"hole must have 2 cards, got {len(hole)}")
    if not 0 <= len(board) <= 5:
        raise ValueError(f"board must be 0..5 cards, got {len(board)}")

    if not board:
        return Blockers(
            blocks_nut_flush=False,
            blocks_nut_straight=False,
            blocks_top_set=False,
            blocks_top_two_pair=False,
            has_ace_high_blocker=any(c[0] == "A" for c in hole),
            has_king_high_blocker=any(c[0] == "K" for c in hole),
        )

    board_suit_counts: dict[str, int] = {}
    for c in board:
        s = c[1]
        board_suit_counts[s] = board_suit_counts.get(s, 0) + 1

    # Nut flush blocker: we hold the A of a suit that has ≥3 on board.
    blocks_nf = False
    for c in hole:
        if c[0] == "A" and board_suit_counts.get(c[1], 0) >= 3:
            blocks_nf = True
            break

    # Nut straight blocker: simplified — we hold a card that would
    # complete the highest possible straight on this board.
    board_ranks = sorted({_RANK_VALUES[c[0]] for c in board}, reverse=True)
    hole_ranks = {_RANK_VALUES[c[0]] for c in hole}
    nut_straight_top = _highest_straight_top(set(board_ranks))
    blocks_ns = False
    if nut_straight_top:
        # Nut straight uses ranks {top-4 .. top}. Any of those ranks in
        # our hole that aren't already on the board is a blocker.
        nut_ranks = set(range(nut_straight_top - 4, nut_straight_top + 1))
        blocks_ns = bool((hole_ranks & nut_ranks) - set(board_ranks))

    # Top set blocker: we hold the rank of the highest board card.
    top_board = board_ranks[0]
    blocks_top_set = top_board in hole_ranks

    # Top two pair blocker: we hold one of the top two board ranks
    # (denying opponent a TP+2P combination).
    blocks_top_two = False
    if len(board_ranks) >= 2:
        blocks_top_two = bool(hole_ranks & {board_ranks[0], board_ranks[1]})

    return Blockers(
        blocks_nut_flush=blocks_nf,
        blocks_nut_straight=blocks_ns,
        blocks_top_set=blocks_top_set,
        blocks_top_two_pair=blocks_top_two,
        has_ace_high_blocker=any(c[0] == "A" for c in hole),
        has_king_high_blocker=any(c[0] == "K" for c in hole),
    )


def _highest_straight_top(rank_set: set[int]) -> int | None:
    """Return the top rank of the highest possible straight using ranks
    drawn from `rank_set ∪ unknowns`. Returns None if no straight is
    possible from at most 3 board ranks (need ≥3 within 5 of each other).
    """
    if not rank_set:
        return None
    candidates = set(rank_set)
    if 14 in candidates:
        candidates.add(1)
    # Find the highest top such that the 5-window has ≥3 cards from
    # the rank_set (so a straight is reachable using at most 2 unseen
    # cards — i.e. opponent could have them).
    for top in range(14, 4, -1):
        window = set(range(top - 4, top + 1))
        if len(window & candidates) >= 3:
            return top
    return None
