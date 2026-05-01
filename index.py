from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
API_ROOT = PROJECT_ROOT / "services" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATA_DIR", "/tmp/grao-invest-data")
os.environ.setdefault("APP_RUNTIME", "vercel")


def _safe_bootstrap_error(exc: Exception) -> str:
    message = f"{type(exc).__name__}: {exc}"
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        message = message.replace(database_url, "[DATABASE_URL]")
    return message


try:
    app = import_module("app.main").app
except Exception as bootstrap_exc:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    bootstrap_error = _safe_bootstrap_error(bootstrap_exc)
    app = FastAPI(
        title="Grao Invest bootstrap diagnostic",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "degraded",
            "phase": "bootstrap",
            "error": bootstrap_error,
        }

    @app.get("/{path:path}")
    def fallback(path: str) -> JSONResponse:
        payload: dict[str, Any] = {
            "status": "degraded",
            "phase": "bootstrap",
            "path": path,
            "error": bootstrap_error,
        }
        return JSONResponse(status_code=503, content=payload)
