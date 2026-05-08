"""Draw detection: flush draws, straight draws, combo draws, backdoors.

Operates on the holdings + board, computing which draws exist and
counting outs (cards that complete the draw).
"""

from __future__ import annotations

from dataclasses import dataclass

_RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}


@dataclass(frozen=True)
class Draws:
    """Draws available given the current holdings + board."""

    nut_flush_draw: bool
    weak_flush_draw: bool
    has_oesd: bool        # 8 outs
    has_double_gutshot: bool  # also 8 outs
    has_gutshot: bool     # 4 outs
    has_combo_draw: bool  # FD + SD together (12+ outs)
    has_bdfd: bool        # backdoor flush draw (need 2 perfect cards)
    has_bdsd: bool        # backdoor straight draw
    has_overcard_draw: bool  # 2 unpaired hole > board top
    has_pair_plus_draw: bool  # paired + drawing
    outs_count: int


def _suits(cards: list[str]) -> list[str]:
    return [c[1] for c in cards]


def _ranks(cards: list[str]) -> list[int]:
    return [_RANK_VALUES[c[0]] for c in cards]


def _flush_draw(hole: list[str], board: list[str]) -> tuple[bool, bool]:
    """Return (any_flush_draw, is_nut). FD means ≥4 of same suit, ≥1 from hole."""
    if len(board) < 3 or len(board) > 4:
        return False, False
    all_suits = _suits(hole + board)
    suit_counts: dict[str, int] = {}
    for s in all_suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    for suit, count in suit_counts.items():
        if count == 4:
            hole_suit_cards = [c for c in hole if c[1] == suit]
            if not hole_suit_cards:
                return False, False
            hole_max_rank = max(_RANK_VALUES[c[0]] for c in hole_suit_cards)
            return True, hole_max_rank == 14
    return False, False


def _backdoor_flush_draw(hole: list[str], board: list[str]) -> bool:
    """BDFD: exactly 3 cards of same suit on flop with ≥1 from hole."""
    if len(board) != 3:
        return False
    all_suits = _suits(hole + board)
    suit_counts: dict[str, int] = {}
    for s in all_suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    for suit, count in suit_counts.items():
        if count == 3:
            hole_suit_cards = [c for c in hole if c[1] == suit]
            if hole_suit_cards:
                return True
    return False


def _straight_outs(hole: list[str], board: list[str]) -> tuple[set[int], int]:
    """Compute straight out ranks and total card count.

    Returns (out_ranks, card_count). Each rank contributes 4 suits to
    card_count (capped if board reduces availability — we don't subtract
    here for simplicity).
    """
    if not 3 <= len(board) <= 4:
        return set(), 0
    rank_set: set[int] = set(_ranks(hole + board))
    if 14 in rank_set:
        rank_set.add(1)

    outs: set[int] = set()
    for top in range(5, 15):
        target = set(range(top - 4, top + 1))
        missing = target - rank_set
        if len(missing) == 1:
            (m,) = missing
            outs.add(m if m != 1 else 14)
    return outs, len(outs) * 4


def _gutshot(hole: list[str], board: list[str]) -> bool:
    out_ranks, _ = _straight_outs(hole, board)
    return len(out_ranks) == 1


def _backdoor_straight_draw(hole: list[str], board: list[str]) -> bool:
    """BDSD: any 3 consecutive ranks among hole+flop with ≥1 hole rank."""
    if len(board) != 3:
        return False
    hole_ranks = set(_ranks(hole))
    all_ranks = set(_ranks(hole + board))
    if 14 in all_ranks:
        all_ranks.add(1)
    for top in range(3, 15):
        triple = set(range(top - 2, top + 1))
        if triple.issubset(all_ranks) and (triple & hole_ranks):
            return True
    return False


def _overcard_draw(hole: list[str], board: list[str]) -> bool:
    """Both hole cards > top board card AND not paired (has 6 outs to pair)."""
    if not board:
        return False
    if hole[0][0] == hole[1][0]:
        return False  # pocket pair
    top_board = max(_ranks(board))
    return all(_RANK_VALUES[c[0]] > top_board for c in hole)


def _pair_plus_draw(hole: list[str], board: list[str], has_draw: bool) -> bool:
    """Pair + flush/straight draw."""
    if not has_draw:
        return False
    hole_set = {_RANK_VALUES[c[0]] for c in hole}
    board_set = {_RANK_VALUES[c[0]] for c in board}
    paired_with_board = bool(hole_set & board_set)
    paired_pocket = hole[0][0] == hole[1][0]
    return paired_with_board or paired_pocket


def detect_draws(hole: list[str], board: list[str]) -> Draws:
    """Return all draw flags + total outs for the given holdings."""
    if len(hole) != 2:
        raise ValueError(f"hole must have 2 cards, got {len(hole)}")
    if not 0 <= len(board) <= 5:
        raise ValueError(f"board must be 0..5 cards, got {len(board)}")

    fd, nut_fd = _flush_draw(hole, board)
    weak_fd = fd and not nut_fd
    bdfd = _backdoor_flush_draw(hole, board)
    out_ranks, _card_count = _straight_outs(hole, board)
    n_out_ranks = len(out_ranks)
    # OESD: exists a 4-rank contiguous run in hole+board (so a card on
    # either side completes a straight). Double gutshot: 2 outs but no
    # 4-contiguous run. Gutshot: exactly 1 out.
    is_oesd = False
    is_double_gs = False
    is_gs = False
    if n_out_ranks >= 2:
        rank_set = set(_ranks(hole + board))
        if 14 in rank_set:
            rank_set.add(1)
        has_4_contig = any(
            all((top - i) in rank_set for i in range(4))
            for top in range(4, 15)
        )
        if has_4_contig:
            is_oesd = True
        else:
            is_double_gs = True
    elif n_out_ranks == 1:
        is_gs = True
    bdsd = _backdoor_straight_draw(hole, board) and n_out_ranks == 0 and not fd
    has_combo = fd and (is_oesd or is_double_gs or is_gs)

    # Outs: flush 9, OESD/double-gutshot 8, gutshot 4. Combo subtracts
    # overlap (one straight out per suit overlaps the flush draw).
    outs = 0
    if fd:
        outs += 9
    if is_oesd or is_double_gs:
        outs += 8 if not fd else 6
    elif is_gs:
        outs += 4 if not fd else 3
    outs = min(outs, 15)

    overcard = _overcard_draw(hole, board)
    pair_plus = _pair_plus_draw(
        hole, board, has_draw=fd or is_oesd or is_double_gs or is_gs
    )

    return Draws(
        nut_flush_draw=nut_fd,
        weak_flush_draw=weak_fd,
        has_oesd=is_oesd,
        has_double_gutshot=is_double_gs,
        has_gutshot=is_gs,
        has_combo_draw=has_combo,
        has_bdfd=bdfd and not fd,
        has_bdsd=bdsd,
        has_overcard_draw=overcard,
        has_pair_plus_draw=pair_plus,
        outs_count=outs,
    )
