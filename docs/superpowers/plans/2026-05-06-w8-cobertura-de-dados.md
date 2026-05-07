# W8 Cobertura De Dados Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Grao Invest show honest data coverage for market, history, news, fundamentals and macro, while adding the scheduled context refresh that keeps non-price sources updated.

**Architecture:** Keep the backend as the source of truth and add a GitHub Actions workflow that calls the existing `/api/ops/data-context-refresh` endpoint. Normalize coverage in the cockpit adapter so every screen consumes the same contract, then render compact explanations on Dashboard, thesis cards and Saude without treating missing sources as neutral `50%` evidence.

**Tech Stack:** GitHub Actions, FastAPI endpoint already present, React 18/Vite, Vitest, Testing Library, inline style system from `src/components/tokens.js`.

---

### Task 1: Scheduled Data Context Refresh Workflow

**Files:**
- Create: `.github/workflows/data-context-refresh.yml`
- Create: `tests/unit/test_github_actions_data_context_refresh.py`

- [ ] **Step 1: Write the failing workflow test**

Create `tests/unit/test_github_actions_data_context_refresh.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "data-context-refresh.yml"


def test_github_actions_data_context_refresh_workflow_is_configured() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "name: Data context refresh" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "30 11,21 * * *"' in workflow
    assert "https://grao-invest.vercel.app" in workflow
    assert "/api/ops/data-context-refresh" in workflow
    assert "run_fundamentals=true" in workflow
    assert "run_news=true" in workflow
    assert "max_instruments=10" in workflow
    assert "news_lookback_days=3" in workflow
    assert "max_articles_per_instrument=20" in workflow
    assert "fundamentals_provider=auto" in workflow
    assert "fundamentals_only_missing=false" in workflow
    assert "Authorization: Bearer ${{ secrets.CRON_SECRET }}" in workflow
    assert "X-GitHub-Actions-Refresh: data-context-twice-daily" in workflow
    assert "--request POST" in workflow
    assert "--fail-with-body" in workflow
    assert "--max-time 180" in workflow
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_github_actions_data_context_refresh.py -q
```

Expected: fail with `FileNotFoundError` because `data-context-refresh.yml` does not exist.

- [ ] **Step 3: Add the workflow**

Create `.github/workflows/data-context-refresh.yml`:

```yaml
name: Data context refresh

on:
  workflow_dispatch:
  schedule:
    - cron: "30 11,21 * * *"

concurrency:
  group: data-context-refresh
  cancel-in-progress: false

jobs:
  refresh:
    name: Refresh news and fundamentals
    runs-on: ubuntu-latest
    timeout-minutes: 8
    env:
      BASE_URL: https://grao-invest.vercel.app
      REFRESH_PATH: /api/ops/data-context-refresh
      REFRESH_QUERY: run_fundamentals=true&run_news=true&max_instruments=10&news_lookback_days=3&max_articles_per_instrument=20&fundamentals_provider=auto&fundamentals_only_missing=false
    steps:
      - name: Check CRON_SECRET is configured
        env:
          CRON_SECRET: ${{ secrets.CRON_SECRET }}
        run: |
          if [ -z "$CRON_SECRET" ]; then
            echo "::error::Configure the repository secret CRON_SECRET before enabling data context refresh."
            exit 1
          fi

      - name: Call bounded data context refresh
        run: |
          curl \
            --request POST \
            --fail-with-body \
            --silent \
            --show-error \
            --max-time 180 \
            --retry 2 \
            --retry-delay 10 \
            --header "Authorization: Bearer ${{ secrets.CRON_SECRET }}" \
            --header "X-GitHub-Actions-Refresh: data-context-twice-daily" \
            "$BASE_URL$REFRESH_PATH?$REFRESH_QUERY"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_github_actions_data_context_refresh.py tests\unit\test_github_actions_microtrades_refresh.py -q
```

Expected: both workflow tests pass.

### Task 2: Normalize Coverage Contract In Cockpit Adapter

**Files:**
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\data\cockpitHalleyAdapter.js`
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\__tests__\cockpitHalleyAdapter.test.js`

- [ ] **Step 1: Write failing adapter test**

Append a test that normalizes the live crypto current monitor:

