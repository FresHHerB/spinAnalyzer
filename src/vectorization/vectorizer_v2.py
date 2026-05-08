"""Vectorizer v2: build 99-dim feature vectors from v2 DecisionPoints.

Reuses every `_encode_*` function from `src.vectorization.vectorizer`
(which are pure and correct) but feeds them the v2 schema fields,
including the previously-NULL hand_strength and draws blocks. No
encoder is rewritten — only the call sites change.

Block layout matches v1 exactly so existing FAISS HNSW indices remain
ABI-compatible:
    street(4) + position(4) + board_texture(10) + spr(5) +
    action_sequence(30) + aggressor(3) + pot_size(1) + stack_size(1) +
    draws(4) + board_cards(12) + hand_strength(9) +
    previous_hero_action(8) + bet_sizing(6) + action_count(2) = 99
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.context.dp_schema import DecisionPoint
from src.vectorization.vectorizer import FeatureConfig, Vectorizer


def _dp_to_v1_dict(dp: DecisionPoint) -> dict[str, Any]:
    """Adapt a v2 DecisionPoint to the field shape v1 encoders expect."""
    draws = (
        {
            "flush_draw": dp.villain_draws.nut_flush_draw or dp.villain_draws.weak_flush_draw,
            "oesd": dp.villain_draws.has_oesd,
            "gutshot": dp.villain_draws.has_gutshot,
            "combo_draw": dp.villain_draws.has_combo_draw,
        }
        if dp.villain_draws is not None
        else {}
    )
    return {
        "street": dp.street,
        "villain_position": dp.villain_position,
        "hero_position": dp.hero_position,
        "board_texture": dp.board_texture.model_dump(),
        "spr": dp.spr,
        "current_street_sequence": dp.current_street_sequence,
        "current_aggressor": dp.current_aggressor,
        "pot_bb": dp.pot_bb,
        "eff_stack_bb": dp.eff_stack_bb,
        "villain_draws": draws,
        "board_cards": dp.board_cards,
        "villain_hand_strength": dp.villain_hand_strength,
        "villain_bet_size_pot_pct": dp.villain_bet_size_pot_pct,
        "action_number_in_street": dp.action_number_in_street,
    }


def vectorize_dp(dp: DecisionPoint, vectorizer: Vectorizer | None = None) -> np.ndarray:
    """Vectorize a single v2 DecisionPoint into a 99-dim float32 array."""
    v = vectorizer or Vectorizer()
    return v.vectorize_decision_point(_dp_to_v1_dict(dp))


def vectorize_dps(dps: list[DecisionPoint], vectorizer: Vectorizer | None = None) -> np.ndarray:
    """Vectorize a batch of DPs. Shape: (n, 99)."""
    v = vectorizer or Vectorizer()
    arr = np.zeros((len(dps), v.config.total_dimensions), dtype=np.float32)
    for i, dp in enumerate(dps):
        arr[i] = v.vectorize_decision_point(_dp_to_v1_dict(dp))
    return arr


def expected_dimension() -> int:
    """The expected vector length (99)."""
    return FeatureConfig().total_dimensions
