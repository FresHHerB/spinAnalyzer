"""Search endpoints: by-decision (FAISS) and by-action-path (filter)."""

from __future__ import annotations

import time

import numpy as np
import polars as pl
from fastapi import APIRouter, HTTPException

from src.api.v2 import deps
from src.api.v2.models import (
    DecisionResponse,
    SearchByActionPathRequest,
    SearchByDecisionRequest,
    SearchBySpotRequest,
    SearchResponse,
)
from src.api.v2.routers.hands import _row_to_decision
from src.context.dp_schema import BoardTexture, DecisionPoint
from src.vectorization.vectorizer_v2 import vectorize_dp

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/by-decision", response_model=SearchResponse)
def search_by_decision(req: SearchByDecisionRequest) -> SearchResponse:
    """k-NN search around the vector for the given decision_id."""
    start = time.perf_counter()
    df = deps.load_dps()
    if df.is_empty():
        raise HTTPException(404, "no DPs loaded")
    sub = df.filter(pl.col("decision_id") == req.decision_id)
    if sub.is_empty():
        raise HTTPException(404, f"decision {req.decision_id!r} not found")

    row = sub.to_dicts()[0]
    villain = row["villain_name"]
    dp = DecisionPoint.model_validate(row)
    query_vec = vectorize_dp(dp).astype(np.float32)

    builder = deps.get_index_builder()
    try:
        distances, _indices, decision_ids = builder.search(
            villain_name=villain, query_vector=query_vec, k=req.k,
        )
    except FileNotFoundError:
        raise HTTPException(404, f"no FAISS index for villain {villain!r}")

    # Look up the result rows in the same villain partition
    villain_df = df.filter(pl.col("villain_name") == villain)
    results: list[DecisionResponse] = []
    for dist, did in zip(distances.tolist(), decision_ids):
        match = villain_df.filter(pl.col("decision_id") == did)
        if match.is_empty():
            continue
        results.append(_row_to_decision(match.to_dicts()[0], distance=float(dist)))

    return SearchResponse(
        query={
            "decision_id": req.decision_id,
            "villain_name": villain,
            "k": req.k,
        },
        total=len(results),
        results=results,
        search_time_ms=(time.perf_counter() - start) * 1000,
    )


def _synthetic_dp(req: SearchBySpotRequest) -> DecisionPoint:
    """Build a synthetic DecisionPoint from picker fields for vectorization.

    Only fields the v1 encoders read need to be populated; everything
    else uses schema defaults.
    """
    pot = max(req.pot_bb, 0.1)
    spr = req.eff_stack_bb / pot if pot > 0 else None

    # Board texture is derived per-board on the fly (best-effort).
    suits = [c[1] for c in req.board_cards if len(c) == 2]
    ranks = [c[0] for c in req.board_cards if len(c) == 2]
    texture = BoardTexture(
        monotone=(len(set(suits)) == 1 and len(suits) >= 3),
        two_tone=(len(set(suits)) == 2 and len(suits) == 3),
        rainbow=(len(set(suits)) == 3 and len(suits) == 3),
        paired=(len(ranks) != len(set(ranks))),
    )

    return DecisionPoint(
        decision_id="__synthetic__",
        hand_id="__synthetic__",
        villain_name=req.villain_name,
        hero_name="hero",
        step_idx=0,
        street=req.street,
        action_number_in_street=0,
        pot_bb=pot,
        eff_stack_bb=req.eff_stack_bb,
        spr=spr,
        villain_position=req.villain_position,
        hero_position="IP" if req.villain_position == "OOP" else "OOP",
        action_path="",
        preflop_aggressor=req.aggressor,
        current_aggressor=req.aggressor,
        board_cards=req.board_cards,
        board_texture=texture,
        villain_hand_strength=req.villain_hand_strength,
        villain_action="bet",
        villain_bet_size_pot_pct=req.bet_size_pot_pct,
    )


@router.post("/by-spot-builder", response_model=SearchResponse)
def search_by_spot_builder(req: SearchBySpotRequest) -> SearchResponse:
    """Mode A: build a synthetic DP vector from picker fields and run k-NN."""
    start = time.perf_counter()
    df = deps.load_dps()
    if df.is_empty():
        raise HTTPException(404, "no DPs loaded")

    villain_df = df.filter(pl.col("villain_name") == req.villain_name)
    if villain_df.is_empty():
        raise HTTPException(404, f"villain {req.villain_name!r} not found")

    synthetic = _synthetic_dp(req)
    query_vec = vectorize_dp(synthetic).astype(np.float32)

    builder = deps.get_index_builder()
    try:
        distances, _indices, decision_ids = builder.search(
            villain_name=req.villain_name, query_vector=query_vec, k=req.k,
        )
    except FileNotFoundError:
        raise HTTPException(404, f"no FAISS index for villain {req.villain_name!r}")

    results: list[DecisionResponse] = []
    for dist, did in zip(distances.tolist(), decision_ids):
        match = villain_df.filter(pl.col("decision_id") == did)
        if match.is_empty():
            continue
        results.append(_row_to_decision(match.to_dicts()[0], distance=float(dist)))

    return SearchResponse(
        query=req.model_dump(),
        total=len(results),
        results=results,
        search_time_ms=(time.perf_counter() - start) * 1000,
    )


@router.post("/by-action-path", response_model=SearchResponse)
def search_by_action_path(req: SearchByActionPathRequest) -> SearchResponse:
    """Exact-match filter on (villain, street, action_path)."""
    start = time.perf_counter()
    df = deps.load_dps()
    if df.is_empty():
        raise HTTPException(404, "no DPs loaded")
    sub = (
        df.filter(pl.col("villain_name") == req.villain_name)
        .filter(pl.col("street") == req.street)
        .filter(pl.col("action_path") == req.action_path)
        .head(req.k)
    )
    rows = sub.to_dicts()
    return SearchResponse(
        query={
            "villain_name": req.villain_name,
            "street": req.street,
            "action_path": req.action_path,
            "k": req.k,
        },
        total=len(rows),
        results=[_row_to_decision(r) for r in rows],
        search_time_ms=(time.perf_counter() - start) * 1000,
    )
