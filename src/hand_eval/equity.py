"""Monte Carlo equity vs a random hand.

For each sample: deal opponent 2 cards from the deck (excluding hero
hole + board), complete the board with random cards, evaluate, score
1 for win / 0.5 tie / 0 loss. Average over samples.
"""

from __future__ import annotations

import random
from typing import Iterable

from src.hand_eval.evaluator import evaluate_hand

_SUITS = ("c", "d", "h", "s")
_RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
_FULL_DECK = tuple(r + s for r in _RANKS for s in _SUITS)


def _deck_minus(used: Iterable[str]) -> list[str]:
    used_set = set(used)
    return [c for c in _FULL_DECK if c not in used_set]


def equity_vs_random(
    hole: list[str],
    board: list[str],
    samples: int = 1000,
    seed: int | None = None,
) -> float:
    """Approximate equity of `hole` against an unknown random opponent
    on the given board.

    Args:
        hole: hero's 2 hole cards
        board: 0..5 board cards (will be randomly completed)
        samples: number of Monte Carlo iterations
        seed: optional RNG seed for reproducibility

    Returns:
        Equity in [0, 1].
    """
    if len(hole) != 2:
        raise ValueError(f"hole must have 2 cards, got {len(hole)}")
    if not 0 <= len(board) <= 5:
        raise ValueError(f"board must be 0..5 cards, got {len(board)}")
    if samples < 1:
        raise ValueError(f"samples must be ≥ 1, got {samples}")

    rng = random.Random(seed)
    deck_base = _deck_minus(hole + board)
    cards_to_complete = 5 - len(board)

    score = 0.0
    for _ in range(samples):
        # Sample opponent's 2 cards + remaining board cards
        sample = rng.sample(deck_base, 2 + cards_to_complete)
        opp = sample[:2]
        complete_board = list(board) + sample[2:]

        hero_rank = evaluate_hand(hole, complete_board)
        opp_rank = evaluate_hand(opp, complete_board)

        if hero_rank.rank_int > opp_rank.rank_int:
            score += 1.0
        elif hero_rank.rank_int == opp_rank.rank_int:
            score += 0.5

    return score / samples
