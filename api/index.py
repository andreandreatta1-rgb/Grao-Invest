from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "services" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATA_DIR", "/tmp/grao-invest-data")
os.environ.setdefault("APP_RUNTIME", "vercel")

app = import_module("app.main").app
