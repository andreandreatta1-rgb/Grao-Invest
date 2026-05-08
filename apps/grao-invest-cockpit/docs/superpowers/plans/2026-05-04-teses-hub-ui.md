# Teses Hub UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change `Teses` from a giant table-first screen into a decision hub that summarizes the thesis universe first and opens the complete archive only when requested.

**Architecture:** Keep the existing `src/screens/Teses.jsx` data normalization and detail drawer. Add a local tab state (`overview`, `open`, `imoveis`, `historico`) and lightweight presentational sections in the same file to avoid a risky broad refactor while the screen is still evolving.

**Tech Stack:** React 18, inline styles, existing `Badge`, `KPICard`, `PatrickJane`, `C`, `mono`, Vitest + Testing Library.

---

### Task 1: Red Test For Hub Default

**Files:**
- Modify: `src/__tests__/tesesHub.test.jsx`

- [x] Add a test rendering `Teses` with mixed B3, Cripto, Imóveis and historical rows.
- [x] Assert the default screen shows `Visão geral das teses`, `Fila de atenção`, `Teses vivas`, and `Arquivo histórico`.
- [x] Assert the complete table `data-testid="teses-table"` is not rendered by default.
- [x] Assert clicking `Abrir arquivo completo` renders `Lista de teses` and `teses-table`.

### Task 2: Implement Hub Sections

**Files:**
- Modify: `src/screens/Teses.jsx`

- [x] Add `view` state defaulting to `overview`.
- [x] Add summary helpers for counts, attention rows, active rows, and front summaries.
- [x] Add compact components: `ViewTab`, `SummaryCard`, `FrontSummaryCard`, `AttentionQueue`, `CompactThesisList`, `ArchivePrompt`.
- [x] Render the existing full table only in `historico`, and reuse row click behavior.

### Task 3: Preserve Specialized Views

**Files:**
- Modify: `src/screens/Teses.jsx`

- [x] Add tabs `Visão geral`, `Abertas`, `Imóveis`, `Histórico`.
- [x] `Abertas` shows active rows only.
- [x] `Imóveis` shows real-estate rows first and preserves detail drawer with `realEstateAnalysis`.
- [x] `Histórico` shows the complete table with existing filters and sticky columns.

### Task 4: Verify

**Files:**
- Test: `src/__tests__/tesesHub.test.jsx`
- Test: full suite

- [x] Run targeted test and confirm RED.
- [x] Implement code.
- [x] Run targeted test and confirm GREEN.
- [x] Run all tests.
- [x] Run Vite build.
- [x] Generate new prints for `Teses` overview, archive, and imóvel detail.
