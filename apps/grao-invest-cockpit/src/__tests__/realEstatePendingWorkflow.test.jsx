import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Teses from "../screens/Teses.jsx";

const realEstateRow = {
  id: 2014,
  thesisId: "IM-RADAR-4",
  asset: "Caixa Av Nordestina apto 08",
  front: "Im\u00f3veis",
  direction: "Potencial positivo",
  expectedPct: 64.04,
  structure: "LeilÃ£o/venda online",
  entryPrice: 118465.05,
  currentPrice: 196000,
  exitRule: "Confirmar ocupacao",
  outcome: "PendÃªncias abertas",
  days: 0,
  status: "Aberta - Atencao",
  statusGroup: "Go-live",
  resultPct: 0,
  resultKind: "estimate",
  isOpen: true,
  hypothesis: "Radar imobiliario com ocupacao pendente.",
  learning: "Antes de proposta, confirmar pendencias P0.",
  realEstateAnalysis: {
    score: 80,
    confidence: 36,
    suggested_status: "Aberto com pendencias",
    next_action: "Confirmar ocupacao",
    price_ceiling_status: "Dentro do teto",
    max_purchase_price: 124000,
    price_gap_to_ceiling: -5217.35,
    pending_items: [
      { key: "registration", priority: "P0", title: "Buscar matricula atualizada", action: "Conferir onus." },
      { key: "sale_comparables", priority: "P1", title: "Buscar 3 comparaveis de venda", action: "Usar comparaveis proximos." },
    ],
    clarified_items: [],
    score_breakdown: [],
    confidence_breakdown: [],
  },
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("real estate pending workflow", () => {
  it("lets the user register evidence and close a pending item through the official API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
    const onRefresh = vi.fn();

    render(<Teses data={{ thesisRows: [realEstateRow] }} onRefresh={onRefresh} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir tese em atenção Caixa Av Nordestina apto 08/i }));
    expect(screen.getByTestId("pending-grid-P0")).toHaveStyle({
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    });
    expect(screen.getByTestId("pending-grid-P1")).toHaveStyle({
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    });
    fireEvent.change(screen.getByLabelText("Evidencia para Buscar matricula atualizada"), {
      target: { value: "Matricula atualizada baixada no cartorio em 04/05." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Registrar e fechar Buscar matricula atualizada" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/real-estate/candidates/4",
      expect.objectContaining({
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
      }),
    ));

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toMatchObject({
      has_registration: true,
    });
    expect(body.notes).toContain("Matricula atualizada baixada");
    await waitFor(() => expect(onRefresh).toHaveBeenCalled());
    expect(await screen.findByText("Registrado. O radar vai recalcular esta tese.")).toBeInTheDocument();
  });

  it("keeps the real estate decision table inside optional support without desktop horizontal scroll", () => {
    render(<Teses data={{ thesisRows: [realEstateRow] }} />);

    fireEvent.click(screen.getAllByText(/Im.veis/)[0].closest("button"));

    const cockpit = screen.getByTestId("real-estate-deal-cockpit");
    expect(cockpit).toBeInTheDocument();
    expect(cockpit).toHaveTextContent("80/100 score");
    expect(cockpit).toHaveTextContent("36/100 confiança");
    expect(cockpit).toHaveTextContent("1 P0");

    fireEvent.click(screen.getByText("Ver lista completa"));

    expect(screen.getAllByText(/Decis.o/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Dire..o/)).not.toBeInTheDocument();
    expect(screen.getByTestId("teses-table-wrapper")).toHaveStyle({ overflowX: "hidden" });
    expect(screen.getByTestId("teses-table")).toHaveStyle({ minWidth: "0px" });
    expect(screen.getByText("Todos os candidatos imobiliários")).toBeInTheDocument();
    expect(screen.queryByText(/ROI estimado no cen.rio base/i)).not.toBeInTheDocument();
  });

  it("shows clarified items, score composition, and confidence composition as decision cards", () => {
    const rowWithDossierCards = {
      ...realEstateRow,
      realEstateAnalysis: {
        ...realEstateRow.realEstateAnalysis,
        clarified_items: [
          { title: "Matricula baixada", detail: "Documento atualizado no cartorio." },
          { title: "Valor de mercado validado", detail: "Tres comparaveis conferidos." },
        ],
        score_breakdown: [
          { label: "Liquidez", points: 12, max_points: 20, detail: "Boa demanda na regiao." },
        ],
        confidence_breakdown: [
          { label: "Ocupacao", points: 0, max_points: 15, status: "pendente", detail: "Falta confirmar ocupacao." },
        ],
      },
    };

    render(<Teses data={{ thesisRows: [rowWithDossierCards] }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir tese em atenção Caixa Av Nordestina apto 08/i }));

    expect(screen.getByTestId("clarified-grid")).toHaveStyle({
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    });
    expect(screen.getByTestId("clarified-card-0")).toHaveTextContent("Matricula baixada");
    expect(screen.getByTestId("clarified-card-0")).toHaveTextContent("Evidencia confirmada");

    expect(screen.getByTestId("score-breakdown-grid")).toHaveStyle({
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    });
    expect(screen.getByTestId("score-breakdown-card-0")).toHaveTextContent("12/20");
    expect(screen.getByTestId("score-breakdown-fill-0")).toHaveStyle({ width: "60%" });

    expect(screen.getByTestId("confidence-breakdown-grid")).toHaveStyle({
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    });
    expect(screen.getByTestId("confidence-breakdown-card-0")).toHaveTextContent("pendente");
    expect(screen.getByTestId("confidence-breakdown-fill-0")).toHaveStyle({ width: "0%" });
  });
});

