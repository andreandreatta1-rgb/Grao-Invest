# Grao Ops Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the B3/current thesis pipeline auditable end-to-end so stale feeds, broken scheduled tasks, seed drift, and zero-thesis publications are explicit instead of silent.

**Architecture:** Keep existing data-generation scripts intact, then add a thin operational guard around them. PowerShell owns Windows Task Scheduler installation/repair; Python owns data quality checks and JSON/Markdown health artifacts; the dashboard API exposes the latest health payload through the existing dashboard summary contract.

**Tech Stack:** PowerShell scheduled tasks, Python 3.14 stdlib, FastAPI/Pydantic dashboard schema, SQLite `market_ticks`, existing `run_b3_daily_job.py` and `run_current_thesis_by_front_job.py`.

---

### Task 1: Scheduler as Code

**Files:**
- Create: `scripts/install_grao_tasks.ps1`
- Create: `scripts/verify_grao_tasks.ps1`
- Create: `scripts/repair_grao_tasks.ps1`

- [ ] Implement install/update of expected GraoInvest scheduled tasks using `powershell.exe` as executable, quoted script paths in arguments, and `-WorkingDirectory` set to repo root.
- [ ] Implement verification that fails when `Execute` is a truncated path like `C:\Users\Andreatta\OneDrive`.
- [ ] Implement repair as install followed by verify.

### Task 2: Current Thesis Stage in B3 Cycle

**Files:**
- Modify: `scripts/run_b3_automation_cycle.ps1`

- [ ] Run daily B3 job before current thesis generation.
- [ ] Run `scripts/run_current_thesis_by_front_job.py` after B3/case study and before publish.
- [ ] Run `scripts/run_grao_ops_guard.py` after current thesis generation and before publish.
- [ ] Publish only after seed includes current thesis and ops health.

### Task 3: Ops Guard Artifact

**Files:**
- Create: `scripts/run_grao_ops_guard.py`

- [ ] Check repo/venv/db/script preflight.
- [ ] Check scheduler tasks by invoking `verify_grao_tasks.ps1` on Windows.
- [ ] Inspect `market_ticks` freshness by provider/front.
- [ ] Inspect `current_thesis_by_front_latest.json` and `dashboard_seed.json` consistency.
- [ ] Write `data/ops_health_latest.json` and `data/ops_health_latest.md`.
- [ ] Inject `ops_health` into `data/dashboard_seed.json` unless disabled.

### Task 4: Dashboard Contract

**Files:**
- Modify: `services/api/app/schemas.py`
- Modify: `services/api/app/main.py`

- [ ] Add optional `ops_health` to `DashboardResponse`.
- [ ] Load runtime/bundled `ops_health_latest.json` in dashboard summary.
- [ ] Return `ops_health` so the UI can explain stale/blocked pipeline state.

### Task 5: Verification

**Files:**
- Use existing tests plus targeted command checks.

- [ ] Run scheduler verify.
- [ ] Run ops guard check.
- [ ] Run focused backend tests for current thesis and dashboard contract.
- [ ] Report exact statuses and remaining operational blockers.
