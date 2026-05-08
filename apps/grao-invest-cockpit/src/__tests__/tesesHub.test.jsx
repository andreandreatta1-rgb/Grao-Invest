import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Teses from "../screens/Teses.jsx";

const rows = [
  {
    id: "B3-001",
    asset: "PETR4",
    front: "B3",
    direction: "Alta",
    expectedPct: 4.82,
    structure: "Compra estruturada com alvo e stop",
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
    id: "CR-001",
    asset: "BTCUSDT",
    front: "Cripto",
    direction: "Alta",
    expectedPct: 7.37,
    structure: "Compra com alvo parcial",
    entryPrice: 62400,
    targetPrice: 67000,
    stopPrice: 60400,
    outcome: "Validada",
    days: 2,
    statusGroup: "Go-live",
    resultPct: 7.37,
    hypothesis: "Hipotese cripto em acompanhamento.",
    learning: "Aprendizado cripto.",
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
    outcome: "Pendências abertas",
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
      pending_items: [
        { priority: "P0", title: "Confirmar ocupacao", action: "Validar com fonte oficial." },
        { priority: "P1", title: "Buscar comparaveis", action: "Coletar tres vendas recentes." },
      ],
      clarified_items: [],
      score_breakdown: [],
      confidence_breakdown: [],
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
    hypothesis: "Historica.",
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
    hypothesis: "Historica.",
    learning: "Aprendizado historico.",
  },
];

describe("Teses decision hub", () => {
  it("uses the canonical unique tested thesis count in the main KPI", () => {
    render(<Teses data={{ scientificSummary: { testedTheses: 879 }, thesisRows: rows }} />);

    expect(screen.getByText("Teses testadas únicas")).toBeInTheDocument();
    expect(screen.getByText("879")).toBeInTheDocument();
    expect(screen.queryByText("Teses mapeadas")).not.toBeInTheDocument();
  });

  it("opens in a summarized decision hub instead of the complete thesis archive", () => {
    render(<Teses data={{ thesisRows: rows }} />);

    expect(screen.getByText("Mapa de oportunidades")).toBeInTheDocument();
    expect(screen.getByText("Fila de atenção")).toBeInTheDocument();
    expect(screen.getByText("Acompanhamento ativo")).toBeInTheDocument();
    expect(screen.getByText("Arquivo histórico")).toBeInTheDocument();
    expect(screen.queryByTestId("teses-table")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Abrir arquivo completo/i }));

    expect(screen.getByText("Lista de teses")).toBeInTheDocument();
    expect(screen.getByTestId("teses-table")).toBeInTheDocument();
  });

  it("shows a decision desk before the user reaches the complete archive", () => {
    render(<Teses data={{ thesisRows: rows }} />);
    const desk = within(screen.getByTestId("decision-desk"));

    expect(screen.getByText("Mesa de decisão")).toBeInTheDocument();
    expect(screen.getByText("Decisões agora")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Abrir radar imobili.rio/i })).toBeInTheDocument();
    expect(desk.queryByRole("button", { name: /Abrir radar imobili.rio/i })).not.toBeInTheDocument();
    expect(desk.getByRole("button", { name: /Ver acompanhamento ativo/i })).toBeInTheDocument();
    expect(desk.getByRole("button", { name: /Abrir lista completa/i })).toBeInTheDocument();
    expect(screen.queryByTestId("teses-table")).not.toBeInTheDocument();
  });

  it("routes decision desk actions to the right thesis views", () => {
    render(<Teses data={{ thesisRows: rows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    expect(screen.getByRole("heading", { name: /Radar imobili.rio/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Voltar ao mapa/i }));
    fireEvent.click(within(screen.getByTestId("decision-desk")).getByRole("button", { name: /Ver acompanhamento ativo/i }));
    expect(screen.getByText("Acompanhamento ativo")).toBeInTheDocument();
    expect(screen.queryByText("Teses abertas")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Voltar ao mapa/i }));
    fireEvent.click(within(screen.getByTestId("decision-desk")).getByRole("button", { name: /Abrir lista completa/i }));
    expect(screen.getByText("Lista de teses")).toBeInTheDocument();
    expect(screen.getByTestId("teses-table")).toBeInTheDocument();
  });

  it("prioritizes active attention over historical stops from the decision desk", () => {
    const rowsWithHistoricalStopFirst = [rows[4], ...rows.slice(0, 4)];
    render(<Teses data={{ thesisRows: rowsWithHistoricalStopFirst }} />);

    fireEvent.click(within(screen.getByTestId("decision-desk")).getByRole("button", { name: /Abrir tese em aten..o/i }));

    const detail = screen.getByTestId("teses-detail-desktop");
    expect(within(detail).getByText(/Apartamento Vila Mariana/i)).toBeInTheDocument();
    expect(within(detail).queryByText(/MGLU3/i)).not.toBeInTheDocument();
  });

  it("explains when active follow-up is limited to real estate", () => {
    render(<Teses data={{ thesisRows: [rows[2], rows[3], rows[4]] }} />);

    fireEvent.click(within(screen.getByTestId("decision-desk")).getByRole("button", { name: /Ver acompanhamento ativo/i }));

    expect(screen.getByText(/B3 e Cripto sem teses ativas/i)).toBeInTheDocument();
    expect(screen.getByText(/a tela mostra apenas os planos imobiliários/i)).toBeInTheDocument();
  });

  it("lets the user jump from the summary to real estate detail without scanning the full table", () => {
    render(<Teses data={{ thesisRows: rows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    expect(screen.getByText("Radar imobiliário")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("teses-row-IM-010"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    const map = within(drawer).getByTestId("real-estate-decision-map");
    expect(within(map).getByText(/Mapa mental da decis/i)).toBeInTheDocument();
    expect(within(map).getByText(/Este im.vel deve avan.ar/i)).toBeInTheDocument();
    expect(within(drawer).queryByTestId("real-estate-decision-summary")).not.toBeInTheDocument();
    expect(within(drawer).getByText("Score do candidato")).toBeInTheDocument();
  });
});
