# Cockpit Halley Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first React/PWA vertical slice of the Grão Invest Cockpit Halley, separating B3, Cripto and Imóveis while preserving the current Android/mobile beta.

**Architecture:** Create an isolated Vite React 18 JSX app in `apps/grao-invest-cockpit`. The app reads existing API payloads through a dedicated adapter, renders a compact executive cockpit with reusable inline-style components, and falls back to local seed data when a feed is unavailable. The existing `apps/grao-invest-mobile-web` and Android app remain untouched.

**Tech Stack:** React 18 JSX, Vite, Vitest, Testing Library, Recharts dependency available for future charts, 100% inline `style={}`, Sora + JetBrains Mono fonts, no Tailwind, no external CSS.

---

## Scope Check

This plan implements one vertical slice: Cockpit Halley as a standalone PWA candidate. It does not replace the deployed FastAPI UI, does not modify Android, does not add authentication, and does not change thesis generation jobs.

## File Structure

- `apps/grao-invest-cockpit/package.json`: isolated scripts and dependencies.
- `apps/grao-invest-cockpit/index.html`: UTF-8 Vite entry.
- `apps/grao-invest-cockpit/vite.config.js`: React/Vitest config.
- `apps/grao-invest-cockpit/src/App.jsx`: root shell and data lifecycle.
- `apps/grao-invest-cockpit/src/main.jsx`: React mount.
- `apps/grao-invest-cockpit/src/tokens.js`: single source for `C` and `mono`.
- `apps/grao-invest-cockpit/src/utils/formatters.js`: money, percent, integer, days and dates.
- `apps/grao-invest-cockpit/src/utils/text.js`: mojibake/accent cleanup for legacy JSON.
- `apps/grao-invest-cockpit/src/hooks/useFonts.js`: Sora + JetBrains Mono injection.
- `apps/grao-invest-cockpit/src/components/*.jsx`: Badge, KPICard, PatrickJane, ProgressBar, FrontCard, ThesisCard, LearningLoopCard.
- `apps/grao-invest-cockpit/src/data/*.js`: mock seed, API fetcher, Cockpit adapter.
- `apps/grao-invest-cockpit/src/screens/CockpitHalley.jsx`: screen composition.
- `apps/grao-invest-cockpit/src/__tests__/*.test.*`: unit and component tests.
- `apps/grao-invest-cockpit/README.md`: run and validation guide.

---

### Task 1: Scaffold The Isolated PWA

**Files:**
- Create: `apps/grao-invest-cockpit/package.json`
- Create: `apps/grao-invest-cockpit/index.html`
- Create: `apps/grao-invest-cockpit/vite.config.js`
- Create: `apps/grao-invest-cockpit/src/main.jsx`
- Create: `apps/grao-invest-cockpit/src/App.jsx`
- Test: `apps/grao-invest-cockpit/src/__tests__/app.smoke.test.jsx`

- [ ] **Step 1: Create package manifest**

Use this dependency shape. Keep React pinned to 18.2.0 and do not add Tailwind.

```json
{
  "name": "grao-invest-cockpit",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build",
    "preview": "vite preview --host 0.0.0.0",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "recharts": "latest",
    "lucide-react": "latest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "latest",
    "@testing-library/react": "latest",
    "@testing-library/user-event": "latest",
    "jsdom": "latest",
    "vitest": "latest"
  }
}
```

- [ ] **Step 2: Create UTF-8 HTML and Vite config**

`index.html` must include `<meta charset="UTF-8" />`, `lang="pt-BR"`, viewport, theme color `#070b14`, and title `Grão Invest — Cockpit Halley`.

`vite.config.js`:

```js
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", globals: true },
});
```

- [ ] **Step 3: Write failing smoke test**

```jsx
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App.jsx";

describe("App", () => {
  it("renders Cockpit Halley", () => {
    render(<App />);
    expect(screen.getByText("Cockpit Halley")).toBeInTheDocument();
  });
});
```

