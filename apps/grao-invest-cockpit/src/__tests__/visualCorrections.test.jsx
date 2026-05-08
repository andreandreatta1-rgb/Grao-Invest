import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Backtest from "../screens/Backtest.jsx";
import CockpitHalley from "../screens/CockpitHalley.jsx";
import Mercado from "../screens/Mercado.jsx";
import Metodo from "../screens/Metodo.jsx";
import Risco from "../screens/Risco.jsx";
import Teses from "../screens/Teses.jsx";
import { C } from "../components";

describe("targeted visual and data corrections", () => {
  it("keeps the Dashboard cockpit tall enough for the Patrick Jane portrait", () => {
    render(
      <CockpitHalley
        data={{
          scientificSummary: {
            testedTheses: 1727,
            validatedPct: 67.52,
            expectancyPct: 2.68,
            goLiveCount: 3,
            appliedLearningsCount: 18,
          },
        }}
      />,
    );

    const image = screen.getByAltText("Patrick Jane");
    expect(screen.getByTestId("patrick-jane-visual")).toHaveStyle({ aspectRatio: "16 / 9" });
    expect(image).toHaveStyle({ height: "100%", objectFit: "contain", width: "100%" });
    expect(screen.getByText(/Placar cient/i).closest("section")).toHaveStyle({
      minHeight: "330px",
    });
  });

  it("expands an odd Dashboard learning card across the full grid width", () => {
    render(
      <CockpitHalley
        data={{
          scientificSummary: {
            testedTheses: 1727,
            validatedPct: 67.52,
            expectancyPct: 2.68,
            goLiveCount: 3,
            appliedLearningsCount: 18,
          },
          learningLoops: [
            { pain: "Dor 1", remedy: "Remedio 1", expectedImpact: "Impacto 1" },
            { pain: "Dor 2", remedy: "Remedio 2", expectedImpact: "Impacto 2" },
            { pain: "Dor 3", remedy: "Remedio 3", expectedImpact: "Impacto 3" },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("dashboard-learning-2")).toHaveStyle({
      gridColumn: "1 / -1",
    });
  });

  it("keeps the Dashboard thesis status badge on the same header row as the asset", () => {
    render(
      <CockpitHalley
        data={{
          scientificSummary: {},
          activeTheses: [
            {
              id: "IM-001",
              front: "Im\u00f3veis",
              asset: "GalpÃ£o logÃ­stico Campinas",
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
        }}
      />,
    );

    expect(screen.getByTestId("thesis-card-header-IM-001")).toHaveStyle({ flexWrap: "nowrap" });
    expect(screen.getByTestId("thesis-card-asset-IM-001")).toHaveStyle({
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    });
  });

  it("renders the thesis exit rule as a readable operational criterion", () => {
    render(
      <Teses
        data={{
          thesisRows: [
            {
              id: 1570,
              asset: "PETR4",
              front: "B3",
              direction: "Alta",
              expectedPct: 4.82,
              structure: "Compra estruturada",
              entryPrice: 39.92,
              targetPrice: 42.48,
              stopPrice: 36.88,
              outcome: "Observando",
              days: 4,
              statusGroup: "Go-live",
              resultPct: 2.36,
              hypothesis: "Hipotese em acompanhamento.",
              learning: "Aprendizado em coleta.",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Abrir arquivo completo/i }));

    const cell = screen.getByText((content) => content.includes("alvo R$ 42,48") && content.includes("stop R$ 36,88"));
    expect(cell).toHaveStyle({
      color: C.text,
      fontWeight: "700",
    });
    expect(screen.getAllByText("PETR4")[0]).toHaveStyle({ minWidth: "120px", whiteSpace: "nowrap" });
    const resultadoHeader = screen.getAllByText("Resultado").find((element) => element.tagName === "TH");
    expect(resultadoHeader).toHaveStyle({ fontSize: "7px" });
    expect(screen.getByTestId("teses-table-wrapper")).toHaveStyle({ overflowX: "auto" });
    expect(document.querySelectorAll("col")[3]).toHaveStyle({ width: "132px" });
  });

  it("shows each thesis as an operational plan with reason, dates and exit criteria", () => {
    render(
      <Teses
        data={{
          thesisRows: [
            {
              id: 1571,
              asset: "BTCUSDT",
              front: "Cripto",
              direction: "Neutra",
              expectedPct: 0.84,
              operation: "Iron Condor em range",
              structure: "Iron Condor com risco definido",
              entryPrice: 81212.04,
              targetPrice: 82400,
              stopPrice: 79800,
              exitRule: "Sai por alvo, stop ou tempo de 48h",
              outcome: "Observando",
              days: 0,
              statusGroup: "Go-live",
              resultPct: 2.4,
              openedAt: "2026-05-06T12:00:00Z",
              hypothesis: "Range estatistico respeitado com volatilidade suficiente para vender premio.",
              learning: "Monitorar se o range quebra antes do vencimento.",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Abrir arquivo completo/i }));

    expect(screen.getByText("Mapa operacional das teses")).toBeInTheDocument();
    expect(screen.getByText("Tese e motivo")).toBeInTheDocument();
    expect(screen.getByText("Operação e entrada")).toBeInTheDocument();
    expect(screen.getByText("Critério de saída")).toBeInTheDocument();
    expect(screen.getByText("Estado da tese")).toBeInTheDocument();
    expect(screen.getByTestId("teses-row-1571")).toHaveTextContent("Range estatistico respeitado");
    expect(screen.getByTestId("teses-row-1571")).toHaveTextContent("Iron Condor em range");
    expect(screen.getByTestId("teses-row-1571")).toHaveTextContent("06/05/2026");
    expect(screen.getByTestId("teses-row-1571")).toHaveTextContent("Sai por alvo, stop ou tempo de 48h");
    expect(screen.getByTestId("teses-row-1571")).toHaveTextContent("Hoje");
  });

  it("opens discarded real estate theses in the decision map instead of realized-results KPIs", () => {
    render(
      <Teses
        data={{
          thesisRows: [
            {
              id: 1880,
              asset: "REAL - Caixa TatuapÃ©",
              front: "Im\u00f3veis",
              direction: "Descartada",
              expectedPct: -15.9,
              structure: "Radar imobiliÃ¡rio",
              entryPrice: 142000,
              exitRule: "Confirmar ocupaÃ§Ã£o",
              outcome: "PendÃªncias abertas",
              days: 0,
              status: "Fechada",
              statusGroup: "HistÃ³rica",
              resultPct: -15.9,
              resultKind: "estimate",
              isOpen: false,
              hypothesis: "Radar imobiliÃ¡rio com ocupaÃ§Ã£o pendente.",
              learning: "Candidato descartado pelo radar.",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Abrir tese em atenção Caixa Tatuap/i }));

    expect(screen.getAllByText("Descartada").length).toBeGreaterThan(0);
    expect(screen.queryByText(/REAL - Caixa/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("real-estate-decision-map")).toBeInTheDocument();
    expect(screen.getByText(/Este im.vel deve avan.ar/i)).toBeInTheDocument();
    expect(screen.queryByText("Resultado vs esperado")).not.toBeInTheDocument();
    expect(screen.getByText(/Preço em validação/i)).toBeInTheDocument();
  });

  it("renders the complete real estate analysis dossier in the thesis detail", () => {
    render(
      <Teses
        data={{
          thesisRows: [
            {
              id: 1888,
              asset: "REAL - VivaReal Colonia",
              front: "Im\u00f3veis",
              direction: "Descartada",
              expectedPct: -31.92,
              structure: "House flipping com comparÃ¡veis",
              entryPrice: 215000,
              currentPrice: 240000,
              exitRule: "Rever preco maximo ou descartar",
              outcome: "Descartado pelo radar",
              days: 0,
              status: "Fechada",
              statusGroup: "HistÃ³rica",
              resultPct: -31.92,
              resultKind: "estimate",
              isOpen: false,
              sourceUrl: "https://example.com/imovel",
              hypothesis: "Radar imobiliÃ¡rio com preÃ§o acima do teto.",
              learning: "Candidato descartado pelo radar.",
              realEstateAnalysis: {
                score: 63,
                confidence: 51,
                suggested_status: "Descartado",
                next_action: "Rever preco maximo ou descartar",
                price_ceiling_status: "Acima do teto",
                max_purchase_price: 160400,
                price_gap_to_ceiling: 54600,
                cash_needed: 78000,
                breakeven_sale_price: 266489.36,
                target_roi_pct: 20,
                base_profit_pct: -11.58,
                scenarios: {
                  conservative: { sale_price: 225000, net_profit: -39000, roi_pct: -50 },
                  base: { sale_price: 240000, net_profit: -24900, roi_pct: -31.92 },
                  optimistic: { sale_price: 252000, net_profit: -13620, roi_pct: -17.46 },
                },
                pending_items: [
                  { priority: "P0", title: "Confirmar ocupaÃ§Ã£o", action: "Validar com fonte oficial." },
                  { priority: "P1", title: "Buscar 3 comparÃ¡veis de venda", action: "Usar comparÃ¡veis prÃ³ximos." },
                ],
                clarified_items: [
                  { title: "OrÃ§amento de reforma informado", detail: "OrÃ§amento de R$ 18.000,00." },
                ],
                score_breakdown: [
                  { label: "Liquidez/localizaÃ§Ã£o", points: 12, max_points: 20, detail: "Ãndice informado/estimado: 60/100." },
                ],
                confidence_breakdown: [
                  { label: "OcupaÃ§Ã£o confirmada", points: 0, max_points: 15, status: "pendente", detail: "OcupaÃ§Ã£o desconhecida." },
                ],
              },
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByText("VivaReal Colonia"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).queryByAltText("Patrick Jane")).not.toBeInTheDocument();
    const janeInsight = within(drawer).getByText(/Coment.rio sobre o im.vel selecionado/i).closest("section");
    expect(janeInsight).toBeInTheDocument();
    expect(janeInsight.textContent).not.toMatch(/go-live|histÃ³rico/i);
    expect(screen.getByTestId("real-estate-score-hero")).toBeInTheDocument();
    expect(screen.getByTestId("real-estate-score-gauge").querySelector("svg")).not.toBeNull();
    expect(screen.getByTestId("real-estate-confidence-gauge").querySelector("svg")).not.toBeNull();
    expect(screen.getByTestId("real-estate-score-value")).toHaveAttribute("font-size", "24");
    expect(screen.getByTestId("real-estate-score-value")).toHaveTextContent("63");
    expect(screen.getByTestId("real-estate-confidence-value")).toHaveTextContent("51");
    expect(screen.getByText(/Decis.o do Radar/i).closest("section")).toHaveStyle({
      borderTop: `2px solid ${C.amber}`,
    });
    expect(screen.getByText(/Decis.o do Radar/i)).toBeInTheDocument();
    expect(screen.getByText("Status sugerido")).toBeInTheDocument();
    expect(screen.getAllByText("Descartado").length).toBeGreaterThan(0);
    expect(screen.getByText(/Pend.ncias: 1 P0 bloqueia decis.o, 1 P1 melhora an.lise\./i)).toBeInTheDocument();
    expect(screen.getByText(/Score e Confian.a/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Score e Confian.a/i)).toHaveLength(1);
    expect(screen.getAllByText("Score do candidato").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Confian.a da an.lise/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/N.meros da Opera..o/i)).toBeInTheDocument();
    expect(screen.getByText(/Pre.o m.ximo de compra/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Cen.rios/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Conservador")).toBeInTheDocument();
    expect(screen.getByText(/Pend.ncias abertas/i)).toBeInTheDocument();
    expect(screen.getByText("Confirmar ocupaÃ§Ã£o")).toBeInTheDocument();
    expect(screen.getAllByText(/Bloqueia decis.o/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Pontos j. esclarecidos/i)).toBeInTheDocument();
    expect(screen.getByText(/Composi..o do Score/i)).toBeInTheDocument();
    expect(screen.getByTestId("score-breakdown-card-0")).toHaveTextContent(/Liquidez\/localiza/i);
    expect(screen.getByTestId("score-breakdown-card-0")).toHaveTextContent("12/20");
    expect(screen.getByText(/Composi..o da Confian.a/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir fonte do im.vel/i })).toHaveAttribute("href", "https://example.com/imovel");
  });

  it("gives compact market confidence meters room for the percentage before the status badge", () => {
    render(<Mercado />);

    const btcMeter = screen.getByTestId("confidence-meter-BTCUSDT");
    expect(btcMeter).toHaveStyle({ minWidth: "0px", width: "100%" });
    expect(screen.getByText("84%")).toBeInTheDocument();
  });

  it("does not let raw pattern counts override forced Cripto confidence values", () => {
    render(
      <Mercado
        data={{
          marketAssets: [
            { asset: "BTCUSDT", front: "Cripto", price: 63800, dayPct: 2.24, weekPct: 7.37, patterns: 2, status: "monitorando", activeTheses: 1 },
            { asset: "ETHUSDT", front: "Cripto", price: 3200, dayPct: -0.8, weekPct: 2.1, patterns: 3, status: "atenÃ§Ã£o", activeTheses: 0 },
            { asset: "SOLUSDT", front: "Cripto", price: 145, dayPct: 4.1, weekPct: 5.4, patterns: 1, status: "candidato", activeTheses: 0 },
          ],
        }}
      />,
    );

    expect(within(screen.getByTestId("confidence-meter-BTCUSDT")).getByText("84%")).toBeInTheDocument();
    expect(within(screen.getByTestId("confidence-meter-ETHUSDT")).getByText("71%")).toBeInTheDocument();
    expect(within(screen.getByTestId("confidence-meter-SOLUSDT")).getByText("56%")).toBeInTheDocument();
    expect(screen.getAllByText("1 TESE").length).toBeGreaterThan(0);
    expect(screen.getByTestId("thesis-count-BTCUSDT")).toHaveStyle({ minWidth: "58px", whiteSpace: "nowrap" });
  });

  it("uses the consolidated historical calibration gap without implying perfect approval", () => {
    render(
      <Backtest
        data={{
          backtest: {
            calibrations: [
              {
                id: 1,
                data: "histÃ³rico",
                teses: 1727,
                esperado: 4.43,
                alcancado: 2.68,
                aprovadas: 1768,
              },
            ],
          },
        }}
      />,
    );

    const evidence = screen.getByTestId("audit-evidence-1");
    expect(within(evidence).getByText("histÃ³rico")).toBeInTheDocument();
    expect(within(evidence).getByText(/1,02pp/)).toBeInTheDocument();
    expect(within(evidence).getAllByText(/regra ajustada/i).length).toBeGreaterThan(0);
    expect(screen.queryByText("1.708")).not.toBeInTheDocument();
  });

  it("renders the validation evolution line chart with an explicit height", () => {
    const { container } = render(<Backtest />);

    expect(screen.getByTestId("calibration-evolution-chart")).toHaveStyle({ minHeight: "260px" });
    expect(container.querySelector(".recharts-line")).not.toBeNull();
  });

  it("uses a subtle rounded coral border on Patrick Jane in Risco", () => {
    render(<Risco />);

    const style = screen.getByAltText("Patrick Jane").getAttribute("style");
    expect(style).toContain("border-radius: 12px");
    expect(style).toContain("border: 2px solid rgba(255, 94, 94, 0.3)");
  });

  it("uses the nine-scene Metodo player instead of the old five-step strip", () => {
    render(<Metodo />);

    expect(screen.getByTestId("metodo-media-stage")).toBeInTheDocument();
    expect(within(screen.getByTestId("metodo-scene-navigator")).getAllByRole("button")).toHaveLength(9);
    expect(screen.queryByTestId("method-step-01")).not.toBeInTheDocument();
  });
});
