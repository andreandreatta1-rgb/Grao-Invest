# Method To Thesis Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the end of the Method animation into a direct entry point for seeing one thesis through the method.

**Architecture:** Keep navigation state in `App.jsx`. `Metodo.jsx` exposes a callback CTA at the final act. `Teses.jsx` accepts an entry mode that opens the real-estate view and selects the first available real-estate thesis once rows are loaded.

**Tech Stack:** React, Vite, Vitest, Testing Library, inline styles with Grão tokens from `../components`.

---

### Task 1: Final Method CTA

**Files:**
- Modify: `src/__tests__/metodoAnimation.test.jsx`
- Modify: `src/screens/Metodo.jsx`

- [ ] **Step 1: Write the failing test**

Add a test that renders `Metodo` with `onOpenMethodExample`, advances the animation to act 05, clicks `Ver uma tese passando pelo método`, and expects the callback to run.

- [ ] **Step 2: Run the focused test**

Run: `node node_modules/vitest/vitest.mjs run src/__tests__/metodoAnimation.test.jsx`
Expected: FAIL because the CTA does not exist yet.

- [ ] **Step 3: Implement the minimal CTA**

Add an optional `onOpenMethodExample` prop to `Metodo`, render the CTA only when `isComplete`, and call the callback on click.

- [ ] **Step 4: Verify**

Run the focused test again and expect PASS.

### Task 2: App Navigation Bridge

**Files:**
- Modify: `src/App.jsx`
- Modify: `src/screens/Teses.jsx`
- Modify: `src/__tests__/navigationScreens.test.jsx`

- [ ] **Step 1: Write the failing integration test**

Render `App`, open Método, finish the animation, click the final CTA, and expect Teses to show `Radar imobiliário` plus `Ficha completa da tese`.

- [ ] **Step 2: Run the integration test**

Run: `node node_modules/vitest/vitest.mjs run src/__tests__/navigationScreens.test.jsx`
Expected: FAIL because `App` does not wire the callback yet.

- [ ] **Step 3: Implement navigation state**

In `App.jsx`, add `tesesEntryMode`, reset it on normal sidebar selection, and set it to `method-demo` when the Method CTA is clicked.

- [ ] **Step 4: Implement Teses entry behavior**

In `Teses.jsx`, accept `entryMode`. When `entryMode === "method-demo"`, initialize view to `imoveis` and auto-select the first real-estate row after rows are available.

- [ ] **Step 5: Verify**

Run focused tests, full Vitest suite, Vite build, and capture the Method final state plus resulting Teses screen.
