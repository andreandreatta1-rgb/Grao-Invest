import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Teses from "../screens/Teses.jsx";

const thesisRows = [
  {
    id: "B3-001",
    thesisId: "B3-001",
    asset: "PETR4",
    front: "B3",
    direction: "Alta",
    expectedPct: 4.82,
    structure: "Compra estruturada com alvo e stop",
    entryPrice: 39.92,
    currentPrice: 40.86,
    targetPrice: 43.37,
    stopPrice: 38.83,
    exitRule: "alvo R$ 43,37 / stop R$ 38,83",
    outcome: "Observando",
    days: 13,
    status: "Observando",
    statusGroup: "Go-live",
    resultPct: 2.36,
    isOpen: true,
    hypothesis: "A hipotese sugere continuidade de alta com suporte respeitado.",
    learning: "Exigir confirmacao de volume no fechamento.",
  },
  {
    id: "CR-001",
    thesisId: "CR-001",
    asset: "BTCUSDT",
    front: "Cripto",
    direction: "Alta",
    expectedPct: 7.37,
    structure: "Compra com alvo parcial e stop fixo",
    entryPrice: 62400,
    currentPrice: 63800,
    targetPrice: 67000,
    stopPrice: 60400,
    exitRule: "alvo USDT 67000 / stop USDT 60400",
    outcome: "Validada",
    days: 3,
    status: "Validada",
    statusGroup: "Go-live",
    resultPct: 2.24,
    isOpen: true,
    hypothesis: "O ciclo aponta recuperacao apos sustentacao acima da media curta.",
    learning: "Alvo parcial reduz ruido quando o movimento ocorre rapido demais.",
  },
  {
    id: "IM-OPEN",
    thesisId: "IM-RADAR-101",
    asset: "REAL - Caixa Portal Cantareira apto 42 BL01",
    front: "Im\u00f3veis",
    direction: "Alta",
    expectedPct: 62.08,
    structure: "Leilao / venda online Caixa",
    entryPrice: 114838.57,
    currentPrice: 186100,
    sourceUrl: "https://www.caixa.gov.br/imoveis/imovel-aberto",
    openedAt: "2026-05-04T10:00:00.000Z",
    exitRule: "Confirmar ocupacao, matricula e debitos",
    outcome: "Pendencias abertas",
    days: 0,
    status: "Aberta - Atencao",
    statusGroup: "Em an\u00e1lise",
    resultPct: 0,
    resultKind: "estimate",
    isOpen: true,
    hypothesis: "Imovel com desconto potencial frente a comparaveis.",
    learning: "Confirmar pendencias antes de qualquer proposta.",
    realEstateAnalysis: {
      score: 63,
      confidence: 51,
      suggested_status: "Estudar com cautela",
      next_action: "Confirmar ocupacao, matricula e debitos",
      price_ceiling_status: "Acima do teto",
      max_purchase_price: 108000,
      price_gap_to_ceiling: 6838.57,
      cash_needed: 23000,
      breakeven_sale_price: 150000,
      target_roi_pct: 18,
      base_profit_pct: 12,
      scenarios: {
        conservative: { sale_price: 150000, net_profit: 8000, roi_pct: 7 },
        base: { sale_price: 186100, net_profit: 22000, roi_pct: 12 },
        optimistic: { sale_price: 205000, net_profit: 35000, roi_pct: 19 },
      },
      pending_items: [
        { key: "occupancy", priority: "P0", title: "Confirmar ocupacao", action: "Validar com fonte oficial." },
      ],
      clarified_items: [],
      score_breakdown: [],
      confidence_breakdown: [],
    },
  },
  {
    id: "IM-DISC",
    thesisId: "IM-RADAR-102",
    asset: "REAL - Lancamento Plano Estacao Belem",
    front: "Im\u00f3veis",
    direction: "Baixa",
    expectedPct: -4.5,
    structure: "Compra direta fora do teto",
    entryPrice: 250000,
    currentPrice: 220000,
    sourceUrl: "https://www.exemplo.com/imovel-descartado",
    openedAt: "2026-05-01T10:00:00.000Z",
    exitRule: "Descartar se preco ficar acima do teto",
    outcome: "Descartado pelo radar",
    days: 2,
    status: "Descartada",
    statusGroup: "Hist\u00f3rica",
    resultPct: -4.5,
    resultKind: "estimate",
    isOpen: false,
    hypothesis: "O preco pedido ficou acima do teto calculado.",
    learning: "Registrar descarte quando o teto nao fecha.",
    realEstateAnalysis: {
      score: 41,
      confidence: 33,
      suggested_status: "Descartado",
      next_action: "Rever apenas se o preco cair",
      price_ceiling_status: "Acima do teto",
      pending_items: [],
      clarified_items: [],
      score_breakdown: [],
      confidence_breakdown: [],
    },
  },
];

