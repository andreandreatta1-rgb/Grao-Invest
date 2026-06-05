import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import { normalizeCockpitHalley } from "../data/cockpitHalleyAdapter.js";
import Saude from "../screens/Saude.jsx";

const dashboardSummary = {
  updated_at: "2026-05-04T10:00:00.000Z",
  thesis_history_overview: {
    total_tested: 1901,
    success_rate_pct: 67.52,
    expectancy_net_pct: 2.68,
    applied_learnings_count: 18,
  },
  current_simulation_summary: {
    thesis_count: 2,
    expected_pct: 4.1,
    achieved_pct: 2.3,
    approved_count: 1,
  },
  thesis_open_operations: [
    {
      thesis_id: "B3-001",
      thesis_number: "B3-001",
      front: "B3",
      action: "PETR4",
      phase: "pos_go_live",
      status: "Observando",
      is_open: true,
      expected_result_pct: 4.82,
      moment_result_pct: 2.36,
      entry_price_brl: 39.92,
      current_price_brl: 40.86,
      operation_plan: "Compra estruturada com alvo e stop",
      structured_operation: "Rompimento com volume",
      exit_rule: "alvo R$ 43,37 / stop R$ 38,83",
      outcome: "Observando",
    },
  ],
  data_quality_gate: {
    checks: [
      { check_id: "market_fresh_coverage", label: "Market fresh coverage", status: "warning", details: "fresh=0/1 com lag <= 1800s" },
      { check_id: "provider_critical_count", label: "Provider critical count", status: "pass", details: "providers_criticos=0" },
      { check_id: "provider_no_data_count", label: "Provider no-data count", status: "pass", details: "providers_sem_dados=0" },
      { check_id: "fundamentals_coverage", label: "Fundamentals coverage", status: "pass", details: "com_snapshot=1/1 no universo alvo" },
      { check_id: "fundamentals_fresh_coverage", label: "Fundamentals fresh coverage", status: "warning", details: "frescos=0/1 com staleness <= 1 dia(s)" },
      { check_id: "news_recent_coverage", label: "News recent coverage", status: "warning", details: "ativos_com_noticia=0/1 na janela de 7 dia(s)" },
    ],
  },
};

function successFetch(url) {
  if (String(url).includes("/api/dashboard/summary/1")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(dashboardSummary) });
  }
  if (String(url).includes("/api/theses/current-monitor/latest")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ theses: [] }) });
  }
  if (String(url).includes("/api/real-estate/candidates")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ candidates: [] }) });
  }
  if (String(url).includes("/api/real-estate/strategy-territory-candidates")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        summary: {
          strategy_count: 9,
          territory_count: 12,
          matrix_brief_count: 108,
          source_candidate_count: 18,
          source_confirmed_requalification_count: 4,
        },
        matrix_briefs: [],
        strategy_candidate_watchlist: [],
        condominium_requalification_watchlist: [],
      }),
    });
  }
  return Promise.reject(new Error(`unexpected url ${url}`));
}

