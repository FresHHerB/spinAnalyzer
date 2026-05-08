"""Per-villain aggregate stats from a DP DataFrame.

Computes the canonical HUD stats:

    n_hands         — distinct hand_ids the villain appears in
    n_decisions     — total DPs for this villain
    vpip            — % of preflop hands where villain put money in voluntarily
                      (call/raise; not just BB-check)
    pfr             — % of preflop hands where villain raised
    threebet_pct    — % of facing-raise preflop spots where villain re-raised
    cbet_flop_pct   — % of flop spots where villain (as PF aggressor) bet
    fold_to_cbet_pct— % of facing-flop-cbet spots where villain folded
    donk_freq       — % of postflop spots where villain led OOP
    xr_freq         — % of postflop spots where villain check-raised
    avg_bet_pot_pct_flop / turn / river
    sb_limp_pct     — % of preflop hands where villain (SB) limped
    showdown_pct    — % of hands that reached showdown for this villain
"""

from __future__ import annotations

import polars as pl

# Subset of DP fields the aggregator reads. Keeping this tight makes it
# robust to schema additions in dp_schema.
_REQUIRED_COLS = {
    "villain_name",
    "hand_id",
    "street",
    "villain_action",
    "villain_position",
    "villain_bet_size_pot_pct",
    "preflop_aggressor",
    "current_aggressor",
    "action_number_in_street",
    "line_tag",
    "went_to_showdown",
    "villain_won",
}


def _check_required(df: pl.DataFrame) -> None:
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"DP DataFrame missing columns: {sorted(missing)}")