Run:

```powershell
cd apps/grao-invest-cockpit
npm install
npm test
```

Expected: FAIL until `App.jsx` exists.

- [ ] **Step 4: Create minimal entry**

`src/main.jsx` mounts `<App />` with `React.StrictMode`. `src/App.jsx` returns a minimal `<main><h1>Cockpit Halley</h1></main>`.

Run:

```powershell
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/grao-invest-cockpit
git commit -m "feat: scaffold cockpit halley pwa"
```

---

### Task 2: Tokens, Fonts, Formatters And Text Cleanup

**Files:**
- Create: `apps/grao-invest-cockpit/src/tokens.js`
- Create: `apps/grao-invest-cockpit/src/utils/formatters.js`
- Create: `apps/grao-invest-cockpit/src/utils/text.js`
- Create: `apps/grao-invest-cockpit/src/hooks/useFonts.js`
- Test: `apps/grao-invest-cockpit/src/__tests__/formatters.test.js`
- Test: `apps/grao-invest-cockpit/src/__tests__/text.test.js`

- [ ] **Step 1: Write formatter and text tests**

Tests must assert:

```js
expect(fmtMoney(42.3)).toBe("R$ 42,30");
expect(fmtMoney(null)).toBe("R$ --");
expect(fmtPct(3.14159)).toBe("+3,14%");
expect(fmtPct(-2)).toBe("-2,00%");
expect(fmtPct(undefined)).toBe("--%");
expect(fmtDays(4.91)).toBe("5 d");
expect(fmtDate("2026-04-27T12:00:00Z")).toBe("27/04/2026");
expect(cleanText("Ações, Operações, Imóveis, Hipótese")).toBe("Ações, Operações, Imóveis, Hipótese");
const brokenLegacyText = "Pr\\u00c3\\u00b3xima: exigir confirma\\u00c3\\u00a7\\u00c3\\u00a3o de volume";
expect(cleanText(brokenLegacyText)).toBe("Próxima: exigir confirmação de volume");
```

Run `npm test`. Expected: FAIL because helpers do not exist.

- [ ] **Step 2: Implement tokens**

Create `tokens.js` with the full AGENTS token object `C`, including `bg`, `panel`, `card`, `border`, `hover`, `line`, `faint`, `gold`, `teal`, `coral`, `amber`, `green`, `sky`, `purple`, `text`, `muted`, `dim`, and `mono = "'JetBrains Mono', 'Fira Code', monospace"`. Use `Object.freeze`.

- [ ] **Step 3: Implement helpers**

`formatters.js` exports `fmtMoney`, `fmtPct`, `fmtInteger`, `fmtDays`, `fmtDate`. No helper may return `NaN`, `undefined`, `null`, or unformatted raw numbers.

`text.js` exports `cleanText(value)` and replaces the common legacy mojibake sequences for á, â, ã, é, ê, í, ó, ô, õ, ú, ç, Ç, dash and en dash with correct characters.

`useFonts.js` injects:

```js
https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap
```

Run `npm test`. Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add apps/grao-invest-cockpit/src/tokens.js apps/grao-invest-cockpit/src/utils apps/grao-invest-cockpit/src/hooks apps/grao-invest-cockpit/src/__tests__/formatters.test.js apps/grao-invest-cockpit/src/__tests__/text.test.js
git commit -m "feat: add cockpit tokens and formatters"
```

---
### Task 3: Base Components

**Files:**
- Create: `apps/grao-invest-cockpit/src/components/Badge.jsx`
- Create: `apps/grao-invest-cockpit/src/components/KPICard.jsx`
- Create: `apps/grao-invest-cockpit/src/components/PatrickJane.jsx`
- Create: `apps/grao-invest-cockpit/src/components/ProgressBar.jsx`
- Create: `apps/grao-invest-cockpit/src/components/FrontCard.jsx`
- Create: `apps/grao-invest-cockpit/src/components/ThesisCard.jsx`
- Create: `apps/grao-invest-cockpit/src/components/LearningLoopCard.jsx`
- Test: `apps/grao-invest-cockpit/src/__tests__/components.test.jsx`

- [ ] **Step 1: Write component tests**

Tests must cover:

```jsx
render(<Badge label="Observando" type="info" />);
expect(screen.getByText("Observando")).toBeInTheDocument();

