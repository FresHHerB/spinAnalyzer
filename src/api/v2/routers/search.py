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
    SearchResponse,
)
from src.api.v2.routers.hands import _row_to_decision
from src.context.dp_schema import DecisionPoint
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
