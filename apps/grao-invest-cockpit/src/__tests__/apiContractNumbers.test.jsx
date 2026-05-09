import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

const dashboardSummary879 = {
  updated_at: "2026-05-08T22:39:03+00:00",
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
  thesis_history_overview: {
    total_tested: 879,
    success_count: 671,
    success_rate_pct: 76.34,
    expectancy_net_pct: 3.0073,
    applied_learnings_count: 18,
  },
  historical_analysis_summary: {
    thesis_count: 879,
    avg_expected_pct: 4.1227,
    avg_return_pct: 3.0071,
    approved_count: 671,
  },
  thesis_open_operations: [
    {
      thesis_id: "IM-1888",
      thesis_number: 1888,
      front: "imoveis",
      action: "REAL - VivaReal Colonia",
      status: "Fechada",
      is_open: false,
      expected_result_pct: -31.92,
      moment_result_pct: -31.92,
      entry_price_brl: 215000,
      current_price_brl: 240000,
      real_estate_analysis: { score: 63, confidence: 51 },
    },
  ],
};

function fetchContract(url) {
  const target = String(url);
  if (target.includes("/api/frontend/version")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  }
  if (target.includes("/api/dashboard/summary/1")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(dashboardSummary879) });
  }
  if (target.includes("/api/theses/current-monitor/latest")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        scan_scope: { fresh_instruments: ["PETR4"], tick_count: 100 },
        theses: [],
      }),
    });
  }
  if (target.includes("/api/real-estate/candidates")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ candidates: [] }) });
  }
  if (target.includes("/api/real-estate/strategy-territory-candidates")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ matrix_briefs: [] }) });
  }
  return Promise.reject(new Error(`unexpected url ${target}`));
}

describe("API contract numbers", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("keeps the canonical 879 thesis count stable from API payload through dashboard and validation UI", async () => {
    vi.stubGlobal("fetch", vi.fn(fetchContract));
    const user = userEvent.setup();

    render(<App />);

    await waitFor(() => expect(screen.getAllByText("879").length).toBeGreaterThan(0));
    expect(screen.queryByText("1.727")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Valida/i }));

    expect(screen.getAllByText("879").length).toBeGreaterThan(0);
    expect(screen.queryByText("1.727")).not.toBeInTheDocument();
  });
});
