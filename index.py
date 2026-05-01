from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
import json
from collections.abc import Awaitable, Callable

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
    bootstrap_error = _safe_bootstrap_error(bootstrap_exc)
    Receive = Callable[[], Awaitable[dict[str, object]]]
    Send = Callable[[dict[str, object]], Awaitable[None]]

    async def app(scope: dict[str, object], receive: Receive, send: Send) -> None:
        path = str(scope.get("path") or "/")
        status_code = 200 if path == "/health" else 503
        body = json.dumps(
            {
            "status": "degraded",
            "phase": "bootstrap",
                "path": path,
            "error": bootstrap_error,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