describe("laboratory health screen", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows API health, official endpoints, operation array and daily command", async () => {
    vi.stubGlobal("fetch", vi.fn(successFetch));
    const user = userEvent.setup();

    render(<App />);

    await waitFor(() => expect(screen.getByText("1.901")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Sa\u00fade/i }));

    expect(screen.queryByRole("heading", { name: "Sa\u00fade" })).not.toBeInTheDocument();
    expect(screen.getByText(/Prontid\u00e3o di\u00e1ria dos feeds/i)).toBeInTheDocument();
    expect(screen.getAllByText("API real").length).toBeGreaterThan(0);
    expect(screen.getByAltText("Patrick Jane")).toHaveAttribute("src", "/assets/metodo/09.webp");
    expect(screen.getByText("/api/dashboard/summary/1")).toBeInTheDocument();
    expect(screen.getByText("/api/real-estate/strategy-territory-candidates")).toBeInTheDocument();
    expect(screen.getByText("thesis_open_operations")).toBeInTheDocument();
    expect(screen.getByText("npm run validate:daily")).toBeInTheDocument();
    expect(screen.getByText("Cobertura por fonte")).toBeInTheDocument();
    expect(screen.getByText("microtrades-data-refresh")).toBeInTheDocument();
    expect(screen.getByText("data-context-refresh")).toBeInTheDocument();
    expect(screen.getAllByText("Noticias sem cobertura recente").length).toBeGreaterThan(0);
  });

  it("uses canonical unique tested theses instead of raw thesis rows", async () => {
    vi.stubGlobal("fetch", vi.fn(successFetch));
    const user = userEvent.setup();

    render(<App />);

    await waitFor(() => expect(screen.getByText("1.901")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Sa\u00fade/i }));

    expect(screen.getByText("Teses testadas \u00fanicas")).toBeInTheDocument();
    expect(screen.getByText("1.901")).toBeInTheDocument();
    expect(screen.queryByText("Teses no laborat\u00f3rio")).not.toBeInTheDocument();
    expect(screen.queryByText("linhas normalizadas")).not.toBeInTheDocument();
  });

  it("summarizes quality warnings with user-facing labels", async () => {
    vi.stubGlobal("fetch", vi.fn(successFetch));
    const user = userEvent.setup();

    render(<App />);

    await waitFor(() => expect(screen.getByText("1.901")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Sa\u00fade/i }));

    expect(await screen.findByText("Qualidade com aten\u00e7\u00e3o")).toBeInTheDocument();
    expect(await screen.findByText("Feeds 4/4 online \u00b7 3 alertas de qualidade exigem confer\u00eancia antes de ampliar risco.")).toBeInTheDocument();
    expect(await screen.findByText("Pre\u00e7o de mercado atualizado")).toBeInTheDocument();
    expect(await screen.findByText("Fornecedores cr\u00edticos")).toBeInTheDocument();
    expect(await screen.findByText("Not\u00edcias recentes")).toBeInTheDocument();
    expect(screen.queryByText("Market fresh coverage")).not.toBeInTheDocument();
  });

  it("shows the operational freshness traffic light before the technical rows", async () => {
    const data = normalizeCockpitHalley({
      dashboardSummary: {
        ...dashboardSummary,
        ops_health: {
          status: "ok",
          stages: {
            market_feed: {
              status: "ok",
              fronts: {
                b3: { age_days: 0.2, max_age_days: 4 },
                crypto: { age_days: 0.01, max_age_days: 1 },
              },
            },
          },
        },
      },
      currentMonitor: {
        scan_scope: { fresh_instruments: ["PETR4", "BTCUSDT"], tick_count: 200 },
        theses: [
          {
            thesis_id: "TH-PETR4-bullish-0001",
            instrument: "PETR4",
            direction: "bullish",
            thesis_raised_at: "2026-05-04T09:30:00Z",
            monitor_status: "monitoring",
            news_available: true,
            fundamental_available: true,
          },
        ],
      },
      realEstateCandidates: { candidates: [] },
      realEstateStrategyTerritoryCandidates: { matrix_briefs: [] },
    });
    render(<Saude data={data} feedStatus="live" feedHealth={[]} />);

    const board = await screen.findByTestId("freshness-board");
    expect(within(board).getByText("Sem\u00e1foro de frescor")).toBeInTheDocument();
    expect(within(board).getByText("Frescor operacional")).toBeInTheDocument();
    expect(screen.getAllByText("Parcial").length).toBeGreaterThan(0);
    expect(screen.getByText("B3")).toBeInTheDocument();
    expect(screen.getByText("Cripto")).toBeInTheDocument();
    expect(screen.getByText("Im\u00f3veis")).toBeInTheDocument();
  });

  it("keeps the operational freshness board visible when the adapter has no freshness summary yet", async () => {
    render(
      <Saude
        data={{
          scientificSummary: { testedTheses: 879 },
          coverage: {
            market: { status: "fresh", label: "Mercado atualizado" },
            history: { status: "fresh", label: "Historico disponivel" },
          },
        }}
        feedStatus="live"
        feedHealth={[
          {
            key: "dashboardSummary",
            label: "Resumo cientifico",
            status: "live",
            labelStatus: "API real",
            endpoint: "/api/dashboard/summary/1",
            officialArray: "thesis_open_operations",
            message: "Feed oficial respondendo.",
          },
        ]}
      />,
    );

    const board = screen.getByTestId("freshness-board");
    expect(within(board).getByText("Sem\u00e1foro de frescor")).toBeInTheDocument();
    expect(within(board).getByText("Frescor operacional")).toBeInTheDocument();
    expect(within(board).getByText(/Resumo cientifico/)).toBeInTheDocument();
  });

  it("makes fallback explicit when feeds are unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    await waitFor(() => expect(screen.getByText(/Feed temporariamente indispon\u00edvel/i)).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Sa\u00fade/i }));

    expect(screen.getAllByText("Fallback ativo").length).toBeGreaterThan(0);
    expect(within(screen.getByRole("complementary")).getByText(/Feed temporariamente/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Feed temporariamente indispon\u00edvel/i).length).toBeGreaterThanOrEqual(1);
  });
});
