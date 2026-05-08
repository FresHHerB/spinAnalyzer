"""Bet-size histograms per (villain, street).

Buckets %pot sizes into 6 conventional ranges (matching v1's encoder
buckets). Returns counts per bucket.
"""

from __future__ import annotations

import polars as pl

# Same boundaries as src.vectorization.vectorizer._encode_bet_sizing
_BUCKET_LABELS = (
    "no_bet", "tiny_le33", "half_pot", "two_thirds", "pot", "overbet",
)


def _bucket(pct: float | None) -> str:
    if pct is None or pct <= 0:
        return _BUCKET_LABELS[0]
    if pct <= 33:
        return _BUCKET_LABELS[1]
    if pct <= 50:
        return _BUCKET_LABELS[2]
    if pct <= 75:
        return _BUCKET_LABELS[3]
    if pct <= 100:
        return _BUCKET_LABELS[4]
    return _BUCKET_LABELS[5]


def compute_sizing_histograms(dps_df: pl.DataFrame) -> pl.DataFrame:
    """Return one row per (villain_name, street, bucket) with counts.

    Only postflop bets/raises are histogrammed (preflop sizing is in
    bb-multiples and lives in `villain_stats.avg_bet_pot_pct_*` columns).
    """
    if dps_df.is_empty():
        return pl.DataFrame(schema={
            "villain_name": pl.Utf8, "street": pl.Utf8, "bucket": pl.Utf8,
            "count": pl.UInt32,
        })

    bets = dps_df.filter(
        pl.col("street").is_in(["flop", "turn", "river"])
        & pl.col("villain_action").is_in(["bet", "raise"])
    )
    if bets.is_empty():
        return pl.DataFrame(schema={
            "villain_name": pl.Utf8, "street": pl.Utf8, "bucket": pl.Utf8,
            "count": pl.UInt32,
        })

    bets = bets.with_columns(
        pl.col("villain_bet_size_pot_pct")
        .map_elements(_bucket, return_dtype=pl.Utf8)
        .alias("bucket")
    )
    return (
        bets.group_by(["villain_name", "street", "bucket"])
        .agg(pl.len().alias("count"))
        .sort(["villain_name", "street", "bucket"])
    )