render(<PatrickJane state="reporting" message="O plano foi seguido. Aprendizado registrado." />);
expect(screen.getByText("Patrick Jane")).toBeInTheDocument();

render(<FrontCard front={{ id: "b3", label: "B3", tested: 100, goLive: 8, validatedPct: 67.5, status: "atualizado" }} />);
expect(screen.getByText("B3")).toBeInTheDocument();

render(<ThesisCard thesis={sampleThesis} />);
expect(screen.queryByText(/Volume confirmou/i)).not.toBeInTheDocument();
fireEvent.click(screen.getByRole("button", { name: /Tese 162 PETR4/i }));
expect(screen.getByText(/Volume confirmou/i)).toBeInTheDocument();
```

Run `npm test`. Expected: FAIL because components do not exist.

- [ ] **Step 2: Implement components**

Requirements:

- `Badge` follows AGENTS semantic types: open, closed, warning, success, danger, neutral, high, bull, bear, info.
- `KPICard` matches the AGENTS shape with card background, top accent and radial glow.
- `PatrickJane` supports states reporting, observing, testing, alerting, celebrating and uses calm method-first wording supplied by the caller.
- `ProgressBar` clamps progress between 0 and 100.
- `FrontCard` shows tested, go-live and validation metrics for B3, Cripto or Imóveis.
- `ThesisCard` is clickable; first click expands details and second click collapses details. Long texts stay inside the expanded area.
- `LearningLoopCard` renders Dor observada, Remédio aplicado and Impacto esperado.
- All styling uses inline `style={}` and tokens from `C`.
- No `className`, no CSS file, no Tailwind.

Run:

```powershell
npm test
```

Expected: PASS.

- [ ] **Step 3: Commit**

```powershell
git add apps/grao-invest-cockpit/src/components apps/grao-invest-cockpit/src/__tests__/components.test.jsx
git commit -m "feat: add cockpit base components"
```

---

### Task 4: Data Adapter For B3, Cripto And Imóveis

**Files:**
- Create: `apps/grao-invest-cockpit/src/data/cockpitHalleyAdapter.js`
- Create: `apps/grao-invest-cockpit/src/data/cockpitHalleyApi.js`
- Create: `apps/grao-invest-cockpit/src/data/mockCockpitHalley.js`
- Test: `apps/grao-invest-cockpit/src/__tests__/cockpitHalleyAdapter.test.js`

- [ ] **Step 1: Write adapter tests**

Use fixture payloads shaped like current endpoints:

- `dashboardSummary.thesis_history_overview.total_tested = 1727`
- `dashboardSummary.thesis_history_overview.success_rate_pct = 67.52`
- `dashboardSummary.thesis_history_overview.expectancy_net_pct = 2.683`
- `currentMonitor.theses[0].instrument = "PETR4"`
- `currentMonitor.theses[1].instrument = "BTCUSDT"`
- `realEstateCandidates.candidates[0].status = "analysis"`

Assertions:

```js
expect(statusToUi("monitoring")).toEqual({ label: "Observando", badge: "info" });
expect(statusToUi("target_hit")).toEqual({ label: "Validada", badge: "success" });
expect(statusToUi("stop_alert")).toEqual({ label: "Alerta", badge: "warning" });
expect(result.scientificSummary.testedTheses).toBe(1727);
expect(result.scientificSummary.goLiveCount).toBe(3);
expect(result.fronts.map((front) => front.id)).toEqual(["b3", "crypto", "real_estate"]);
expect(result.fronts.find((front) => front.id === "b3").goLive).toBe(1);
expect(result.fronts.find((front) => front.id === "crypto").goLive).toBe(1);
expect(result.fronts.find((front) => front.id === "real_estate").goLive).toBe(1);
expect(result.goLiveTheses[0].daysOpen).toBe(4);
expect(result.learningLoops.length).toBeGreaterThan(0);
```

Run `npm test`. Expected: FAIL because data files do not exist.

- [ ] **Step 2: Implement adapter**

`normalizeCockpitHalley(payloads, now)` returns exactly:

```js
{
  scientificSummary: {
    testedTheses,
    validatedPct,
    expectancyPct,
    goLiveCount,
    appliedLearningsCount,
    lastUpdatedAt
  },
  goLiveTheses: [
    { id, front, asset, direction, hypothesis, evidence, entryPrice, currentPrice, targetPrice, stopPrice, expectedPct, currentPct, daysOpen, openedAt, status, learning, janeState, janeMessage, operation, invalidation }
  ],
  learningLoops: [
    { pain, remedy, expectedImpact, appliedTo, evidenceCount }
  ],
  fronts: [
    { id: "b3", label: "B3", tested, goLive, validatedPct, status, lastUpdatedAt },
    { id: "crypto", label: "Cripto", tested, goLive, validatedPct, status, lastUpdatedAt },
    { id: "real_estate", label: "Imóveis", tested, goLive, validatedPct, status, lastUpdatedAt }
  ]
}
```

Rules:

- Instruments ending in `USDT` or containing BTC, ETH or SOL map to Cripto.
- Other market instruments map to B3.
- Real estate candidates map to Imóveis.
- Days open are integer days from `thesis_raised_at` or candidate date to `now`.
- Learning loops must be real pain/remedy/impact sentences, not one-word categories.
- If payloads are missing, return safe defaults and do not throw.
- Use `cleanText` on any user-facing text from payloads.

- [ ] **Step 3: Implement API fetcher**

`fetchCockpitPayloads()` calls:

```text
/api/dashboard/summary/1
/api/theses/current-monitor/latest
/api/real-estate/candidates
```

Use `Promise.allSettled` and return partial results plus `errors`; a single failed feed must not blank the cockpit.

- [ ] **Step 4: Create mock fallback seed**

Mock must include:

- One B3 thesis, for example PETR4.
- One Cripto thesis, for example BTCUSDT.
- One Imóveis candidate.
- At least three learning notes covering volume confirmation, stop discipline and target/prazo calibration.

Run:

```powershell
npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/grao-invest-cockpit/src/data apps/grao-invest-cockpit/src/__tests__/cockpitHalleyAdapter.test.js
git commit -m "feat: normalize cockpit halley data"
```

---
### Task 5: Compose Cockpit Halley Screen

**Files:**
- Modify: `apps/grao-invest-cockpit/src/App.jsx`
- Create: `apps/grao-invest-cockpit/src/screens/CockpitHalley.jsx`
- Test: `apps/grao-invest-cockpit/src/__tests__/CockpitHalley.test.jsx`

- [ ] **Step 1: Write screen tests**

Tests must assert:

```jsx
expect(screen.getByText("Teses testadas")).toBeInTheDocument();
expect(screen.getByText("Validação histórica")).toBeInTheDocument();
expect(screen.getByText("Expectância líquida")).toBeInTheDocument();
expect(screen.getByText("B3")).toBeInTheDocument();
expect(screen.getByText("Cripto")).toBeInTheDocument();
expect(screen.getByText("Imóveis")).toBeInTheDocument();
expect(screen.getByText(/Feed temporariamente indisponível/i)).toBeInTheDocument();
```

Also assert that thesis detail remains collapsed until clicking the card.

Run `npm test`. Expected: FAIL because screen does not exist.

- [ ] **Step 2: Implement screen**

`CockpitHalley.jsx` renders:

- Header with `Cockpit Halley`, subtitle and last updated date.
- Optional amber feed warning when feed status is fallback.
- `PatrickJane` reporting message from the approved spec.
- KPI grid `repeat(5, 1fr)`: Teses testadas, Validação histórica, Expectância líquida, Teses em go-live, Aprendizados aplicados.
- Front grid `1fr 1fr 1fr`: B3, Cripto, Imóveis.
- Go-live thesis grid `1fr 1fr 1fr` with expandable `ThesisCard`.
- Learning grid `1fr 1fr` with `LearningLoopCard`.

Responsive rule for this first slice:

```js
const isNarrow = typeof window !== "undefined" && window.innerWidth < 760;
const threeCol = isNarrow ? "1fr" : "1fr 1fr 1fr";
const fiveCol = isNarrow ? "1fr" : "repeat(5, 1fr)";
```

Keep all style inline and tokenized.

- [ ] **Step 3: Wire App**

`App.jsx` must:

- Call `useFonts()`.
- Start with `mockCockpitPayloads`.
- Call `fetchCockpitPayloads()` in `useEffect`.
- Use live payloads when available.
- Use mock fallback when all or part of the feed fails.
- Pass normalized data to `CockpitHalley`.
- Use `C.bg`, `C.text`, and Sora in the root style.

Run:

```powershell
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add apps/grao-invest-cockpit/src/App.jsx apps/grao-invest-cockpit/src/screens apps/grao-invest-cockpit/src/__tests__/CockpitHalley.test.jsx
git commit -m "feat: compose cockpit halley screen"
```

---

### Task 6: Documentation And Manual Verification

**Files:**
- Create: `apps/grao-invest-cockpit/README.md`

- [ ] **Step 1: Create README**

Include:

````md
# Grão Invest Cockpit Halley

Standalone React/PWA candidate for the Grão Invest scientific cockpit.

## Run

```powershell
cd apps/grao-invest-cockpit
npm install
npm run dev
```

## Test

```powershell
npm test
npm run build
```

## UX Validation

- The first screen shows Teses testadas, Validação histórica, Expectância líquida, Teses em go-live and Aprendizados aplicados.
- B3, Cripto and Imóveis appear as separate fronts.
- Clicking a thesis opens details and clicking again closes details.
- Accented words render correctly: Ações, Operações, Imóveis, Hipótese, Evidência, Validação, Refutação.
- No text sounds like investment recommendation.
- No Tailwind classes or CSS files are used for visual styling.
````

- [ ] **Step 2: Final verification**

Run:

```powershell
cd apps/grao-invest-cockpit
npm test
npm run build
```

Expected: PASS.

Run:

```powershell
git status --short
```

Expected: only intended cockpit files are changed or committed. Existing unrelated dirty files remain untouched.

- [ ] **Step 3: Commit**

```powershell
git add apps/grao-invest-cockpit/README.md
git commit -m "docs: add cockpit halley validation guide"
```

---

## Final Verification Before Publish

Run from `apps/grao-invest-cockpit`:

```powershell
npm test
npm run build
npm run dev
```

Manual checks:

- B3, Cripto and Imóveis are visibly separate.
- The consolidated top KPIs are visible without scrolling on desktop.
- On narrow mobile width, grids collapse to one column.
- Thesis details open and close by clicking the card.
- Acentos are correct.
- No `game` source appears as a thesis source.
- No recommendation language appears.

## Rollback Strategy

This implementation is isolated under `apps/grao-invest-cockpit`. Rollback is a normal git revert of the cockpit commits. No backend migration, Android change, production route change or job schedule change is part of this plan.

## Execution Recommendation

Use Subagent-Driven execution if available, with one fresh worker per task and review after each commit. Use Inline Execution only if subagents are not desired.
