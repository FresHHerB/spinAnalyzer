"""Villain endpoints: list, profile, stats, sizing."""

from __future__ import annotations

import polars as pl
from fastapi import APIRouter, HTTPException

from src.api.v2 import deps
from src.api.v2.models import (
    SizingBucket,
    VillainListResponse,
    VillainProfile,
    VillainSizingResponse,
    VillainSummary,
)

router = APIRouter(prefix="/villains", tags=["villains"])


@router.get("", response_model=VillainListResponse)
def list_villains() -> VillainListResponse:
    profiles = deps.load_villain_profiles()
    if profiles.is_empty():
        return VillainListResponse(total=0, villains=[])

    rows = profiles.to_dicts()
    villains = [
        VillainSummary(
            name=r["villain_name"],
            n_hands=int(r.get("n_hands") or 0),
            n_decisions=int(r.get("n_decisions") or 0),
            archetype=r.get("archetype"),
            vpip=r.get("vpip"),
            pfr=r.get("pfr"),
        )
        for r in rows
    ]
    villains.sort(key=lambda v: v.n_decisions, reverse=True)
    return VillainListResponse(total=len(villains), villains=villains)


@router.get("/{name}", response_model=VillainProfile)
def get_villain(name: str) -> VillainProfile:
    profiles = deps.load_villain_profiles()
    if profiles.is_empty():
        raise HTTPException(404, f"villain {name!r} not found (no profiles loaded)")
    row = profiles.filter(pl.col("villain_name") == name)
    if row.is_empty():
        raise HTTPException(404, f"villain {name!r} not found")
    d = row.to_dicts()[0]
    d["name"] = d.pop("villain_name")
    return VillainProfile(**d)


@router.get("/{name}/sizing", response_model=VillainSizingResponse)
def get_villain_sizing(name: str) -> VillainSizingResponse:
    sizing = deps.load_sizing_histograms()
    if sizing.is_empty():
        return VillainSizingResponse(villain=name, buckets=[])
    rows = sizing.filter(pl.col("villain_name") == name).to_dicts()
    return VillainSizingResponse(
        villain=name,
        buckets=[
            SizingBucket(street=r["street"], bucket=r["bucket"], count=int(r["count"]))
            for r in rows
        ],
    )
