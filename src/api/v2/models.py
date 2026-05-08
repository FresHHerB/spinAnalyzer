"""Pydantic v2 request/response models for the API v2."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Health ────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "2.0.0"
    n_villains: int = 0
    n_decisions: int = 0


# ── Villains ──────────────────────────────────────────────────────────


class VillainSummary(BaseModel):
    """Compact summary card for the villain-list endpoint."""

    name: str
    n_hands: int
    n_decisions: int
    archetype: str | None = None
    vpip: float | None = None
    pfr: float | None = None


class VillainListResponse(BaseModel):
    total: int
    villains: list[VillainSummary]


class VillainProfile(BaseModel):
    """Full per-villain stats block (one row from villain_stats)."""

    model_config = ConfigDict(extra="allow")

    name: str
    n_hands: int
    n_decisions: int
    archetype: str | None = None
    vpip: float | None = None
    pfr: float | None = None
    threebet_pct: float | None = None
    cbet_flop_pct: float | None = None
    fold_to_cbet_pct: float | None = None
    donk_freq: float | None = None
    xr_freq: float | None = None
    sb_limp_pct: float | None = None
    showdown_pct: float | None = None
    avg_bet_pot_pct_flop: float | None = None
    avg_bet_pot_pct_turn: float | None = None
    avg_bet_pot_pct_river: float | None = None


class SizingBucket(BaseModel):
    street: str
    bucket: str
    count: int


class VillainSizingResponse(BaseModel):
    villain: str
    buckets: list[SizingBucket]


# ── Hands / Decisions ────────────────────────────────────────────────


class DecisionResponse(BaseModel):
    """Slimmed-down DP for API responses (drops verbose internal fields)."""

    decision_id: str
    hand_id: str
    villain_name: str
    street: str
    villain_position: str
    villain_action: str
    pot_bb: float
    eff_stack_bb: float
    spr: float | None = None
    board_cards: list[str]
    villain_hand: list[str] | None = None
    villain_hand_strength: str | None = None
    villain_made_specific: str | None = None
    villain_equity_vs_random: float | None = None
    intent: str | None = None
    line_tag: str | None = None
    action_path: str
    villain_bet_size_bb: float | None = None
    villain_bet_size_pot_pct: float | None = None
    went_to_showdown: bool = False
    villain_won: bool | None = None
    distance: float | None = Field(
        default=None, description="L2 distance from query (search results only)"
    )


class HandResponse(BaseModel):
    hand_id: str
    villain_name: str
    decisions: list[DecisionResponse]


# ── Search ────────────────────────────────────────────────────────────


class SearchByDecisionRequest(BaseModel):
    decision_id: str
    k: int = Field(default=20, ge=1, le=200)


class SearchByActionPathRequest(BaseModel):
    villain_name: str
    street: str  # preflop / flop / turn / river
    action_path: str
    k: int = Field(default=50, ge=1, le=500)


class SearchResponse(BaseModel):
    query: dict[str, Any]
    total: int
    results: list[DecisionResponse]
    search_time_ms: float