```js
it("exposes data coverage without treating missing confirmation sources as neutral evidence", () => {
  const result = normalizeCockpitHalley(
    {
      currentMonitor: {
        generated_at: "2026-05-07T00:50:13Z",
        scan_scope: {
          fresh_instruments: ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
          tick_count: 7774,
        },
        theses: [
          {
            thesis_id: "TH-BTCUSDT-range-0007",
            instrument: "BTCUSDT",
            direction: "range",
            entry_price: 81222.99,
            latest_price: 81222.99,
            target_price: 81222.99,
            stop_price: 80004.6452,
            thesis_raised_at: "2026-05-07T00:30:00Z",
            monitor_status: "monitoring",
            fundamental_available: false,
            news_available: false,
            geo_oil_available: false,
            fundamental_support_pct: 50,
            news_support_pct: 50,
          },
        ],
      },
    },
    new Date("2026-05-07T00:55:00Z"),
  );

  expect(result.coverage.market).toMatchObject({ status: "fresh", label: "Mercado atualizado" });
  expect(result.coverage.history).toMatchObject({ status: "fresh", label: "Historico disponivel" });
  expect(result.coverage.news).toMatchObject({ status: "missing", label: "Noticias sem cobertura recente" });
  expect(result.coverage.fundamentals).toMatchObject({ status: "not_applicable", label: "Fundamentos nao aplicaveis para cripto" });
  expect(result.coverage.macro).toMatchObject({ status: "disabled", label: "Macro fora do MVP atual" });
  expect(result.goLiveTheses[0].coverageNotes).toEqual(expect.arrayContaining([
    "Tese tecnica com mercado fresco.",
    "Faltam noticias recentes para confirmar contexto.",
    "Fundamentos nao se aplicam a este par cripto.",
    "Confianca reduzida por lacunas de confirmacao.",
  ]));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `apps/grao-invest-cockpit`:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\cockpitHalleyAdapter.test.js
```

Expected: fail because `coverage` and `coverageNotes` do not exist.

- [ ] **Step 3: Implement coverage helpers**

Add helper functions in `cockpitHalleyAdapter.js`:

```js
const COVERAGE_ORDER = Object.freeze(["market", "history", "news", "fundamentals", "macro"]);

function coverageItem(status, label, detail = "") {
  return { status, label, detail };
}

function normalizeCoverage(payloads, monitorTrust, goLiveTheses) {
  const currentMonitor = payloads?.currentMonitor ?? {};
  const scanScope = currentMonitor?.scan_scope ?? currentMonitor?.scanScope ?? {};
  const freshInstruments = asArray(scanScope.fresh_instruments ?? scanScope.freshInstruments);
  const tickCount = toNumber(scanScope.tick_count ?? scanScope.tickCount, 0);
  const marketFresh = !monitorTrust?.isFrozen && (freshInstruments.length > 0 || tickCount > 0);
  const fronts = new Set(goLiveTheses.map((thesis) => thesis.front));
  const cryptoOnly = fronts.size > 0 && [...fronts].every((front) => front === "Cripto");
  const anyNews = goLiveTheses.some((thesis) => thesis.sourceAvailability?.news === true);
  const anyFundamentals = goLiveTheses.some((thesis) => thesis.sourceAvailability?.fundamentals === true);

  return {
    market: coverageItem(marketFresh ? "fresh" : "stale", marketFresh ? "Mercado atualizado" : "Mercado sem frescor recente"),
    history: coverageItem("fresh", "Historico disponivel"),
    news: coverageItem(anyNews ? "fresh" : "missing", anyNews ? "Noticias recentes conectadas" : "Noticias sem cobertura recente"),
    fundamentals: cryptoOnly
      ? coverageItem("not_applicable", "Fundamentos nao aplicaveis para cripto")
      : coverageItem(anyFundamentals ? "fresh" : "missing", anyFundamentals ? "Fundamentos conectados" : "Fundamentos sem cobertura recente"),
    macro: coverageItem("disabled", "Macro fora do MVP atual"),
  };
}
```

Attach `sourceAvailability` and `coverageNotes` to each normalized thesis. For missing confirmation notes, check `news_available`, `fundamental_available`, `geo_oil_available`, and crypto front.

- [ ] **Step 4: Run adapter test to verify it passes**