function renderTeses(extraProps = {}) {
  return render(
    <Teses
      data={{
        scientificSummary: { lastUpdatedAt: "2026-05-04T10:00:00.000Z" },
        thesisRows,
      }}
      feedStatus="live"
      {...extraProps}
    />,
  );
}

function openArchiveAndRow(rowId) {
  fireEvent.click(within(screen.getByTestId("decision-desk")).getByRole("button", { name: /Abrir lista completa/i }));
  fireEvent.click(screen.getByTestId(`teses-row-${rowId}`));
  return screen.getByText("Ficha completa da tese").closest("aside");
}

describe("Teses M4 complete experience", () => {
  afterEach(() => {
    Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: 1024 });
  });

  it("shows an operational B3 dossier instead of the generic two-card detail", () => {
    renderTeses();

    const drawer = openArchiveAndRow("B3-001");

    expect(within(drawer).getByText("Plano operacional B3")).toBeInTheDocument();
    expect(within(drawer).getByText("Entrada planejada")).toBeInTheDocument();
    expect(within(drawer).getByText("Alvo t\u00e9cnico")).toBeInTheDocument();
    expect(within(drawer).getByText("Stop do plano")).toBeInTheDocument();
    expect(within(drawer).getByText("Ciclo Halley")).toBeInTheDocument();
  });

  it("shows a crypto 24/7 dossier with liquidity and volatility context", () => {
    renderTeses();

    const drawer = openArchiveAndRow("CR-001");

    expect(within(drawer).getByText("Mesa cripto 24/7")).toBeInTheDocument();
    expect(within(drawer).getByText("Pre\u00e7o agora")).toBeInTheDocument();
    expect(within(drawer).getByText("Volatilidade")).toBeInTheDocument();
    expect(within(drawer).getByText("Liquidez")).toBeInTheDocument();
    expect(within(drawer).getByText("Janela do ciclo")).toBeInTheDocument();
  });

  it("makes the official data origin visible on the thesis screen", () => {
    renderTeses();

    expect(screen.getByText("Origem dos dados")).toBeInTheDocument();
    expect(screen.getByText("API real")).toBeInTheDocument();
    expect(screen.getByText("/api/dashboard/summary/1")).toBeInTheDocument();
    expect(screen.getByText("thesis_open_operations")).toBeInTheDocument();
  });

  it("prioritizes fronts and objectives without the old view tabs", () => {
    renderTeses();

    expect(screen.queryByRole("navigation", { name: "Vis\u00f5es de teses" })).not.toBeInTheDocument();
    expect(screen.getByText("Frentes e objetivos")).toBeInTheDocument();
    expect(screen.getByText("Mapa de oportunidades")).toBeInTheDocument();

    const objectives = screen.getByText("Mapa de oportunidades");
    const decisionDesk = screen.getByTestId("decision-desk");

    expect(objectives.compareDocumentPosition(decisionDesk) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("uses a mobile-friendly thesis detail marker on narrow screens", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: 760 });
    renderTeses();

    openArchiveAndRow("B3-001");

    expect(screen.getByTestId("teses-detail-mobile")).toBeInTheDocument();
  });
});
