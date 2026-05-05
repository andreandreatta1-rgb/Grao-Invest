# Modern Frontend Rollout On Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the modern `apps/thesis-lab-view` UI from the existing backend project at `grao-invest.vercel.app` without breaking `/api`, cron routes, or health checks.

**Architecture:** Keep `apps/thesis-lab-view` as the source frontend, but publish a tracked build artifact inside the backend tree so Git-based Vercel deploys have the exact bundle available. Update FastAPI to serve known frontend assets directly and fall back to `index.html` for SPA routes, while leaving existing API routes untouched.

**Tech Stack:** FastAPI, Python, Vite build artifacts, pytest, TestClient, PowerShell build/sync command

---

### Task 1: Lock The Expected HTTP Behavior

**Files:**
- Create: `tests/e2e/test_modern_frontend_rollout.py`
- Modify: `tests/e2e/test_frontend_guardrails.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import re


def test_spa_routes_return_modern_shell(client):
    routes = ["/", "/teses", "/lab", "/decisoes", "/config", "/instalar"]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert '<div id="root"></div>' in response.text
        assert 'manifest.webmanifest' in response.text
        assert re.search(r'/assets/index-[^"]+\\.js', response.text)


def test_frontend_assets_are_served(client):
    index_response = client.get("/")
    asset_match = re.search(r'src="(?P<asset>/assets/index-[^"]+\\.js)"', index_response.text)
    assert asset_match is not None

    asset_response = client.get(asset_match.group("asset"))
    assert asset_response.status_code == 200
    assert "QueryClientProvider" not in asset_response.text

    manifest_response = client.get("/manifest.webmanifest")
    assert manifest_response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_modern_frontend_rollout.py -q`
Expected: FAIL because `/teses`, `/lab`, `/decisoes`, `/config`, `/instalar`, or bundle assets are not served by the backend shell yet.

- [ ] **Step 3: Update guardrail expectations for the new shell**

```python
def test_disclaimer_is_present_in_modern_shell_bundle() -> None:
    html = _html()
    assert '<div id="root"></div>' in html
    assert "manifest.webmanifest" in html
    assert "Grão Invest" in html
```

- [ ] **Step 4: Run the focused frontend guardrails**

Run: `pytest tests/e2e/test_modern_frontend_rollout.py tests/e2e/test_frontend_guardrails.py -q`
Expected: still FAIL until backend serving is implemented, but failures must point to missing modern shell behavior rather than test syntax errors.

### Task 2: Publish A Tracked Frontend Artifact For Backend Delivery

**Files:**
- Create: `scripts/sync_thesis_lab_frontend.ps1`
- Create: `services/api/frontend_dist/` (copied build output)
- Modify: `apps/thesis-lab-view/package.json`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_backend_frontend_dist_exists() -> None:
    dist_dir = Path(__file__).resolve().parents[2] / "services" / "api" / "frontend_dist"
    assert (dist_dir / "index.html").exists()
    assert (dist_dir / "manifest.webmanifest").exists()
    assert (dist_dir / "assets").is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_static_ui_shell.py -q`
Expected: FAIL because `services/api/frontend_dist` does not exist yet.

- [ ] **Step 3: Add a repeatable sync command and generate the tracked artifact**

```powershell
param(
  [string]$FrontendDir = "apps/thesis-lab-view",
  [string]$TargetDir = "services/api/frontend_dist"
)

Remove-Item -LiteralPath $TargetDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $TargetDir | Out-Null
Copy-Item -Path (Join-Path $FrontendDir "dist\\*") -Destination $TargetDir -Recurse -Force
```

- [ ] **Step 4: Run the focused artifact test**

Run: `pytest tests/unit/test_static_ui_shell.py -q`
Expected: PASS for the artifact existence expectations.

### Task 3: Serve The Modern Frontend Bundle Safely

**Files:**
- Modify: `services/api/app/main.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write the failing test**

```python
def test_api_routes_still_return_json_not_shell(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    api_response = client.get("/api/assistant/decisions")
    assert api_response.status_code == 200
    assert api_response.headers["content-type"].startswith("application/json")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_modern_frontend_rollout.py::test_api_routes_still_return_json_not_shell -q`
Expected: FAIL only if the frontend catch-all incorrectly swallows JSON routes or if the fixture cannot support the route yet.

- [ ] **Step 3: Implement minimal serving logic**

```python
frontend_dist_dir = Path(__file__).resolve().parents[3] / "services" / "api" / "frontend_dist"
frontend_shell_dir = frontend_dist_dir if (frontend_dist_dir / "index.html").exists() else static_dir


def _frontend_file(path: str) -> Path | None:
    candidate = (frontend_shell_dir / path.lstrip("/")).resolve()
    try:
        candidate.relative_to(frontend_shell_dir.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


@app.get("/{full_path:path}", include_in_schema=False)
def spa_shell(full_path: str) -> FileResponse:
    asset = _frontend_file(full_path)
    if asset is not None:
        return FileResponse(asset)
    return FileResponse(frontend_shell_dir / "index.html")
```

- [ ] **Step 4: Run the focused serving tests**

Run: `pytest tests/e2e/test_modern_frontend_rollout.py tests/e2e/test_frontend_guardrails.py -q`
Expected: PASS with `/health` and `/api/assistant/decisions` still returning JSON.

### Task 4: Verify End-To-End Before Any Deployment Claim

**Files:**
- Modify: `docs/frontend-rollout-safe-path.md`

- [ ] **Step 1: Build and sync the frontend artifact**

Run: `npm --prefix apps/thesis-lab-view run build`
Then: `powershell -ExecutionPolicy Bypass -File scripts/sync_thesis_lab_frontend.ps1`
Expected: `services/api/frontend_dist` refreshed with the latest Vite bundle.

- [ ] **Step 2: Run backend-facing verification**

Run: `pytest tests/unit/test_static_ui_shell.py tests/e2e/test_frontend_guardrails.py tests/e2e/test_modern_frontend_rollout.py -q`
Expected: PASS

- [ ] **Step 3: Run frontend verification**

Run: `npm --prefix apps/thesis-lab-view run test`
Then: `npm --prefix apps/thesis-lab-view run build`
Expected: PASS

- [ ] **Step 4: Document the ongoing update workflow**

```markdown
Whenever `apps/thesis-lab-view` changes, rebuild it and run `scripts/sync_thesis_lab_frontend.ps1` before deploying the backend project.
```