Run:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\cockpitHalleyAdapter.test.js
```

Expected: adapter tests pass.

### Task 3: Show Coverage On Dashboard And Thesis Cards

**Files:**
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\screens\CockpitHalley.jsx`
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\components\ThesisCard.jsx`
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\__tests__\CockpitHalley.test.jsx`
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\__tests__\components.test.jsx`

- [ ] **Step 1: Write failing UI tests**

Add dashboard expectation:

```js
expect(screen.getByText("Cobertura de dados")).toBeInTheDocument();
expect(screen.getByText("Mercado atualizado")).toBeInTheDocument();
expect(screen.getByText(/Noticias/i)).toBeInTheDocument();
```

Add component test:

```js
it("shows thesis coverage notes before expansion", () => {
  render(
    <ThesisCard
      thesis={{
        ...sampleThesis,
        coverageNotes: [
          "Tese tecnica com mercado fresco.",
          "Faltam noticias recentes para confirmar contexto.",
          "Fundamentos nao se aplicam a este par cripto.",
          "Confianca reduzida por lacunas de confirmacao.",
        ],
      }}
    />,
  );

  const trigger = screen.getByRole("button", { name: /Tese 162 PETR4/i });
  expect(trigger).toHaveTextContent("Tese tecnica com mercado fresco.");
  expect(trigger).toHaveTextContent("Faltam noticias recentes para confirmar contexto.");
  expect(trigger).not.toHaveTextContent("50%");
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\CockpitHalley.test.jsx src\__tests__\components.test.jsx
```

Expected: fail because the new coverage texts are not rendered.

- [ ] **Step 3: Implement dashboard block and thesis notes**

Add a compact `CoverageStrip` in `CockpitHalley.jsx` and render it between `FrozenMonitorNotice` and `ScientificScore`. Add a small note list in `ThesisCard.jsx` above Motivo/Operacao/Saida. Use only `C` tokens and inline styles.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\CockpitHalley.test.jsx src\__tests__\components.test.jsx
```

Expected: both UI test files pass.

### Task 4: Show Coverage And Workflow Status On Saude

**Files:**
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\screens\Saude.jsx`
- Modify: `C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\src\__tests__\healthScreen.test.jsx`

- [ ] **Step 1: Write failing Saude test**

Add expectations after opening Saude:

```js
expect(screen.getByText("Cobertura por fonte")).toBeInTheDocument();
expect(screen.getByText("microtrades-data-refresh")).toBeInTheDocument();
expect(screen.getByText("data-context-refresh")).toBeInTheDocument();
expect(screen.getByText("Noticias sem cobertura recente")).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\healthScreen.test.jsx
```

Expected: fail because Saude does not render coverage/workflow status.

- [ ] **Step 3: Implement Saude sections**

Render `data.coverage` as `Cobertura por fonte`. Render a static operational block `Rotina de atualizacao` with:

```js
[
  { name: "microtrades-data-refresh", status: coverage.market.status === "fresh" ? "success" : "partial", detail: coverage.market.label },
  { name: "data-context-refresh", status: coverage.news.status === "fresh" || coverage.fundamentals.status === "fresh" ? "success" : "partial", detail: `${coverage.news.label} · ${coverage.fundamentals.label}` },
]
```

- [ ] **Step 4: Run Saude test to verify pass**

Run:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\healthScreen.test.jsx
```

Expected: Saude tests pass.

### Task 5: Build, Sync Frontend Dist, Verify And Commit

**Files:**
- Modify generated assets under `C:\Users\Andreatta\.config\superpowers\worktrees\ProjectOne - Copia\w8-cobertura-de-dados\services\api\frontend_dist`

- [ ] **Step 1: Run targeted backend and frontend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_github_actions_data_context_refresh.py tests\unit\test_github_actions_microtrades_refresh.py tests\e2e\test_data_context_refresh_api.py -q
```

Run from `apps/grao-invest-cockpit`:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\dist\cli.js run src\__tests__\cockpitHalleyAdapter.test.js src\__tests__\CockpitHalley.test.jsx src\__tests__\components.test.jsx src\__tests__\healthScreen.test.jsx
```

- [ ] **Step 2: Build frontend**

Run from `apps/grao-invest-cockpit`:

```powershell
& 'C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vite\bin\vite.js build
```

- [ ] **Step 3: Sync dist to deploy repo worktree**

Run:

```powershell
$src = (Resolve-Path 'C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\apps\grao-invest-cockpit\dist').Path
$dest = (Resolve-Path 'C:\Users\Andreatta\.config\superpowers\worktrees\ProjectOne - Copia\w8-cobertura-de-dados\services\api\frontend_dist').Path
Copy-Item -Path "$src\*" -Destination $dest -Recurse -Force
```

- [ ] **Step 4: Verify deployed bundle contains coverage strings**

Run:

```powershell
Select-String -Path 'services\api\frontend_dist\assets\*.js' -Pattern 'Cobertura de dados','data-context-refresh','Noticias sem cobertura recente'
```

Expected: all three strings are found in the generated JS bundle.

- [ ] **Step 5: Review status, commit and push**

Run:

```powershell
git status --short
git add .github/workflows/data-context-refresh.yml tests/unit/test_github_actions_data_context_refresh.py docs/superpowers/plans/2026-05-06-w8-cobertura-de-dados.md services/api/frontend_dist
git commit -m "Add W8 data coverage refresh and UI"
git push -u origin feature/w8-cobertura-de-dados
```

Expected: commit contains only W8 workflow/test/plan and deploy frontend assets. The dirty files in the original main worktree remain untouched.
