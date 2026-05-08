"""Made-hand evaluation wrapper around pokerkit.

Returns a comparable rank, the broad category, and a normalized
"specific" label that downstream classifiers (made_hand.py) can refine
into TPTK / 2nd_set / overpair / etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from pokerkit import StandardHighHand


@dataclass(frozen=True)
class HandRank:
    """Result of evaluating a holding on a board."""

    category: str  # HIGH_CARD / ONE_PAIR / ... / STRAIGHT_FLUSH
    rank_int: int  # comparable: higher = stronger (pokerkit entry.index)
    label_text: str  # human-readable: "One pair", "Top set", ...

    def __lt__(self, other: "HandRank") -> bool:
        return self.rank_int < other.rank_int

    def __le__(self, other: "HandRank") -> bool:
        return self.rank_int <= other.rank_int


def _to_pokerkit_str(cards: list[str]) -> str:
    """Concatenate canonical 2-char card strings into pokerkit's expected form."""
    return "".join(cards)


def evaluate_hand(hole: list[str], board: list[str]) -> HandRank:
    """Evaluate a 2-card hole + 0..5-card board.

    Preflop (board empty) returns a HIGH_CARD rank derived from the hole
    only — pokerkit needs at least one board card for evaluation, so we
    fall back to an internal preflop rank.
    """
    if len(hole) != 2:
        raise ValueError(f"hole must have 2 cards, got {len(hole)}")
    if not 0 <= len(board) <= 5:
        raise ValueError(f"board must be 0..5 cards, got {len(board)}")

    if len(board) == 0:
        return _preflop_rank(hole)

    h = StandardHighHand.from_game(_to_pokerkit_str(hole), _to_pokerkit_str(board))
    label = h.entry.label
    return HandRank(
        category=label.name,
        rank_int=h.entry.index,
        label_text=label.value,
    )


_RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}


def _preflop_rank(hole: list[str]) -> HandRank:
    """Synthetic rank for preflop holdings (board empty).

    Not used for showdown comparison — only to give the extractor a
    non-null value before any board card is dealt.
    """
    r1, r2 = sorted([hole[0][0], hole[1][0]], key=lambda r: -_RANK_VALUES[r])
    paired = r1 == r2
    suited = hole[0][1] == hole[1][1]
    if paired:
        category = "ONE_PAIR"
        # Pocket pair rank: AA = 1413 .. 22 = 200 (approximate, not used
        # for postflop comparison).
        rank_int = 200 + _RANK_VALUES[r1] * 100
        label_text = f"Pocket {r1}{r2}"
    else:
        category = "HIGH_CARD"
        rank_int = (
            _RANK_VALUES[r1] * 14 + _RANK_VALUES[r2] + (5 if suited else 0)
        )
        label_text = f"{r1}{r2}{'s' if suited else 'o'}"
    return HandRank(category=category, rank_int=rank_int, label_text=label_text)
