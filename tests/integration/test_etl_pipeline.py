"""End-to-end ETL pipeline test.

Drives `run_full_pipeline` against a small XML batch (faster than
unzipping the full PHH archive). Verifies that all artefacts land on
disk and the API picks them up.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.v2 import deps
from src.api.v2.main import app
from src.services.etl_pipeline import run_full_pipeline

REPO_ROOT = Path(__file__).parents[2]
RAW_XML_DIR = REPO_ROOT / "dataset" / "original_hands" / "final"


@pytest.fixture(scope="module")
def pipeline_paths(tmp_path_factory) -> dict[str, Path]:
    if not RAW_XML_DIR.exists():
        pytest.skip(f"{RAW_XML_DIR} not found")

    work = tmp_path_factory.mktemp("etl")
    paths = {
        "phh": work / "phh",
        "dps": work / "dps",
        "indices": work / "indices",
        "profiles": work / "villain_profiles.parquet",
        "sizing": work / "sizing_histograms.parquet",
    }

    # Process 50 XMLs (≈ 50 sessions × 17 games × HU filter ≈ 400 PHHs)
    inputs = sorted(RAW_XML_DIR.glob("*.xml"))[:50]
    summary = run_full_pipeline(
        inputs,
        phh_dir=paths["phh"],
        dps_dir=paths["dps"],
        indices_dir=paths["indices"],
        profiles_path=paths["profiles"],
        sizing_path=paths["sizing"],
        job_id=None,  # no progress events for this test
    )
    paths["summary"] = summary  # type: ignore[assignment]
    return paths


@pytest.mark.integration
def test_pipeline_summary_shape(pipeline_paths: dict) -> None:
    s = pipeline_paths["summary"]
    assert s["n_input_files"] == 50
    assert s["n_phhs"] > 0
    assert s["n_dps"] > 0
    assert s["n_villains"] > 0
    assert s["indices"]


@pytest.mark.integration
def test_pipeline_artefacts_on_disk(pipeline_paths: dict) -> None:
    assert pipeline_paths["dps"].is_dir()
    assert any(pipeline_paths["dps"].glob("villain_name=*"))
    assert pipeline_paths["profiles"].exists()
    assert pipeline_paths["sizing"].exists()
    # FAISS indices: at least one per villain
    faiss_files = list(pipeline_paths["indices"].glob("*.faiss"))
    assert faiss_files


@pytest.mark.integration
def test_api_picks_up_pipeline_output(pipeline_paths: dict) -> None:
    """After the pipeline runs, the API should serve the data."""
    deps.DPS_DIR = pipeline_paths["dps"]
    deps.INDICES_DIR = pipeline_paths["indices"]
    deps.PROFILES_PATH = pipeline_paths["profiles"]
    deps.SIZING_PATH = pipeline_paths["sizing"]
    deps.reset_caches()

    client = TestClient(app)
    r = client.get("/api/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["n_villains"] > 0

    # OpenAPI now exposes upload + jobs routes
    schema = client.get("/openapi.json").json()
    assert "/api/v2/upload" in schema["paths"]
    assert "/api/v2/jobs/{job_id}" in schema["paths"]


@pytest.mark.integration
def test_progress_events_published(monkeypatch) -> None:
    """When job_id is set, each stage emits a progress event."""
    if not RAW_XML_DIR.exists():
        pytest.skip(f"{RAW_XML_DIR} not found")

    from src.services import cache

    captured: list[dict] = []

    def fake_publish(job_id: str, event: dict) -> int:
        captured.append({"job_id": job_id, **event})
        return 1

    monkeypatch.setattr(cache, "publish_progress", fake_publish)
    # Also patch the symbol re-imported into etl_pipeline
    import src.services.etl_pipeline as etl
    monkeypatch.setattr(etl, "publish_progress", fake_publish)

    inputs = sorted(RAW_XML_DIR.glob("*.xml"))[:5]

    import tempfile
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        run_full_pipeline(
            inputs,
            phh_dir=td / "phh",
            dps_dir=td / "dps",
            indices_dir=td / "indices",
            profiles_path=td / "profiles.parquet",
            sizing_path=td / "sizing.parquet",
            job_id="test-job",
        )

    stages = [e["stage"] for e in captured]
    assert "pipeline_start" in stages
    assert "parse_done" in stages
    assert "extract_done" in stages
    assert "write_dps_done" in stages
    assert "indices_done" in stages
    assert "pipeline_done" in stages
    assert all(e["job_id"] == "test-job" for e in captured)
