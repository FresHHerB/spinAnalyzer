"""Decision endpoint: get a single DP by decision_id."""

from __future__ import annotations

import polars as pl
from fastapi import APIRouter, HTTPException

from src.api.v2 import deps
from src.api.v2.models import DecisionResponse
from src.api.v2.routers.hands import _row_to_decision

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(decision_id: str) -> DecisionResponse:
    df = deps.load_dps()
    if df.is_empty():
        raise HTTPException(404, f"decision {decision_id!r} not found (no DPs)")
    sub = df.filter(pl.col("decision_id") == decision_id)
    if sub.is_empty():
        raise HTTPException(404, f"decision {decision_id!r} not found")
    return _row_to_decision(sub.to_dicts()[0])