def compute_villain_stats(dps_df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate one row per villain. Empty input → empty result."""
    if dps_df.is_empty():
        return pl.DataFrame(schema={"villain_name": pl.Utf8})

    _check_required(dps_df)

    # n_hands and n_decisions (overall)
    base = (
        dps_df.group_by("villain_name")
        .agg(
            pl.col("hand_id").n_unique().alias("n_hands"),
            pl.len().alias("n_decisions"),
        )
    )

    # ── Preflop stats: VPIP / PFR / 3bet / SB-limp ────────────────────
    pf = dps_df.filter(pl.col("street") == "preflop")
    if pf.is_empty():
        pf_stats = pl.DataFrame(schema={
            "villain_name": pl.Utf8, "vpip": pl.Float64, "pfr": pl.Float64,
            "threebet_pct": pl.Float64, "sb_limp_pct": pl.Float64,
        })
    else:
        # First preflop action per (villain, hand) defines vpip/pfr/limp
        first_pf = (
            pf.sort("action_number_in_street")
            .group_by(["villain_name", "hand_id"])
            .agg(pl.col("villain_action").first().alias("first_pf_action"),
                 pl.col("villain_position").first().alias("first_pf_pos"))
        )
        pf_stats = (
            first_pf.group_by("villain_name")
            .agg(
                (pl.col("first_pf_action").is_in(["call", "raise", "all_in", "allin"]).mean() * 100).alias("vpip"),
                (pl.col("first_pf_action").is_in(["raise", "all_in", "allin"]).mean() * 100).alias("pfr"),
                (((pl.col("first_pf_action") == "call") & (pl.col("first_pf_pos").is_in(["BTN", "SB"]))).mean() * 100).alias("sb_limp_pct"),
            )
        )

        # 3bet: villain raises after a previous preflop raise in the same hand.
        # Approximation: a DP whose action is `raise` AND whose
        # current_aggressor == 'hero' AND villain is the actor AND
        # action_number_in_street > 0.
        threebet_facing = (
            pf.filter(pl.col("current_aggressor") == "hero")
            .group_by("villain_name")
            .agg(pl.len().alias("n_facing_raise"),
                 (pl.col("villain_action").is_in(["raise", "all_in", "allin"]).sum()).alias("n_3bet"))
            .with_columns(
                (pl.col("n_3bet") / pl.col("n_facing_raise") * 100).alias("threebet_pct")
            )
            .select(["villain_name", "threebet_pct"])
        )
        pf_stats = pf_stats.join(threebet_facing, on="villain_name", how="left")

    # ── Cbet stats (flop) ─────────────────────────────────────────────
    flop = dps_df.filter(pl.col("street") == "flop")
    if flop.is_empty():
        cbet_stats = pl.DataFrame(schema={
            "villain_name": pl.Utf8, "cbet_flop_pct": pl.Float64,
            "fold_to_cbet_pct": pl.Float64, "donk_freq": pl.Float64,
            "xr_freq": pl.Float64,
        })
    else:
        # Cbet: villain is PF aggressor AND first to act on flop AND bets
        cbet_opp = flop.filter(
            (pl.col("preflop_aggressor") == "villain")
            & (pl.col("action_number_in_street") == 0)
        )
        cbet_made = cbet_opp.filter(pl.col("villain_action").is_in(["bet", "raise"]))
        cbet_stats_partial = (
            pl.concat(
                [
                    cbet_opp.group_by("villain_name").agg(pl.len().alias("n_cbet_opp")),
                    cbet_made.group_by("villain_name").agg(pl.len().alias("n_cbet_made")),
                ],
                how="align",
            )
            .with_columns(
                pl.col("n_cbet_opp").fill_null(0),
                pl.col("n_cbet_made").fill_null(0),
            )
            .with_columns(
                pl.when(pl.col("n_cbet_opp") > 0)
                .then(pl.col("n_cbet_made") / pl.col("n_cbet_opp") * 100)
                .otherwise(None)
                .alias("cbet_flop_pct")
            )
            .select(["villain_name", "cbet_flop_pct"])
        )

        # Fold-to-cbet: villain faces a flop cbet (line_tag=='cbet' on
        # the prior step would imply this). Approximation: villain is
        # NOT the PF aggressor AND faces a bet on flop (action_number > 0
        # AND current_aggressor == 'hero').
        fold_to_cbet_opp = flop.filter(
            (pl.col("preflop_aggressor") == "hero")
            & (pl.col("action_number_in_street") > 0)
            & (pl.col("current_aggressor") == "hero")
        )
        fold_to_cbet_made = fold_to_cbet_opp.filter(pl.col("villain_action") == "fold")
        ftc_stats = (
            pl.concat(
                [
                    fold_to_cbet_opp.group_by("villain_name").agg(pl.len().alias("n_ftc_opp")),
                    fold_to_cbet_made.group_by("villain_name").agg(pl.len().alias("n_ftc_made")),
                ],
                how="align",
            )
            .with_columns(
                pl.col("n_ftc_opp").fill_null(0),
                pl.col("n_ftc_made").fill_null(0),
            )
            .with_columns(
                pl.when(pl.col("n_ftc_opp") > 0)
                .then(pl.col("n_ftc_made") / pl.col("n_ftc_opp") * 100)
                .otherwise(None)
                .alias("fold_to_cbet_pct")
            )
            .select(["villain_name", "fold_to_cbet_pct"])
        )

        # Donk freq: villain leads OOP postflop with bet (line_tag='donk')
        donk_stats = (
            dps_df.filter(pl.col("street") != "preflop")
            .group_by("villain_name")
            .agg(
                ((pl.col("line_tag") == "donk").mean() * 100).alias("donk_freq"),
                ((pl.col("line_tag") == "xr").mean() * 100).alias("xr_freq"),
            )
        )

        cbet_stats = cbet_stats_partial.join(ftc_stats, on="villain_name", how="full", coalesce=True).join(
            donk_stats, on="villain_name", how="full", coalesce=True
        )

    # ── Avg bet sizing per street ─────────────────────────────────────
    bet_rows = dps_df.filter(
        pl.col("villain_action").is_in(["bet", "raise"])
        & pl.col("villain_bet_size_pot_pct").is_not_null()
    )
    if bet_rows.is_empty():
        sizing = base.select("villain_name").with_columns(
            pl.lit(None).cast(pl.Float64).alias("avg_bet_pot_pct_flop"),
            pl.lit(None).cast(pl.Float64).alias("avg_bet_pot_pct_turn"),
            pl.lit(None).cast(pl.Float64).alias("avg_bet_pot_pct_river"),
        )
    else:
        sizing = (
            bet_rows.group_by(["villain_name", "street"])
            .agg(pl.col("villain_bet_size_pot_pct").mean().alias("avg_pct"))
            .pivot(values="avg_pct", index="villain_name", on="street")
        )
        # Pivot only creates columns for streets that actually appear.
        # Add the missing ones as nulls and rename present ones.
        for street in ("flop", "turn", "river"):
            target = f"avg_bet_pot_pct_{street}"
            if street in sizing.columns:
                sizing = sizing.rename({street: target})
            elif target not in sizing.columns:
                sizing = sizing.with_columns(
                    pl.lit(None).cast(pl.Float64).alias(target)
                )
        # Drop any extraneous street columns (e.g. preflop bets)
        keep = ["villain_name", "avg_bet_pot_pct_flop", "avg_bet_pot_pct_turn", "avg_bet_pot_pct_river"]
        sizing = sizing.select([c for c in keep if c in sizing.columns])

    # ── Showdown rate ─────────────────────────────────────────────────
    showdown = (
        dps_df.group_by("villain_name")
        .agg(
            (pl.col("went_to_showdown").mean() * 100).alias("showdown_pct"),
        )
    )

    # ── Join all blocks ───────────────────────────────────────────────
    out = base
    for piece in (pf_stats, cbet_stats, sizing, showdown):
        if not piece.is_empty():
            out = out.join(piece, on="villain_name", how="left")
    return out
