import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { C } from "../components";
import { normalizeCockpitHalley } from "../data/cockpitHalleyAdapter.js";
import { mockCockpitHalleyPayloads } from "../data/mockCockpitHalley.js";
import CockpitHalley from "../screens/CockpitHalley.jsx";

const cockpitData = normalizeCockpitHalley(
  mockCockpitHalleyPayloads,
  new Date("2026-05-03T12:00:00Z"),
);

describe("CockpitHalley", () => {
  it("renders the executive scientific cockpit with separated fronts", () => {
    render(<CockpitHalley data={cockpitData} />);

    expect(screen.queryByRole("heading", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Laboratório científico de teses — motor Halley"),
    ).toBeInTheDocument();
    expect(screen.queryByText("UI rev soul-4")).not.toBeInTheDocument();
    expect(screen.queryByText(/Atualizado em/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Cockpit Halley")).not.toBeInTheDocument();
    expect(screen.getByText("Teses testadas")).toBeInTheDocument();
    expect(screen.getByText("Validação histórica")).toBeInTheDocument();
    expect(screen.getByText("Expectância líquida")).toBeInTheDocument();
    expect(screen.getByText("B3")).toBeInTheDocument();
    expect(screen.getByText("Cripto")).toBeInTheDocument();
    expect(screen.getByText("Imóveis")).toBeInTheDocument();
    expect(screen.getByText("Cobertura de dados")).toBeInTheDocument();
    expect(screen.getByText("Mercado atualizado")).toBeInTheDocument();
    expect(screen.getAllByText(/Noticias/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Feed temporariamente/i)).not.toBeInTheDocument();
  });

  it("uses the required KPI accent colors from the design system", () => {
    render(<CockpitHalley data={cockpitData} />);

    const kpiCard = (label) => screen.getByText(label).parentElement.parentElement;
    const kpiValue = (label) => screen.getByText(label).parentElement.nextElementSibling;
    const kpiGlow = (label) => kpiCard(label).firstElementChild;

    expect(kpiCard("Teses testadas")).toHaveStyle({ borderTop: `2px solid ${C.sky}` });
    expect(kpiCard("Validação histórica")).toHaveStyle({ borderTop: `2px solid ${C.teal}` });
    expect(kpiCard("Expectância líquida")).toHaveStyle({ borderTop: `2px solid ${C.gold}` });
    expect(kpiCard("Planos em go-live")).toHaveStyle({ borderTop: `2px solid ${C.amber}` });
    expect(kpiCard("Aprendizados")).toHaveStyle({ borderTop: `2px solid ${C.purple}` });
    expect(kpiValue("Validação histórica")).toHaveStyle({ color: C.teal });
    expect(kpiGlow("Validação histórica").getAttribute("style")).toContain("radial-gradient");
  });

  it("separates active plans from covered assets in the dashboard wording", () => {
    render(
      <CockpitHalley
        data={{
          scientificSummary: {
            testedTheses: 879,
            validatedPct: 76.34,
            expectancyPct: 3.01,
            goLiveCount: 8,
            goLiveAssetCount: 3,
            appliedLearningsCount: 3,
            learningCountLabel: "lições recentes",
          },
          fronts: [],
          activeTheses: [],
          learningLoops: [],
        }}
      />,
    );

    expect(screen.getByText("8 planos em go-live")).toBeInTheDocument();
    expect(screen.getAllByText("3 ativos cobertos").length).toBeGreaterThan(0);
    expect(screen.getByText("3 lições recentes")).toBeInTheDocument();
    expect(screen.queryByText("8 teses em go-live")).not.toBeInTheDocument();
  });

  it("warns when the current monitor is frozen instead of presenting stale plans as live", () => {
    render(
      <CockpitHalley
        data={{
          scientificSummary: {
            testedTheses: 879,
            validatedPct: 76.34,
            expectancyPct: 3.01,
            goLiveCount: 8,
            goLiveAssetCount: 3,
            appliedLearningsCount: 3,
            learningCountLabel: "li\u00e7\u00f5es recentes",
            monitorFrozen: true,
            goLiveLabel: "planos no \u00faltimo monitor",
            goLiveKpiLabel: "\u00daltimo monitor",
          },
          monitorTrust: {
            isFrozen: true,
            label: "Monitor congelado",
            message: "Monitor congelado por falta de dados frescos. Mantemos o \u00faltimo retrato para estudo; novas decis\u00f5es exigem atualiza\u00e7\u00e3o do feed.",
          },
          fronts: [],
          activeTheses: [
            {
              id: "TH-ETHUSDT-range-0001",
              front: "Cripto",
              asset: "ETHUSDT",
              direction: "Neutra",
              hypothesis: "Range reaproveitado do ultimo monitor.",
              entryPrice: 2361.92,
              currentPrice: 2369.53,
              targetPrice: 2361.92,
              stopPrice: 2326.49,
              priceReferenceLabel: "Faixa",
              expectedPct: 0,
              currentPct: 0.32,
              daysOpen: 0,
              hoursOpen: 17,
              openedAt: "2026-05-05T22:45:00Z",
              status: "monitoring",
              learning: "Revalidar quando o feed voltar.",
              janeState: "monitoring",
              janeMessage: "Retrato congelado por falta de dados frescos.",
              operation: "Iron Condor educativo com risco definido.",
              invalidation: "Recalcular antes de qualquer nova decisao.",
            },
          ],
          learningLoops: [],
        }}
      />,
    );

    expect(screen.getAllByText("Monitor congelado").length).toBeGreaterThan(0);
    expect(screen.getByText(/falta de dados frescos/i)).toBeInTheDocument();
    expect(screen.getByText("8 planos no \u00faltimo monitor")).toBeInTheDocument();
    expect(screen.getByText("\u00daltimo monitor")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "\u00daltimo monitor congelado" })).toBeInTheDocument();
    expect(screen.queryByText("8 planos em go-live")).not.toBeInTheDocument();
    expect(screen.queryByText("Planos em go-live")).not.toBeInTheDocument();
  });

  it("keeps thesis details collapsed until the card is clicked", async () => {
    const user = userEvent.setup();
    render(<CockpitHalley data={cockpitData} />);

    expect(
      screen.queryByText(/Volume confirmado acima da média/i),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Tese B3-001 PETR4/i }));

    expect(screen.getByText(/Volume confirmado acima da média/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Tese B3-001 PETR4/i }));

    expect(
      screen.queryByText(/Volume confirmado acima da média/i),
    ).not.toBeInTheDocument();
  });
});
