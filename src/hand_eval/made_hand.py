"""Refine a generic hand category (PAIR/SET/etc) into a poker-specific
label (TPTK/2nd_set/overpair/etc).

The plan calls for ~15 specific labels covering the strategically
distinct made hands. We map by examining the relationship between the
hole cards and the board ranks.
"""

from __future__ import annotations

from src.hand_eval.evaluator import HandRank, evaluate_hand

_RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}


def _rank_value(card: str) -> int:
    return _RANK_VALUES[card[0]]


def _board_ranks_sorted(board: list[str]) -> list[int]:
    return sorted({_rank_value(c) for c in board}, reverse=True)


def _board_pairs(board: list[str]) -> dict[int, int]:
    """Return {rank_value: count} for ranks that appear ≥1 on the board."""
    counts: dict[int, int] = {}
    for c in board:
        v = _rank_value(c)
        counts[v] = counts.get(v, 0) + 1
    return counts


def classify_made(hole: list[str], board: list[str]) -> str:
    """Return a specific made-hand label.

    Categories returned (subset of):
        nut_straight_flush, straight_flush, quads, boat,
        nut_flush, second_nut_flush, weak_flush,
        nut_straight, weak_straight,
        top_set, mid_set, bottom_set,
        two_pair_top_top, two_pair_top_other, two_pair_lower,
        overpair, TPTK, TPGK, TPWK,
        second_pair, third_pair, under_pair,
        pocket_pair_under_board, ace_high, king_high, high_card,
        unknown
    """
    if not board:
        # Preflop: classify by whether hole is paired
        if hole[0][0] == hole[1][0]:
            return "pocket_pair"
        return "high_card"

    rank = evaluate_hand(hole, board)
    return _classify_from_rank(rank, hole, board)


def _classify_from_rank(rank: HandRank, hole: list[str], board: list[str]) -> str:
    cat = rank.category
    board_ranks = _board_ranks_sorted(board)
    top_board_rank = board_ranks[0]
    hole_ranks = sorted([_rank_value(hole[0]), _rank_value(hole[1])], reverse=True)
    pair_counts = _board_pairs(board)

    if cat == "STRAIGHT_FLUSH":
        # A-high straight flush == royal/nut
        all_ranks = sorted(
            [_rank_value(c) for c in hole + board], reverse=True
        )
        return "nut_straight_flush" if all_ranks[0] == 14 else "straight_flush"
    if cat == "FOUR_OF_A_KIND":
        return "quads"
    if cat == "FULL_HOUSE":
        return "boat"
    if cat == "FLUSH":
        # Determine flush nut status by comparing hole flush card to
        # any flush card not present on the board.
        hole_suits = [c[1] for c in hole]
        board_suits = [c[1] for c in board]
        flush_suit = max(set(hole_suits + board_suits), key=(hole_suits + board_suits).count)
        hole_flush_ranks = sorted(
            [_rank_value(c) for c in hole if c[1] == flush_suit], reverse=True
        )
        if not hole_flush_ranks:
            return "weak_flush"
        if hole_flush_ranks[0] == 14:
            return "nut_flush"
        if hole_flush_ranks[0] in (12, 13):
            return "second_nut_flush"
        return "weak_flush"
    if cat == "STRAIGHT":
        # Nut straight = uses the highest card (= top of the straight)
        # Approximation: if hole contains the top card of the made
        # straight (often A or K), call it nut. Otherwise weak.
        all_ranks = sorted(
            {_rank_value(c) for c in hole + board}, reverse=True
        )
        # Find a 5-in-a-row in all_ranks (treat A as both 14 and 1)
        ranks_set = set(all_ranks)
        if 14 in ranks_set:
            ranks_set.add(1)
        for top in sorted(ranks_set, reverse=True):
            if all((top - i) in ranks_set for i in range(5)):
                # Check if hole contributes to the top
                if top in hole_ranks or (top == 14 and 14 in hole_ranks):
                    return "nut_straight"
                return "weak_straight"
        return "weak_straight"
    if cat == "THREE_OF_A_KIND":
        # Set vs trips: set uses both hole cards (pocket pair), trips
        # uses one hole + paired board.
        if hole_ranks[0] == hole_ranks[1]:
            # Pocket pair → set. Compare to board ranks.
            pp = hole_ranks[0]
            if pp == top_board_rank:
                return "top_set"
            higher_board = [r for r in board_ranks if r > pp]
            if not higher_board:
                return "top_set"
            if pp == sorted(board_ranks)[0]:
                return "bottom_set"
            return "mid_set"
        # trips (one hole rank matches paired board)
        for h in hole_ranks:
            if pair_counts.get(h, 0) >= 2:
                return "trips"
        return "trips"
    if cat == "TWO_PAIR":
        # Determine which pairs: typically one hole + top board pair, or
        # two unpaired hole + matching board ranks.
        paired_hole_ranks = [r for r in hole_ranks if pair_counts.get(r, 0) >= 1]
        if len(paired_hole_ranks) == 2:
            top_two = sorted(paired_hole_ranks, reverse=True)
            if top_two[0] == top_board_rank:
                return "two_pair_top_top"
            return "two_pair_top_other"
        # Pocket pair + matching board card
        return "two_pair_lower"
    if cat == "ONE_PAIR":
        # Determine pair source: hole pair (overpair / underpair / pocket
        # pair) vs hole+board pair (TPTK / TPGK / TPWK / 2nd / 3rd).
        if hole_ranks[0] == hole_ranks[1]:
            # Pocket pair
            pp = hole_ranks[0]
            if pp > top_board_rank:
                return "overpair"
            return "pocket_pair_under_board"
        # Hole + board pair
        for h in hole_ranks:
            if pair_counts.get(h, 0) >= 1:
                # Pair the board with this hole rank
                kicker = max(r for r in hole_ranks if r != h)
                if h == top_board_rank:
                    if kicker == 14:
                        return "TPTK"
                    if kicker >= 11:
                        return "TPGK"
                    return "TPWK"
                # Hit a non-top board rank
                if h == board_ranks[1] if len(board_ranks) >= 2 else False:
                    return "second_pair"
                if len(board_ranks) >= 3 and h == board_ranks[2]:
                    return "third_pair"
                return "under_pair"
        return "high_card"
    # HIGH_CARD
    if 14 in hole_ranks:
        return "ace_high"
    if 13 in hole_ranks:
        return "king_high"
    return "high_card"
