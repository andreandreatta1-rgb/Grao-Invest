import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Aprendizado, { gapData } from "../screens/Aprendizado.jsx";
import Backtest from "../screens/Backtest.jsx";
import CockpitHalley from "../screens/CockpitHalley.jsx";
import Mercado from "../screens/Mercado.jsx";
import Metodo from "../screens/Metodo.jsx";
import Risco from "../screens/Risco.jsx";
import Teses from "../screens/Teses.jsx";

describe("review round corrections", () => {
  it("keeps Dashboard Patrick Jane readable and constrains long go-live asset names", () => {
    render(
      <CockpitHalley
        data={{
          scientificSummary: {
            testedTheses: 1727,
            validatedPct: 67.52,
            expectancyPct: 2.68,
            goLiveCount: 1,
            appliedLearningsCount: 3,
          },
          activeTheses: [
            {
              id: "IM-001",
              front: "Imóveis",
              asset: "Galpão logístico Campinas",
              direction: "Alta",
              entryPrice: 850000,
              targetPrice: 910000,
              stopPrice: 820000,
              expectedPct: 7.06,
              currentPct: 0,
              daysOpen: 4,
              status: "analysis",
            },
          ],
          learningLoops: [
            { pain: "Dor 1", remedy: "Remédio 1", expectedImpact: "Impacto 1" },
            { pain: "Dor 2", remedy: "Remédio 2", expectedImpact: "Impacto 2" },
            { pain: "Dor 3", remedy: "Remédio 3", expectedImpact: "Impacto 3" },
          ],
        }}
      />,
    );

    expect(screen.getByAltText("Patrick Jane")).toHaveStyle({ height: "100%", objectFit: "contain" });
    expect(screen.getByTestId("thesis-card-asset-IM-001")).toHaveStyle({
      maxWidth: "130px",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    });
    expect(screen.getByTestId("dashboard-learning-2")).toHaveStyle({ gridColumn: "1 / -1" });
  });

  it("keeps the thesis table inside the card without clipping the Resultado header", () => {
    render(
      <Teses
        data={{
          thesisRows: [
            {
              id: 1570,
              asset: "Galpão logístico Campinas",
              front: "Imóveis",
              direction: "Alta",
              expectedPct: 7.06,
              structure: "Tese imobiliária com margem de segurança",
              entryPrice: 850000,
              targetPrice: 910000,
              stopPrice: 820000,
              outcome: "Observando",
              days: 18,
              statusGroup: "Go-live",
              resultPct: 2.1,
              hypothesis: "Hipótese imobiliária em acompanhamento.",
              learning: "Aprendizado em coleta.",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Abrir lista completa/i }));

    expect(screen.getByTestId("teses-table-wrapper")).toHaveStyle({ overflowX: "auto" });
    const resultadoHeader = screen.getAllByText("Resultado").find((element) => element.tagName === "TH");
    expect(resultadoHeader).toHaveStyle({ padding: "7px 8px", fontSize: "7px" });
  });

  it("keeps compact market thesis badges untruncated", () => {
    render(<Mercado />);

    const btcBadge = screen.getByTestId("thesis-count-BTCUSDT");
    expect(btcBadge).toHaveStyle({ minWidth: "58px", whiteSpace: "nowrap" });
    expect(within(btcBadge).getByText("1 TESE")).toBeInTheDocument();
  });

  it("locks the consolidated historical calibration gap and rule adjustment", () => {
    render(
      <Backtest
        data={{
          backtest: {
            calibrations: [
              { id: 1, data: "Cal.18", teses: 879, esperado: 4.12, alcancado: 3.01, aprovadas: 869 },
            ],
          },
        }}
      />,
    );

    const evidence = screen.getByTestId("audit-evidence-1");
    expect(within(evidence).getByText("Cal.18")).toBeInTheDocument();
    expect(within(evidence).getByText(/879 teses/)).toBeInTheDocument();
    expect(within(evidence).getAllByText(/regra ajustada/i).length).toBeGreaterThan(0);
    expect(screen.queryByText("1.708")).not.toBeInTheDocument();
    expect(within(evidence).getByText(/−1,11pp/)).toBeInTheDocument();
  });

  it("uses the correct risk exposure message and a subtle rounded PJ border", () => {
    render(<Risco data={{ risk: { exposurePct: 24, stopRespectPct: 100 } }} />);

    expect(screen.getByText(/A exposição está em 95% do limite operacional/)).toBeInTheDocument();
    const image = screen.getByAltText("Patrick Jane");
    expect(image).toHaveStyle({
      borderRadius: "12px",
      border: "2px solid rgba(255, 94, 94, 0.3)",
    });
  });

  it("connects all Aprendizado gap points with the coral line and visible dots", () => {
    expect(gapData).toEqual([
      { cal: "Cal.08", gap: 1.9 },
      { cal: "Cal.09", gap: 1.7 },
      { cal: "Cal.10", gap: 1.67 },
      { cal: "Cal.11", gap: 1.65 },
      { cal: "Cal.12", gap: 1.55 },
      { cal: "Cal.13", gap: 1.48 },
      { cal: "Cal.14", gap: 1.4 },
      { cal: "Cal.15", gap: 1.7 },
      { cal: "Cal.16", gap: 1.35 },
      { cal: "Cal.17", gap: 1.15 },
      { cal: "Cal.18", gap: 1.02 },
    ]);
    expect(gapData.every((point) => Number.isFinite(point.gap))).toBe(true);

    const { container } = render(<Aprendizado />);

    const curve = container.querySelector(".recharts-line-curve");
    expect(curve).not.toBeNull();
    expect(curve).toHaveAttribute("stroke", "#ff5e5e");
    expect(curve).toHaveAttribute("stroke-width", "2.5");
    expect(container.querySelectorAll(".recharts-line-dot")).toHaveLength(11);
  });

  it("uses numbered Method scenes instead of fragile emoji substitutions", () => {
    render(<Metodo />);

    expect(screen.getByText("01/09")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sem sinal vazio/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Grãos de evidência/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Grão Invest/i })).toBeInTheDocument();
  });
});
