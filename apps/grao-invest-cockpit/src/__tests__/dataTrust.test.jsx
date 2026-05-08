import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { C } from "../components";
import { dataTrustForScreen, withCockpitDataTrust } from "../data/dataTrust.js";
import Backtest from "../screens/Backtest.jsx";
import CockpitHalley from "../screens/CockpitHalley.jsx";
import Teses from "../screens/Teses.jsx";

const trustedData = {
  scientificSummary: {
    testedTheses: 1727,
    validatedPct: 67.52,
    expectancyPct: 2.68,
    goLiveCount: 3,
    appliedLearningsCount: 18,
    lastUpdatedAt: "2026-05-03T10:00:00Z",
  },
  activeTheses: [],
  fronts: [],
  learningLoops: [],
  thesisRows: [
    {
      id: "B3-001",
      asset: "PETR4",
      front: "B3",
      direction: "Alta",
      expectedPct: 4.82,
      resultPct: 3.14,
      statusGroup: "Go-live",
      outcome: "Observando",
    },
  ],
  backtest: {
    accuracyCycles: [
      { ciclo: "Cal.08", taxa: 55 },
      { ciclo: "Cal.09", taxa: 56.4 },
      { ciclo: "Cal.10", taxa: 57.8 },
      { ciclo: "Cal.11", taxa: 59.1 },
      { ciclo: "Cal.12", taxa: 60.3 },
      { ciclo: "Cal.13", taxa: 61.7 },
      { ciclo: "Cal.14", taxa: 62.9 },
      { ciclo: "Cal.15", taxa: 64.2 },
      { ciclo: "Cal.16", taxa: 65.4 },
      { ciclo: "Cal.17", taxa: 66.3 },
      { ciclo: "Cal.18", taxa: 67.52 },
    ],
  },
};

describe("data trust layer", () => {
  it("marks invalid scientific percentages as degraded before the UI trusts them", () => {
    const trust = dataTrustForScreen("dashboard", {
      scientificSummary: {
        testedTheses: 100,
        validatedPct: 141,
        expectancyPct: 2.1,
        goLiveCount: 2,
        appliedLearningsCount: 4,
      },
    });

    expect(trust.status).toBe("degraded");
    expect(trust.issues.map((issue) => issue.code)).toContain("dashboard.validatedPct.range");
  });

  it("downgrades otherwise valid data when the feed is using fallback", () => {
    const trust = dataTrustForScreen("teses", trustedData, "fallback");

    expect(trust.status).toBe("partial");
    expect(trust.label).toBe("Dados parciais");
  });

  it("marks synthetic calibration history as partial even when values are in range", () => {
    const trust = dataTrustForScreen("backtest", {
      backtest: {
        accuracyCycleSource: "synthetic",
        accuracyCycles: trustedData.backtest.accuracyCycles,
      },
    });

    expect(trust.status).toBe("partial");
    expect(trust.issues.map((issue) => issue.code)).toContain("backtest.cycles.synthetic");
  });

  it("attaches per-screen trust metadata to normalized cockpit data", () => {
    const result = withCockpitDataTrust(trustedData, "live");

    expect(result.dataTrust.dashboard.status).toBe("validated");
    expect(result.dataTrust.teses.status).toBe("validated");
    expect(result.dataTrust.backtest.status).toBe("validated");
  });

  it("degrades teses when an opened date is in the local future", () => {
    const trust = dataTrustForScreen("teses", {
      trustReferenceAt: "2026-05-06T23:30:00-03:00",
      thesisRows: [
        {
          id: "CR-001",
          asset: "BTCUSDT",
          front: "Cripto",
          direction: "Neutra",
          statusGroup: "Go-live",
          openedAt: "2026-05-07T03:01:00+00:00",
          entryPrice: 81212.04,
          targetPrice: 81212.04,
          stopPrice: 79993.86,
          rangeLowerPrice: 79993.86,
          rangeUpperPrice: 82430.22,
        },
      ],
    });

    expect(trust.status).toBe("degraded");
    expect(trust.issues.map((issue) => issue.code)).toContain("teses.rows.0.openedAt.future");
  });

  it("degrades directional teses with entry equal to target", () => {
    const trust = dataTrustForScreen("teses", {
      thesisRows: [
        {
          id: "B3-002",
          asset: "PETR4",
          front: "B3",
          direction: "Alta",
          statusGroup: "Go-live",
          openedAt: "2026-05-06T12:00:00-03:00",
          entryPrice: 40.12,
          targetPrice: 40.12,
          stopPrice: 38.9,
        },
      ],
    });

    expect(trust.status).toBe("degraded");
    expect(trust.issues.map((issue) => issue.code)).toContain("teses.rows.0.target.same_as_entry");
  });

  it("degrades range teses without explicit lower and upper bounds", () => {
    const trust = dataTrustForScreen("teses", {
      thesisRows: [
        {
          id: "CR-002",
          asset: "BTCUSDT",
          front: "Cripto",
          direction: "Neutra",
          statusGroup: "Go-live",
          openedAt: "2026-05-06T12:00:00-03:00",
          entryPrice: 81212.04,
          targetPrice: 81212.04,
          stopPrice: 79993.86,
        },
      ],
    });

    expect(trust.status).toBe("degraded");
    expect(trust.issues.map((issue) => issue.code)).toContain("teses.rows.0.range.bounds");
  });

  it("degrades stale B3 current teses unless the monitor is explicitly frozen", () => {
    const trust = dataTrustForScreen("teses", {
      trustReferenceAt: "2026-05-07T00:00:00+00:00",
      monitorTrust: { isFrozen: false },
      thesisRows: [
        {
          id: "B3-003",
          asset: "PETR4",
          front: "B3",
          direction: "Alta",
          statusGroup: "Go-live",
          openedAt: "2026-04-22T20:46:19+00:00",
          latestEventAt: "2026-04-22T20:46:19+00:00",
          entryPrice: 47.02,
          targetPrice: 50.31,
          stopPrice: 45.04,
        },
      ],
    });

    expect(trust.status).toBe("degraded");
    expect(trust.issues.map((issue) => issue.code)).toContain("teses.rows.0.b3.stale_current");
  });

  it("renders icon-only trust seals on the three critical screens", () => {
    const data = withCockpitDataTrust(trustedData, "live");

    render(<CockpitHalley data={data} />);
    expect(screen.getByTestId("data-trust-seal-dashboard")).toHaveAttribute("aria-label", "Dados validados");
    expect(screen.getByTestId("data-trust-seal-dashboard")).toHaveStyle({ color: C.teal });
    expect(screen.queryByText("Dados validados")).not.toBeInTheDocument();

    render(<Teses data={data} feedStatus="live" />);
    expect(screen.getByTestId("data-trust-seal-teses")).toHaveAttribute("aria-label", "Dados validados");

    render(<Backtest data={data} />);
    expect(screen.getByTestId("data-trust-seal-backtest")).toHaveAttribute("aria-label", "Dados validados");
  });
});
