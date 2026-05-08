# Teses Decision Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make the first Teses screen a summarized decision surface before the user reaches the full archive/table.

**Architecture:** Keep the existing `Teses.jsx` state model and views. Add a top-level `DecisionDesk` component in the overview view that computes action cards from existing normalized rows and calls the existing `switchView` flow.

**Tech Stack:** React, Vite, Vitest, Testing Library, inline styles with Grão tokens from `../components`.

---

### Task 1: Decision Desk Test

**Files:**
- Modify: `src/__tests__/tesesHub.test.jsx`

- [x] Add a failing test that asserts the default Teses view shows `Mesa de decisão`, `Decisões agora`, `Abrir radar imobiliário`, `Ver teses abertas`, and `Abrir lista completa`.
- [x] Assert the full table is not visible by default.
- [x] Click each major CTA and assert the existing views open.

### Task 2: Decision Desk UI

**Files:**
- Modify: `src/screens/Teses.jsx`

- [x] Add `DecisionActionCard`.
- [x] Add `DecisionDesk`.
- [x] Render `DecisionDesk` as the first block in `view === "overview"`.
- [x] Wire actions to `switchView("imoveis")`, `switchView("open")`, and `switchView("historico")`.

### Task 3: Verification

**Files:**
- No additional files.

- [x] Run focused Teses tests.
- [x] Run full Vitest suite.
- [x] Run Vite build.
- [x] Generate screenshots for the Teses M3 default overview and action state.
