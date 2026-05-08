# M5 Daily Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the Grão Invest cockpit for daily use by adding a laboratory health screen and a single local validation command.

**Architecture:** `App.jsx` keeps loading cockpit payloads and now records feed-level health metadata. A new `Saude.jsx` screen renders feed status, thesis counts, B3 freshness, data-quality checks, and the local validation checklist. A Node script runs tests, build, and writes a validation report from one `npm run validate:daily` command.

**Tech Stack:** React 18, Vite, Vitest, Testing Library, Node child_process, inline styles with Grão tokens from `../components`.

---

### Task 1: Health Screen Tests

**Files:**
- Create: `src/__tests__/healthScreen.test.jsx`

- [ ] Write a failing test that renders `App`, clicks `Saúde`, and expects `Saúde do Laboratório`, `API real`, `/api/dashboard/summary/1`, `thesis_open_operations`, and `npm run validate:daily`.
- [ ] Write a failing test for API failure that expects `Fallback ativo` and `Feed temporariamente indisponível`.
- [ ] Run `vitest run src/__tests__/healthScreen.test.jsx` and verify RED.

### Task 2: Validation Command Tests

**Files:**
- Create: `src/__tests__/validateDailyScript.test.js`

- [ ] Write a failing test that asserts `package.json` has `validate:daily`.
- [ ] Assert `scripts/validate-daily.mjs` exists and contains the test, build, and screenshot/report stages.
- [ ] Run `vitest run src/__tests__/validateDailyScript.test.js` and verify RED.

### Task 3: Implement App Feed Health

**Files:**
- Modify: `src/App.jsx`

- [ ] Add endpoint metadata for the three cockpit feeds.
- [ ] Store `feedHealth` in state.
- [ ] Set feed health to live/fallback per feed after `fetchCockpitPayloads`.
- [ ] Set all feeds to fallback when the fetch layer throws.

### Task 4: Implement Saúde Screen

**Files:**
- Create: `src/screens/Saude.jsx`
- Modify: `src/App.jsx`
- Modify: `src/components/Sidebar.jsx`

- [ ] Add the `Saude` screen and sidebar item.
- [ ] Render Patrick Jane reporting with daily-health language.
- [ ] Render KPICards for feed status, thesis rows, go-live count, and latest update.
- [ ] Render feed rows and data-quality checks.
- [ ] Render local checklist including `npm run validate:daily`.

### Task 5: Implement Daily Validation Script

**Files:**
- Create: `scripts/validate-daily.mjs`
- Modify: `package.json`

- [ ] Add `validate:daily` script to `package.json`.
- [ ] Run `npm test`.
- [ ] Run `npm run build`.
- [ ] Write `Validação Telas/daily-validation-report.json`.
- [ ] Include screenshot/report stage labels so it can be extended without changing the app.

### Task 6: Verification

**Files:**
- No production files.

- [ ] Run focused M5 tests.
- [ ] Run full Vitest suite.
- [ ] Run Vite build.
- [ ] Run `npm run validate:daily`.
- [ ] Generate `12-saude-m5.png` in the validation folder.
