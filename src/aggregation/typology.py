"""Rules-based archetype classifier from villain_stats output.

Categories: Nit / TAG / LAG / Maniac / Reg / CallingStation / Fish.

Rules are intentionally conservative — Spin&Go HU samples are usually
small per villain, so we err on the side of broad categories rather
than fitting a tight cluster.
"""

from __future__ import annotations

import polars as pl


def classify_archetype_row(row: dict) -> str:
    """Apply the decision tree to a single villain_stats row."""
    vpip = row.get("vpip") or 0.0
    pfr = row.get("pfr") or 0.0
    threebet = row.get("threebet_pct") or 0.0
    cbet = row.get("cbet_flop_pct") or 0.0
    sb_limp = row.get("sb_limp_pct") or 0.0
    n_hands = row.get("n_hands") or 0

    # Insufficient sample → unknown
    if n_hands < 5:
        return "Unknown"

    # Fish: limps SB or extreme passive call station
    if sb_limp > 25.0:
        return "Fish"
    if vpip > 70.0 and pfr < 25.0:
        return "CallingStation"

    # Maniac: very loose-aggressive
    if vpip >= 60.0 and pfr >= 50.0:
        return "Maniac"

    # LAG: loose + aggressive (not extreme)
    if vpip >= 45.0 and pfr >= 30.0:
        return "LAG"

    # Nit: very tight
    if vpip < 35.0 and pfr < 25.0:
        return "Nit"

    # TAG: tight-aggressive (mid-range vpip + decent pfr/3bet/cbet)
    if 30.0 <= vpip < 55.0 and pfr >= 20.0:
        return "TAG"

    return "Reg"


def classify_archetypes(stats_df: pl.DataFrame) -> pl.DataFrame:
    """Append an `archetype` column to a villain_stats DataFrame."""
    if stats_df.is_empty():
        return stats_df.with_columns(pl.lit(None).cast(pl.Utf8).alias("archetype"))

    rows = stats_df.to_dicts()
    archetypes = [classify_archetype_row(r) for r in rows]
    return stats_df.with_columns(pl.Series("archetype", archetypes))
