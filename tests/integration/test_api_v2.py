"""End-to-end API v2 test: ETL → parquet → DI override → HTTP queries."""

from __future__ import annotations

import zipfile
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from src.aggregation.sizing_histograms import compute_sizing_histograms
from src.aggregation.typology import classify_archetypes
from src.aggregation.villain_stats import compute_villain_stats
from src.api.v2 import deps
from src.api.v2.main import app
from src.context.extractor_v2 import dps_to_records, extract_decision_points
from src.indexing.build_indices_v2 import (
    rebuild_indices,
    write_dps_parquet_partitioned,
)
from src.parsers.pokerkit_adapter import load_phh

REPO_ROOT = Path(__file__).parents[2]
PHH_ZIP = REPO_ROOT / "dataset" / "phh_hands.zip"


@pytest.fixture(scope="module")
def populated_data(tmp_path_factory) -> tuple[Path, Path]:
    """Run the full ETL once and return (dps_dir, indices_dir)."""
    if not PHH_ZIP.exists():
        pytest.skip(f"{PHH_ZIP} not found")

    work = tmp_path_factory.mktemp("api_v2_data")
    phh_extract = work / "phh"
    with zipfile.ZipFile(PHH_ZIP) as zf:
        zf.extractall(phh_extract)
    phh_dir = phh_extract / "phh_hands"

    # Extract DPs
    all_dps = []
    for f in sorted(phh_dir.glob("*.phh")):
        try:
            all_dps.extend(extract_decision_points(load_phh(f)))
        except Exception:
            continue
    assert all_dps

    # Write parquet partitions
    dps_dir = work / "dps"
    write_dps_parquet_partitioned(all_dps, dps_dir)

    # Build FAISS indices
    indices_dir = work / "indices"
    rebuild_indices(dps_dir, indices_dir)

    # Compute aggregates and persist for the API
    df = pl.DataFrame(dps_to_records(all_dps))
    stats = classify_archetypes(compute_villain_stats(df))
    profiles_path = work / "villain_profiles.parquet"
    stats.write_parquet(profiles_path)
    sizing_path = work / "sizing_histograms.parquet"
    compute_sizing_histograms(df).write_parquet(sizing_path)

    return dps_dir, indices_dir, profiles_path, sizing_path


@pytest.fixture(scope="module")
def client(populated_data) -> TestClient:
    """TestClient with deps pointed at the populated tmp dirs."""
    dps_dir, indices_dir, profiles_path, sizing_path = populated_data
    deps.DPS_DIR = dps_dir
    deps.INDICES_DIR = indices_dir
    deps.PROFILES_PATH = profiles_path
    deps.SIZING_PATH = sizing_path
    deps.reset_caches()
    return TestClient(app)


@pytest.mark.integration
def test_root(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "SpinAnalyzer v2"


@pytest.mark.integration
def test_health(client: TestClient) -> None:
    r = client.get("/api/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["n_villains"] > 0
    assert body["n_decisions"] > 0


@pytest.mark.integration
def test_list_villains(client: TestClient) -> None:
    r = client.get("/api/v2/villains")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert {"name", "n_hands", "archetype"}.issubset(body["villains"][0].keys())


@pytest.mark.integration
def test_get_villain_404(client: TestClient) -> None:
    r = client.get("/api/v2/villains/__nonexistent__")
    assert r.status_code == 404


@pytest.mark.integration
def test_get_villain_profile(client: TestClient) -> None:
    # Pick a villain from the list endpoint
    villains = client.get("/api/v2/villains").json()["villains"]
    name = villains[0]["name"]
    r = client.get(f"/api/v2/villains/{name}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == name
    assert "vpip" in body


@pytest.mark.integration
def test_get_hand(client: TestClient, populated_data) -> None:
    dps_dir, *_ = populated_data
    # Read any one hand_id from parquet
    df = deps.load_dps()
    hand_id = df["hand_id"][0]
    r = client.get(f"/api/v2/hands/{hand_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["hand_id"] == hand_id
    assert len(body["decisions"]) > 0


@pytest.mark.integration
def test_get_decision(client: TestClient) -> None:
    df = deps.load_dps()
    decision_id = df["decision_id"][0]
    r = client.get(f"/api/v2/decisions/{decision_id}")
    assert r.status_code == 200
    assert r.json()["decision_id"] == decision_id


@pytest.mark.integration
def test_search_by_decision(client: TestClient) -> None:
    df = deps.load_dps()
    decision_id = df["decision_id"][0]
    r = client.post("/api/v2/search/by-decision",
                    json={"decision_id": decision_id, "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    # Self-match should be the closest result
    distances = [r["distance"] for r in body["results"]]
    assert min(distances) < 1e-3


@pytest.mark.integration
def test_search_by_action_path(client: TestClient) -> None:
    df = deps.load_dps()
    sample = df.filter(pl.col("action_path").is_not_null()).to_dicts()[0]
    r = client.post(
        "/api/v2/search/by-action-path",
        json={
            "villain_name": sample["villain_name"],
            "street": sample["street"],
            "action_path": sample["action_path"],
            "k": 50,
        },
    )
    assert r.status_code == 200
    body = r.json()
    # At least the seed DP itself should match
    assert body["total"] >= 1
    matched_ids = [d["decision_id"] for d in body["results"]]
    assert sample["decision_id"] in matched_ids


@pytest.mark.integration
def test_villain_sizing(client: TestClient) -> None:
    villains = client.get("/api/v2/villains").json()["villains"]
    # Find a villain with at least one bet
    for v in villains:
        r = client.get(f"/api/v2/villains/{v['name']}/sizing")
        assert r.status_code == 200
        body = r.json()
        assert body["villain"] == v["name"]
        if body["buckets"]:
            return
    pytest.skip("no villain with sizing data in fixture")


@pytest.mark.integration
def test_openapi_schema_loads(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "SpinAnalyzer v2 API"
    assert "/api/v2/villains" in schema["paths"]
    assert "/api/v2/search/by-decision" in schema["paths"]
