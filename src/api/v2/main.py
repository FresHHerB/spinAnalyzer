"""SpinAnalyzer v2 FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v2 import deps
from src.api.v2.models import HealthResponse
from src.api.v2.routers import decisions, hands, jobs, search, upload, villains
from src.config.settings import settings

app = FastAPI(
    title="SpinAnalyzer v2 API",
    description="Villain pattern search engine for HU/Spin&Go poker",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned routers
prefix = settings.api_v2_prefix
app.include_router(villains.router, prefix=prefix)
app.include_router(hands.router, prefix=prefix)
app.include_router(decisions.router, prefix=prefix)
app.include_router(search.router, prefix=prefix)
app.include_router(upload.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)


@app.get("/", tags=["general"])
def root() -> dict[str, str]:
    return {
        "name": "SpinAnalyzer v2",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get(f"{prefix}/health", response_model=HealthResponse, tags=["general"])
def health() -> HealthResponse:
    df = deps.load_dps()
    return HealthResponse(
        n_villains=df["villain_name"].n_unique() if not df.is_empty() else 0,
        n_decisions=df.height,
    )
