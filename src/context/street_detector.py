"""Group action snapshots by street.

Thin wrapper over `src.parsers.pokerkit_adapter` that materialises
the per-street bucket structure required by the extractor.

The native PHH `street` field is the primary signal (every action row
in this repo's PHH files carries it), and the pokerkit adapter
cross-validates it against `state.street_index`. This module only
splits the already-validated stream into buckets keyed by street name.
"""

from __future__ import annotations

from src.parsers.pokerkit_adapter import PHHHand, StepSnapshot, replay_to_list

STREETS = ("preflop", "flop", "turn", "river")


def split_by_street(
    snapshots: list[StepSnapshot],
) -> dict[str, list[StepSnapshot]]:
    """Group an already-replayed snapshot list by street name."""
    buckets: dict[str, list[StepSnapshot]] = {s: [] for s in STREETS}
    for snap in snapshots:
        if snap.street in buckets:
            buckets[snap.street].append(snap)
    return buckets


def detect_streets(hand: PHHHand) -> dict[str, list[StepSnapshot]]:
    """Convenience: replay then split."""
    return split_by_street(replay_to_list(hand))
