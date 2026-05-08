"""SpinAnalyzer v2 FastAPI application.

Surface:
    GET  /api/v2/health
    GET  /api/v2/villains
    GET  /api/v2/villains/{name}
    GET  /api/v2/villains/{name}/stats
    GET  /api/v2/villains/{name}/sizing
    GET  /api/v2/hands/{hand_id}
    GET  /api/v2/decisions/{decision_id}
    POST /api/v2/search/by-decision
    POST /api/v2/search/by-action-path

The v2 API drops v1's `app_state` global anti-pattern in favor of
FastAPI Dependency Injection (`src.api.v2.deps`).
"""

from src.api.v2.main import app

__all__ = ["app"]
