# M4 Teses Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make thesis detail screens decision-specific for B3, Crypto, and Real Estate, while making data origin visible and preserving the summarized M3 entry flow.

**Architecture:** Keep `Teses.jsx` as the owning screen and add small front-specific detail sections inside it to avoid introducing a new data format. `App.jsx` passes current feed status into `Teses`, and the existing normalized `thesisRows` remains the source of truth.

**Tech Stack:** React 18, Vite, Vitest, Testing Library, inline styles with Grão tokens from `../components`.

---

### Task 1: M4 Behavioral Tests

**Files:**
- Create: `src/__tests__/tesesM4Experience.test.jsx`

- [ ] Write tests that open a B3 thesis and assert B3-specific detail sections: `Plano operacional B3`, `Entrada planejada`, `Alvo técnico`, `Stop do plano`, `Ciclo Halley`.
- [ ] Write tests that open a Crypto thesis and assert Crypto-specific detail sections: `Mesa cripto 24/7`, `Preço agora`, `Volatilidade`, `Liquidez`, `Janela do ciclo`.
- [ ] Write tests that render `feedStatus="live"` and assert the data origin panel shows `Origem dos dados`, `API real`, `/api/dashboard/summary/1`, and `thesis_open_operations`.
- [ ] Write a responsive test with `window.innerWidth = 760` and assert the detail drawer uses a mobile-friendly layout marker.
- [ ] Run `vitest run src/__tests__/tesesM4Experience.test.jsx` and verify the tests fail for missing M4 UI.

### Task 2: Front-Specific Detail UI

**Files:**
- Modify: `src/screens/Teses.jsx`

- [ ] Add helpers: `frontDetailAccent`, `marketJaneComment`, and `marketDetailMetrics`.
- [ ] Add `MarketThesisDossier` that branches between B3 and Crypto labels while reusing `DetailCell`, `KPICard`, `Badge`, `money`, and `pct`.
- [ ] Replace the generic non-real-estate drawer body with `MarketThesisDossier`.
- [ ] Keep `RealEstateDossier` unchanged except for allowing the shared data origin panel above it.
- [ ] Run the focused M4 test and verify the B3/Crypto assertions pass.

### Task 3: Data Origin Visibility

**Files:**
- Modify: `src/App.jsx`
- Modify: `src/screens/Teses.jsx`

- [ ] Pass `feedStatus={feedStatus}` from `App.jsx` into `Teses`.
- [ ] Add `DataOriginPanel` in `Teses.jsx` that uses `feedStatus`, `data.scientificSummary.lastUpdatedAt`, and fixed endpoint labels.
- [ ] Render a compact origin panel near the top of the `Teses` screen and inside the drawer context where it helps explain the selected thesis.
- [ ] Use only colors from `C` and numbers/dates with `mono`.
- [ ] Run the focused M4 test and verify data-origin assertions pass.

### Task 4: Responsive Detail Layout

**Files:**
- Modify: `src/screens/Teses.jsx`

- [ ] Use the existing `isNarrow` calculation to pass responsive state into `ThesisDrawer`.
- [ ] On narrow screens, set the drawer marker `data-testid="teses-detail-mobile"` and make grids use one column.
- [ ] Ensure badges and KPI values use nowrap/ellipsis where needed.
- [ ] Run the focused M4 test and verify responsive assertions pass.

### Task 5: Verification and Prints

**Files:**
- No production files.

- [ ] Run `vitest run src/__tests__/tesesM4Experience.test.jsx`.
- [ ] Run `vitest run`.
- [ ] Run `vite build`.
- [ ] Generate screenshots for B3, Crypto, Real Estate open, Real Estate discarded, and at least one normal-user resolution.
