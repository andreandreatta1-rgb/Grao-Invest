import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FrontCard } from "../components";
import Teses from "../screens/Teses.jsx";

const baseRows = [
  {
    id: "B3-001",
    asset: "PETR4",
    front: "B3",
    direction: "Alta",
    expectedPct: 4.82,
    structure: "Compra estruturada",
    entryPrice: 39.92,
    targetPrice: 43.37,
    stopPrice: 38.83,
    outcome: "Observando",
    days: 13,
    statusGroup: "Go-live",
    resultPct: 3.14,
    hypothesis: "Hipotese B3 em acompanhamento.",
    learning: "Aprendizado B3.",
  },
  {
    id: "IM-010",
    asset: "Apartamento Vila Mariana",
    front: "Imóveis",
    direction: "Alta",
    expectedPct: 12.4,
    structure: "Radar imobiliario com margem de seguranca",
    entryPrice: 640000,
    currentPrice: 710000,
    exitRule: "Confirmar matricula e ocupacao",
    outcome: "Observando",
    days: 0,
    status: "Observando",
    statusGroup: "Em análise",
    resultPct: 0,
    resultKind: "performance",
    isOpen: true,
    hypothesis: "Imovel com desconto potencial frente a comparaveis.",
    learning: "Aguardando documentos antes de qualquer proposta.",
    realEstateAnalysis: {
      score: 63,
      confidence: 51,
      suggested_status: "Estudar com cautela",
      next_action: "Confirmar ocupacao, matricula e debitos",
      price_ceiling_status: "Dentro do teto",
      max_purchase_price: 615000,
      price_gap_to_ceiling: 25000,
      cash_needed: 128000,
      breakeven_sale_price: 690000,
      target_roi_pct: 20,
      base_profit_pct: 12.4,
      scenarios: {
        conservative: { sale_price: 660000, net_profit: 12000, roi_pct: 9.4 },
        base: { sale_price: 710000, net_profit: 15872, roi_pct: 12.4 },
        optimistic: { sale_price: 760000, net_profit: 31000, roi_pct: 24.2 },
      },
      pending_items: [
        { priority: "P0", title: "Confirmar ocupacao", action: "Validar com fonte oficial." },
        { priority: "P0", title: "Baixar matricula", action: "Checar onus e titularidade." },
        { priority: "P1", title: "Buscar comparaveis", action: "Coletar tres vendas recentes." },
      ],
      clarified_items: [{ title: "Regiao mapeada", detail: "Liquidez local com demanda consistente." }],
      score_breakdown: [{ label: "Liquidez/localizacao", points: 12, max_points: 20, detail: "Indice 60/100." }],
      confidence_breakdown: [{ label: "Ocupacao confirmada", points: 0, max_points: 15, status: "pendente", detail: "Ainda falta evidência." }],
    },
  },
  {
    id: "H-001",
    asset: "VALE3",
    front: "B3",
    direction: "Alta",
    expectedPct: 3.2,
    structure: "Historica",
    entryPrice: 70.1,
    targetPrice: 72.34,
    stopPrice: 68.75,
    outcome: "Validada",
    days: 7,
    statusGroup: "Histórica",
    resultPct: 3.38,
    hypothesis: "Historica 1.",
    learning: "Aprendizado historico.",
  },
  {
    id: "H-002",
    asset: "MGLU3",
    front: "B3",
    direction: "Baixa",
    expectedPct: 5.44,
    structure: "Historica",
    entryPrice: 9.72,
    targetPrice: 9.19,
    stopPrice: 10.05,
    outcome: "Stop",
    days: 4,
    statusGroup: "Histórica",
    resultPct: -1.7,
    hypothesis: "Historica 2.",
    learning: "Aprendizado historico.",
  },
  {
    id: "H-003",
    asset: "BTCUSDT",
    front: "Cripto",
    direction: "Alta",
    expectedPct: 7.37,
    structure: "Historica",
    entryPrice: 62400,
    targetPrice: 67000,
    stopPrice: 60400,
    outcome: "Validada",
    days: 2,
    statusGroup: "Histórica",
    resultPct: 7.37,
    hypothesis: "Historica 3.",
    learning: "Aprendizado historico.",
  },
  {
    id: "H-004",
    asset: "ITUB4",
    front: "B3",
    direction: "Alta",
    expectedPct: 2.9,
    structure: "Historica",
    entryPrice: 32.1,
    targetPrice: 33.04,
    stopPrice: 31.5,
    outcome: "Tempo",
    days: 9,
    statusGroup: "Histórica",
    resultPct: 1.2,
    hypothesis: "Historica 4.",
    learning: "Aprendizado historico.",
  },
  {
    id: "H-005",
    asset: "WEGE3",
    front: "B3",
    direction: "Alta",
    expectedPct: 2.4,
    structure: "Historica",
    entryPrice: 38,
    targetPrice: 38.91,
    stopPrice: 37.2,
    outcome: "Tempo",
    days: 11,
    statusGroup: "Histórica",
    resultPct: 0.8,
    hypothesis: "Historica 5.",
    learning: "Aprendizado historico.",
  },
];

