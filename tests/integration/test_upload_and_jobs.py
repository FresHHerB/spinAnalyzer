"""POST /api/v2/upload + GET /api/v2/jobs/{id}.

Tests the **sync fallback path** of the upload router (when ARQ/Redis
is unavailable). The upload runs in-process via FastAPI BackgroundTasks
and the API surface still responds correctly.

Real ARQ + WebSocket streaming would need a live Redis and is left to
manual smoke-test in the deployment guide.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.v2 import deps
from src.api.v2.main import app

REPO_ROOT = Path(__file__).parents[2]
RAW_XML_FILE = REPO_ROOT / "dataset" / "original_hands" / "final" / "8384733544.xml"


@pytest.fixture
def empty_data_dirs(tmp_path, monkeypatch) -> dict:
    """Point all deps at empty tmp dirs so the upload populates them."""
    paths = {
        "dps": tmp_path / "dps",
        "indices": tmp_path / "indices",
        "profiles": tmp_path / "villain_profiles.parquet",
        "sizing": tmp_path / "sizing_histograms.parquet",
        "phh": tmp_path / "phh",
        "uploads": tmp_path / "uploads",
    }
    paths["dps"].mkdir(parents=True, exist_ok=True)
    paths["indices"].mkdir(parents=True, exist_ok=True)
    paths["phh"].mkdir(parents=True, exist_ok=True)
    paths["uploads"].mkdir(parents=True, exist_ok=True)

    deps.DPS_DIR = paths["dps"]
    deps.INDICES_DIR = paths["indices"]
    deps.PROFILES_PATH = paths["profiles"]
    deps.SIZING_PATH = paths["sizing"]
    deps.reset_caches()

    # Redirect upload + pipeline outputs to tmp dirs.
    # _upload_dir() reads settings.data_dir, which we patch below.

    # The pipeline reads `settings.phh_dir` etc. inside run_full_pipeline.
    # Patch the singleton attributes directly.
    from src.config.settings import settings as _settings
    monkeypatch.setattr(_settings, "phh_dir", paths["phh"])
    monkeypatch.setattr(_settings, "dps_dir", paths["dps"])
    monkeypatch.setattr(_settings, "indices_dir", paths["indices"])
    monkeypatch.setattr(_settings, "profiles_path", paths["profiles"])
    monkeypatch.setattr(_settings, "data_dir", tmp_path)

    return paths


@pytest.fixture
def force_sync_fallback(monkeypatch) -> None:
    """Patch _try_enqueue_arq to always return False so we exercise the
    BackgroundTasks fallback (no Redis required for this test)."""
    from src.api.v2.routers import upload

    async def _no_arq(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(upload, "_try_enqueue_arq", _no_arq)


@pytest.mark.integration
def test_upload_rejects_unsupported_extension(
    empty_data_dirs: dict, force_sync_fallback,
) -> None:
    client = TestClient(app)
    r = client.post(
        "/api/v2/upload",
        files=[("files", ("foo.exe", b"junk", "application/octet-stream"))],
    )
    assert r.status_code == 400
    assert "unsupported extension" in r.json()["detail"]


@pytest.mark.integration
def test_upload_no_files_returns_400(
    empty_data_dirs: dict, force_sync_fallback,
) -> None:
    client = TestClient(app)
    # FastAPI's File(...) rejects empty list at validation layer
    r = client.post("/api/v2/upload", files=[])
    assert r.status_code in (400, 422)


@pytest.mark.integration
def test_upload_xml_runs_pipeline_via_sync_fallback(
    empty_data_dirs: dict, force_sync_fallback,
) -> None:
    if not RAW_XML_FILE.exists():
        pytest.skip(f"{RAW_XML_FILE} not found")

    client = TestClient(app)
    with open(RAW_XML_FILE, "rb") as f:
        r = client.post(
            "/api/v2/upload",
            files=[("files", ("session.xml", f.read(), "application/xml"))],
        )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "sync"
    assert body["queued_files"] == ["session.xml"]
    assert body["job_id"]

    # TestClient runs BackgroundTasks synchronously after the response.
    # The pipeline should have produced parquet partitions + indices.
    deps.reset_caches()
    villains = client.get("/api/v2/villains").json()
    assert villains["total"] >= 1


@pytest.mark.integration
def test_jobs_endpoint_returns_unknown_when_arq_down(
    empty_data_dirs: dict, monkeypatch,
) -> None:
    """When ARQ/Redis is unreachable, GET /jobs/{id} returns status=unknown
    rather than 500."""
    client = TestClient(app)

    # Force the ARQ probe in the route to raise
    from src.api.v2.routers import jobs as jobs_module

    async def _raise(*_a, **_kw):
        raise RuntimeError("simulated arq down")

    # Replace the imported `Job` class to short-circuit
    monkeypatch.setattr("arq.jobs.Job.__init__", lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("arq down")))

    r = client.get("/api/v2/jobs/anything")
    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == "anything"
    assert body["status"] == "unknown"
