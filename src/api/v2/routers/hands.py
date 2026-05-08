"""Hand endpoint: get all DPs for a hand_id."""

from __future__ import annotations

import polars as pl
from fastapi import APIRouter, HTTPException

from src.api.v2 import deps
from src.api.v2.models import DecisionResponse, HandResponse

router = APIRouter(prefix="/hands", tags=["hands"])


def _row_to_decision(r: dict, distance: float | None = None) -> DecisionResponse:
    """Map a parquet row dict to a DecisionResponse, handling nested blocks."""
    return DecisionResponse(
        decision_id=r["decision_id"],
        hand_id=r["hand_id"],
        villain_name=r["villain_name"],
        street=r["street"],
        villain_position=r["villain_position"],
        villain_action=r["villain_action"],
        pot_bb=float(r["pot_bb"]),
        eff_stack_bb=float(r["eff_stack_bb"]),
        spr=r.get("spr"),
        board_cards=list(r.get("board_cards") or []),
        villain_hand=list(r["villain_hand"]) if r.get("villain_hand") else None,
        villain_hand_strength=r.get("villain_hand_strength"),
        villain_made_specific=r.get("villain_made_specific"),
        villain_equity_vs_random=r.get("villain_equity_vs_random"),
        intent=r.get("intent"),
        line_tag=r.get("line_tag"),
        action_path=r.get("action_path") or "",
        villain_bet_size_bb=r.get("villain_bet_size_bb"),
        villain_bet_size_pot_pct=r.get("villain_bet_size_pot_pct"),
        went_to_showdown=bool(r.get("went_to_showdown") or False),
        villain_won=r.get("villain_won"),
        distance=distance,
    )


@router.get("/{hand_id}", response_model=HandResponse)
def get_hand(hand_id: str) -> HandResponse:
    df = deps.load_dps()
    if df.is_empty():
        raise HTTPException(404, f"hand {hand_id!r} not found (no DPs loaded)")
    sub = df.filter(pl.col("hand_id") == hand_id).sort("step_idx")
    if sub.is_empty():
        raise HTTPException(404, f"hand {hand_id!r} not found")
    rows = sub.to_dicts()
    villain = rows[0]["villain_name"]
    return HandResponse(
        hand_id=hand_id,
        villain_name=villain,
        decisions=[_row_to_decision(r) for r in rows],
    )