describe("M1-M10 user experience improvements", () => {
  it("shows the fronts validation bar as a labelled metric with last update context", () => {
    render(
      <FrontCard
        front={{
          id: "real_estate",
          label: "Imóveis",
          tested: 38,
          radarTotal: 38,
          openCount: 31,
          closedCount: 7,
          goLive: 31,
          countingPolicy: "radar_candidates",
          validatedPct: 0,
          status: "atualizado",
          lastUpdatedAt: "2026-05-03T09:30:00Z",
        }}
      />,
    );

    expect(screen.getByTestId("front-radar-Imóveis")).toHaveTextContent("Contrato do radar · 38 = 31 abertos + 7 encerrados");
    expect(screen.getByTestId("front-update-Imóveis")).toHaveTextContent("Base atualizada em 03/05/2026");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "81.57894736842105");
    expect(screen.getByText("No radar")).toBeInTheDocument();
  });

  it("adds counters to thesis filters and keeps table identifiers sticky during horizontal scroll", () => {
    render(<Teses data={{ thesisRows: baseRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir lista completa/i }));

    expect(screen.getByText("Go-live (1)")).toBeInTheDocument();
    expect(screen.getByText("Histórica (5)")).toBeInTheDocument();
    expect(screen.getByText("Em análise (1)")).toBeInTheDocument();
    expect(screen.getByText("B3 (5)")).toBeInTheDocument();
    expect(screen.getByText("Cripto (1)")).toBeInTheDocument();
    expect(screen.getByText("Imóveis (1)")).toBeInTheDocument();
    expect(screen.getByTestId("teses-header-id")).toHaveStyle({ position: "sticky", left: "0px" });
    expect(screen.getByTestId("teses-header-asset")).toHaveStyle({ position: "sticky", left: "70px" });
    expect(screen.getByTestId("teses-cell-id-IM-010")).toHaveStyle({ position: "sticky", left: "0px" });
    expect(screen.getByTestId("teses-cell-asset-IM-010")).toHaveStyle({ position: "sticky", left: "70px" });
  });

  it("uses compact table labels for long real estate decisions without changing the detail meaning", () => {
    render(<Teses data={{ thesisRows: baseRows }} />);

    expect(screen.getByTestId("direction-badge-IM-010")).toHaveTextContent("POT. POSITIVO");
    fireEvent.click(screen.getByTestId("teses-row-IM-010"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Score do candidato")).toBeInTheDocument();
    expect(within(drawer).getAllByText(/Estudar com cautela/i).length).toBeGreaterThan(0);
  });

  it("places a decision mind map at the top of the real estate thesis detail", () => {
    render(<Teses data={{ thesisRows: baseRows }} />);

    fireEvent.click(screen.getByTestId("teses-row-IM-010"));

    const map = screen.getByTestId("real-estate-decision-map");
    expect(map).toHaveTextContent("Este imóvel deve avançar?");
    expect(map).toHaveTextContent("Estudar com cautela");
    expect(map).toHaveTextContent("Confirmar ocupacao, matricula e debitos");
    expect(map).toHaveTextContent("2 P0");
    expect(map).toHaveTextContent("1 P1");
    expect(map.textContent).not.toMatch(/go-live/i);
  });
});
