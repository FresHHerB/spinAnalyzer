"""Tests for src/aggregation/typology.py."""

import polars as pl
import pytest

from src.aggregation.typology import classify_archetype_row, classify_archetypes


def _stats(**kwargs):
    base = {
        "n_hands": 50, "vpip": 30.0, "pfr": 20.0, "threebet_pct": 5.0,
        "cbet_flop_pct": 60.0, "sb_limp_pct": 5.0,
    }
    base.update(kwargs)
    return base


@pytest.mark.parametrize(
    "stats,expected",
    [
        (_stats(vpip=20, pfr=15), "Nit"),
        (_stats(vpip=40, pfr=30), "TAG"),
        (_stats(vpip=55, pfr=40), "LAG"),
        (_stats(vpip=75, pfr=60), "Maniac"),
        (_stats(vpip=80, pfr=15), "CallingStation"),
        (_stats(sb_limp_pct=40), "Fish"),
        (_stats(n_hands=2), "Unknown"),  # too small sample
    ],
)
def test_classify_archetype_row(stats: dict, expected: str) -> None:
    assert classify_archetype_row(stats) == expected


def test_classify_archetypes_appends_column() -> None:
    df = pl.DataFrame([
        {"villain_name": "A", "n_hands": 50, "vpip": 20.0, "pfr": 15.0,
         "threebet_pct": 4.0, "cbet_flop_pct": 50.0, "sb_limp_pct": 0.0},
        {"villain_name": "B", "n_hands": 50, "vpip": 75.0, "pfr": 60.0,
         "threebet_pct": 15.0, "cbet_flop_pct": 80.0, "sb_limp_pct": 0.0},
    ])
    out = classify_archetypes(df)
    assert "archetype" in out.columns
    res = {row["villain_name"]: row["archetype"] for row in out.to_dicts()}
    assert res == {"A": "Nit", "B": "Maniac"}


def test_empty_input() -> None:
    df = pl.DataFrame(schema={"villain_name": pl.Utf8})
    out = classify_archetypes(df)
    assert "archetype" in out.columns
    assert out.is_empty()
