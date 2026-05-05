# Radar Imobiliario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent Imoveis e Projetos / Radar Imobiliario module to Grao Invest.

**Architecture:** Backend stores real estate candidates in SQLAlchemy and exposes CRUD/list endpoints plus deterministic score/confidence/status calculations. Frontend adds a new navigation surface to create candidates, view score/confidence, pendencias and suggested next action.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, static browser UI in `services/api/static/app.js`.

---

### Task 1: Backend scoring service

**Files:**
- Create: `services/api/app/services/real_estate_radar.py`
- Test: `tests/unit/test_real_estate_radar.py`

- [ ] Write failing tests for score, confidence, pendencias and status.
- [ ] Run `python -m pytest tests/unit/test_real_estate_radar.py -q` and confirm import failure.
- [ ] Implement deterministic helpers: `build_candidate_analysis(payload)`.
- [ ] Run the unit test and confirm pass.

### Task 2: Persistence model and schemas

**Files:**
- Modify: `services/api/app/models.py`
- Modify: `services/api/app/schemas.py`
- Modify: `services/api/app/db.py`

- [ ] Add `RealEstateCandidate` model with JSON text fields for comparable/notes/pending output.
- [ ] Add create/update/response Pydantic schemas.
- [ ] Add SQLite startup migration for existing local DBs.

### Task 3: API endpoints

**Files:**
- Modify: `services/api/app/main.py`
- Test: `tests/e2e/test_real_estate_radar_api.py`

- [ ] Write failing API test for create/list/update/discard behavior.
- [ ] Add endpoints under `/api/real-estate/candidates`.
- [ ] Ensure current user scoping reuses existing auth-disabled anonymous user flow.
- [ ] Run API test and confirm pass.

### Task 4: Web UI module

**Files:**
- Modify: `services/api/static/app.js`
- Maybe modify: `services/api/static/index.html` cache version only if needed.

- [ ] Add nav item `Imoveis e Projetos`.
- [ ] Add Radar screen with create form, candidate list, score/confidence/status cards and pendencias.
- [ ] Use existing visual tokens/components in app.js; avoid backend schema drift.
- [ ] Smoke test in browser or via local HTTP endpoint.

### Task 5: Verification

**Files:**
- Run tests only, no broad refactor.

- [ ] Run `python -m pytest tests/unit/test_real_estate_radar.py tests/e2e/test_real_estate_radar_api.py -q`.
- [ ] Start local app with `python -m uvicorn app.main:app --app-dir services/api --reload`.
- [ ] Validate `/health`, create candidate, list candidate, and UI render.
- [ ] Report changed files and any known limitation.
