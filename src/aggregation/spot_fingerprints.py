"""Spot fingerprinting + per-spot action distribution.

A "spot" is a deterministic hash over (street, position, board texture
class, SPR bucket, action_path). DPs sharing a fingerprint are in the
same situation up to the action point. The aggregator returns, for
each (villain, fingerprint), the distribution of actions taken — this
powers the frequency-only analytics surface.
"""

from __future__ import annotations

import hashlib

import polars as pl


def _spr_bucket(spr: float | None) -> str:
    if spr is None:
        return "unknown"
    if spr < 1:
        return "shallow"
    if spr < 4:
        return "low"
    if spr < 10:
        return "med"
    return "deep"


def _texture_class(texture: dict | None) -> str:
    if not texture:
        return "preflop"
    if texture.get("monotone"):
        return "monotone"
    if texture.get("paired"):
        return "paired"
    if texture.get("two_tone") and texture.get("connected"):
        return "ttone_connected"
    if texture.get("two_tone"):
        return "ttone_disco"
    if texture.get("connected"):
        return "rainbow_connected"
    return "rainbow_disco"


def _fingerprint(street: str, position: str, texture_class: str,
                 spr: str, action_path: str) -> str:
    s = f"{street}|{position}|{texture_class}|{spr}|{action_path}"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def compute_spot_fingerprints(dps_df: pl.DataFrame) -> pl.DataFrame:
    """For each DP, compute its fingerprint string (added as a new column)."""
    if dps_df.is_empty():
        return dps_df.with_columns(pl.lit(None).cast(pl.Utf8).alias("fingerprint"))

    rows = dps_df.to_dicts()
    fps: list[str] = []
    classes: list[str] = []
    sprs: list[str] = []
    for r in rows:
        tex = r.get("board_texture") or {}
        if hasattr(tex, "model_dump"):
            tex = tex.model_dump()
        elif not isinstance(tex, dict):
            tex = {}
        cls = _texture_class(tex)
        spr_b = _spr_bucket(r.get("spr"))
        fp = _fingerprint(
            street=r.get("street", ""),
            position=r.get("villain_position", ""),
            texture_class=cls,
            spr=spr_b,
            action_path=r.get("action_path", ""),
        )
        fps.append(fp)
        classes.append(cls)
        sprs.append(spr_b)
    return dps_df.with_columns(
        pl.Series("fingerprint", fps),
        pl.Series("texture_class", classes),
        pl.Series("spr_bucket", sprs),
    )


def aggregate_by_fingerprint(dps_df: pl.DataFrame) -> pl.DataFrame:
    """Action distribution per (villain, fingerprint).

    Returns one row per (villain_name, fingerprint) with action counts
    pivoted into columns: count_check, count_call, count_bet, etc.
    """
    if dps_df.is_empty():
        return pl.DataFrame(schema={
            "villain_name": pl.Utf8, "fingerprint": pl.Utf8, "n": pl.UInt32,
        })

    if "fingerprint" not in dps_df.columns:
        dps_df = compute_spot_fingerprints(dps_df)

    counts = (
        dps_df.group_by(["villain_name", "fingerprint", "villain_action"])
        .agg(pl.len().alias("count"))
    )
    pivot = counts.pivot(values="count", index=["villain_name", "fingerprint"], on="villain_action")
    # Fill nulls with 0 and add a total `n` column.
    action_cols = [c for c in pivot.columns if c not in ("villain_name", "fingerprint")]
    pivot = pivot.with_columns([pl.col(c).fill_null(0) for c in action_cols])
    pivot = pivot.with_columns(
        pl.sum_horizontal(action_cols).alias("n")
    )
    # Rename action columns to count_<action>
    rename_map = {c: f"count_{c}" for c in action_cols}
    return pivot.rename(rename_map)
