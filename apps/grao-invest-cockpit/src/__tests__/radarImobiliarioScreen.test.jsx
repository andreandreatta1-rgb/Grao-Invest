import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import RadarImobiliario from "../screens/RadarImobiliario.jsx";

describe("Radar Imobiliário screen", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("opens a dedicated real estate radar area from the sidebar", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: /Radar Imobiliário/i }));

    expect(await screen.findByRole("heading", { name: /RADAR IMOBILIÁRIO/i })).toBeInTheDocument();
    expect(screen.getByText(/Uma área própria para acompanhar bairros/i)).toBeInTheDocument();
    expect(screen.getByText(/A mesa imobiliária agora nasce separada/i)).toBeInTheDocument();
    expect(screen.getByText(/O radar não compra CEP/i)).toBeInTheDocument();

    const portfolio = await screen.findByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getByText(/Oito histórias para mostrar/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Rua Turiassú, 362/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Edifício Saquarema/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByRole("button", { name: /Abrir/i })).toHaveLength(8);
  });

  it("supports direct deep link and expands one property story at a time", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    window.history.replaceState(null, "", "/#radar-imobiliario");
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByRole("heading", { name: /RADAR IMOBILIÁRIO/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Radar Imobiliário/i })).toHaveStyle({
      color: "rgb(200, 164, 68)",
    });

    const portfolio = await screen.findByTestId("radar-imobiliario-portfolio");
    await user.click(within(portfolio).getByRole("button", { name: /Abrir Rua Turiassú, 362/i }));
    expect(within(portfolio).getByText(/Agora sim existe uma pergunta boa/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Resultado simulado vs renda fixa/i)).toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Rua Caiubí, 91/i }));
    expect(within(portfolio).queryByText(/Agora sim existe uma pergunta boa/i)).not.toBeInTheDocument();
    expect(within(portfolio).getByText(/O tamanho impressiona/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/P0 \/ prova antes de convicção/i)).toBeInTheDocument();
  });

  it("puts open candidates first and uses strategy icons for combined real estate plays", async () => {
    const user = userEvent.setup();
    const data = {
      thesisRows: [
        {
          thesisId: "IM-COMBO-01",
          front: "Imóveis",
          status: "Observando",
          statusGroup: "Em análise",
          asset: "Água Funda Parque do Estado 50m2",
          entryPrice: 120000,
          currentPrice: 220000,
          targetPrice: 300000,
          expectedPct: 24.8,
          openedAt: "2026-05-02T15:00:00Z",
          hypothesis: "Compra direta parcelada com dois caminhos: revenda imediata ou House Flipping.",
          operation: "Compra direta parcelada em 18 meses com comparativo entre saída imediata e House Flipping.",
          realEstateAnalysis: {
            score: 72,
            confidence: 46,
            max_purchase_price: 150000,
            next_action: "Orçar reforma por ambiente",
            scenarios: { base: { sale_price: 220000, net_profit: 73000, roi_pct: 24.8 } },
            pending_items: [{ priority: "P1", title: "Orçar reforma completa", action: "Separar estética, elétrica e hidráulica." }],
            candidate: { renovation_budget: 80000, transaction_costs: 12000 },
          },
        },
        {
          thesisId: "IM-COMBO-02",
          front: "Imóveis",
          status: "Observando",
          statusGroup: "Em análise",
          asset: "Caixa Tatuapé apto para reforma",
          entryPrice: 118000,
          targetPrice: 196000,
          expectedPct: 21,
          openedAt: "2026-05-01T12:00:00Z",
          hypothesis: "Leilão Caixa com desconto, reforma e revenda depois da diligência.",
          operation: "Leilão Caixa + House Flipping com reforma leve.",
          realEstateAnalysis: {
            score: 82,
            confidence: 42,
            max_purchase_price: 124000,
            next_action: "Confirmar ocupação, matrícula e débitos",
            scenarios: { base: { sale_price: 196000, net_profit: 22000, roi_pct: 21 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupação", action: "Validar se está ocupado antes da proposta." }],
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getByText(/2 casos reais no radar/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Água Funda Parque do Estado/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Compra direta \+ HF/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getByText(/Caixa Tatuapé apto para reforma/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Leilão \+ HF/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Ícones por tipo de tese/i)).toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Água Funda Parque do Estado/i }));
    expect(within(portfolio).getAllByText(/Preço entrada/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Teto Halley/i).length).toBeGreaterThan(0);
  });

  it("uses canonical real estate cases as the story portfolio when real rows exist", async () => {
    const user = userEvent.setup();
    const data = {
      thesisRows: [
        {
          thesisId: "IM-REAL-OPEN",
          front: "Imóveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Caixa Portal Cantareira apto 43 BL09",
          entryPrice: 60200,
          currentPrice: 233000,
          targetPrice: 233000,
          expectedPct: 81.25,
          openedAt: "2026-05-14T12:00:00Z",
          hypothesis: "Radar imobiliario: Leilao Caixa com desconto, score 83/100 e pendencias P0 abertas.",
          operation: "Leilao Caixa + House Flipping com reforma leve.",
          sourceUrl: "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=8787708775466",
          realEstateAnalysis: {
            score: 83,
            confidence: 51,
            max_purchase_price: 147860,
            suggested_status: "Aberto com pendencias",
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 233000, net_profit: 48912.36, roi_pct: 81.25 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar com a fonte oficial." }],
          },
        },
        {
          thesisId: "IM-REAL-CLOSED",
          front: "Imóveis",
          status: "Fechada",
          statusGroup: "Histórica",
          isOpen: false,
          asset: "REAL - Bras Rangel Pestana studios alugados",
          entryPrice: 250000,
          currentPrice: 250000,
          targetPrice: 210000,
          expectedPct: -18.85,
          openedAt: "2026-05-11T12:00:00Z",
          hypothesis: "Radar imobiliario: renda/plano B ficou acima do teto e perdeu assimetria.",
          operation: "Renda / Plano B | Chaves na Mao | Kitnet / Studio | Acima do teto",
          outcome: "Descartado pelo radar",
          sourceUrl: "https://www.chavesnamao.com.br/imovel/kitnet-a-venda-sp-sao-paulo-bras-130m2-RS250000/id-11606288/",
          realEstateAnalysis: {
            score: 50,
            confidence: 46,
            max_purchase_price: 202000,
            suggested_status: "Descartado",
            next_action: "Descartar ou travar decisao",
            scenarios: { base: { sale_price: 210000, net_profit: -47125, roi_pct: -18.85 } },
            pending_items: [{ priority: "P0", title: "Validar aluguel real", action: "Comparar contra aluguel fechado." }],
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getByText(/2 casos reais no radar/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Caixa Portal Cantareira apto 43 BL09/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Bras Rangel Pestana studios alugados/i)).toBeInTheDocument();
    expect(within(portfolio).queryByText(/Rua Turiassú, 362/i)).not.toBeInTheDocument();

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    const closedPortfolio = screen.getByTestId("radar-imobiliario-fechados");
    expect(within(openPortfolio).getByText(/Caixa Portal Cantareira apto 43 BL09/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByRole("link", { name: /Ver leilão Caixa Portal Cantareira apto 43 BL09/i })).toHaveAttribute(
      "href",
      "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=8787708775466",
    );
    expect(within(openPortfolio).queryByText(/Bras Rangel Pestana studios alugados/i)).not.toBeInTheDocument();
    expect(within(closedPortfolio).getByText(/Bras Rangel Pestana studios alugados/i)).toBeInTheDocument();
    expect(within(closedPortfolio).queryByText(/Caixa Portal Cantareira apto 43 BL09/i)).not.toBeInTheDocument();

    await user.click(within(closedPortfolio).getByRole("button", { name: /Abrir Bras Rangel Pestana/i }));
    expect(within(closedPortfolio).getAllByText(/Caso real encerrado/i).length).toBeGreaterThan(0);
    expect(within(closedPortfolio).getByText(/-18,9%/i)).toBeInTheDocument();
  });

  it("does not truncate late real candidates from the dashboard summary", () => {
    const fillerRows = Array.from({ length: 15 }, (_, index) => ({
      thesisId: `IM-SEED-${String(index + 1).padStart(2, "0")}`,
      front: "Imoveis",
      status: "Aberta - Atencao",
      statusGroup: "Go-live",
      isOpen: true,
      asset: `REAL - Seed base ${index + 1}`,
      entryPrice: 100000 + index,
      currentPrice: 150000 + index,
      targetPrice: 180000 + index,
      expectedPct: 20,
      realEstateAnalysis: {
        score: 61,
        confidence: 40,
        max_purchase_price: 120000 + index,
        suggested_status: "Aberto com pendencias",
        next_action: "Confirmar fonte individual",
        scenarios: { base: { sale_price: 180000 + index, net_profit: 20000, roi_pct: 20 } },
        pending_items: [{ priority: "P0", title: "Confirmar fonte", action: "Validar link individual." }],
      },
    }));
    const data = {
      thesisRows: [
        ...fillerRows,
        {
          thesisId: "IM-FOLHA-FRAZAO-SAUDE-37528",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Folha Frazao Itau Saude Rua Abagiba 74m2",
          sourceUrl: "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528",
          entryPrice: 285000,
          currentPrice: 285000,
          targetPrice: 430000,
          expectedPct: 24,
          realEstateAnalysis: {
            score: 64,
            confidence: 42,
            source_validation: {
              status: "valid",
              reason: "Fonte individual validada.",
            },
            max_purchase_price: 310000,
            suggested_status: "Aberto com pendencias",
            next_action: "Validar edital, ocupacao e debitos",
            scenarios: { base: { sale_price: 430000, net_profit: 62000, roi_pct: 24 } },
            pending_items: [{ priority: "P0", title: "Validar edital", action: "Conferir datas e ocupacao." }],
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(portfolio).getByText(/16 casos reais no radar/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Folha Frazao Itau Saude Rua Abagiba/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Fonte validada/i)).toBeInTheDocument();
    expect(within(openPortfolio).getAllByRole("button", { name: /Abrir/i })).toHaveLength(16);
  });

  it("lets the investor discard an open runtime candidate from the radar", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ status: "Descartado" }) }));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "prompt").mockReturnValue("Sem fonte individual e P0 demais para manter aberto.");
    const data = {
      thesisRows: [
        {
          thesisId: "IM-RADAR-17",
          front: "Imóveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          canDiscard: true,
          asset: "REAL - Parque do Estado Agua Funda reforma pesada 50m2",
          entryPrice: 120000,
          targetPrice: 300000,
          expectedPct: 54,
          realEstateAnalysis: {
            score: 70,
            confidence: 30,
            suggested_status: "Aberto com pendencias",
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 300000, net_profit: 64800, roi_pct: 54 } },
            pending_items: [{ priority: "P0", title: "Confirmar fonte", action: "Validar fonte individual." }],
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} onRefresh={onRefresh} />);

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    await user.click(within(openPortfolio).getByRole("button", { name: /Descartar Parque do Estado Agua Funda/i }));

    expect(fetchMock).toHaveBeenCalledWith("/api/real-estate/candidates/17/discard", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ reason: "Sem fonte individual e P0 demais para manter aberto." }),
    }));
    await waitFor(() => expect(onRefresh).toHaveBeenCalled());
  });

  it("recovers from fallback and replaces demo stories when the real feed comes back", async () => {
    window.history.replaceState(null, "", "/#radar-imobiliario");
    let feedRequests = 0;
    const dashboardSummary = {
      thesis_open_operations: [
        {
          thesis_id: "IM-RECOVERY-01",
          phase: "pos_go_live",
          front: "imoveis",
          action: "REAL - Caixa Portal Cantareira apto 43 BL09",
          status: "Aberta - Atencao",
          outcome: "Pendencias abertas",
          is_open: true,
          expected_result_pct: 81.25,
          entry_price_brl: 60200,
          current_price_brl: 233000,
          target_price_brl: 233000,
          thesis_reason: "Radar imobiliario: caso real voltou depois do fallback.",
          operation_plan: "Leilao Caixa + House Flipping com reforma leve.",
          real_estate_analysis: {
            score: 83,
            confidence: 51,
            max_purchase_price: 147860,
            suggested_status: "Aberto com pendencias",
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 233000, net_profit: 48912.36, roi_pct: 81.25 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar fonte oficial." }],
          },
        },
      ],
    };

    vi.stubGlobal("fetch", vi.fn((url) => {
      const path = String(url);
      if (path.includes("/api/frontend/version")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }

      feedRequests += 1;
      if (feedRequests <= 4) {
        return Promise.reject(new Error("offline"));
      }
      if (path.includes("/api/dashboard/summary/1")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(dashboardSummary) });
      }
      if (path.includes("/api/theses/current-monitor/latest")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ theses: [] }) });
      }
      if (path.includes("/api/real-estate/candidates")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ candidates: [] }) });
      }
      if (path.includes("/api/real-estate/strategy-territory-candidates")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ matrix_briefs: [] }) });
      }
      return Promise.reject(new Error(`unexpected ${path}`));
    }));

    render(<App />);

    const fallbackPortfolio = await screen.findByTestId("radar-imobiliario-portfolio");
    expect(within(fallbackPortfolio).getByText(/Oito histórias para mostrar/i)).toBeInTheDocument();

    await new Promise((resolve) => setTimeout(resolve, 5500));

    await waitFor(() => {
      const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
      expect(within(portfolio).getByText(/1 casos reais no radar/i)).toBeInTheDocument();
      expect(within(portfolio).getByText(/Caixa Portal Cantareira apto 43 BL09/i)).toBeInTheDocument();
      expect(within(portfolio).queryByText(/Rua Turiassú, 362/i)).not.toBeInTheDocument();
    });
  });

  it("refreshes the radar feed from the dedicated screen when new candidates were published", async () => {
    window.history.replaceState(null, "", "/#radar-imobiliario");
    const user = userEvent.setup();
    let dashboardRequests = 0;
    const updatedDashboardSummary = {
      thesis_open_operations: [
        {
          thesis_id: "IM-RADAR-25",
          phase: "pos_go_live",
          front: "imoveis",
          action: "REAL - Alphaville Campinas flat Ibis Styles 32m2",
          status: "Aberta - Atencao",
          outcome: "Pendencias abertas",
          is_open: true,
          expected_result_pct: 96.88,
          entry_price_brl: 152000,
          current_price_brl: 250000,
          target_price_brl: 250000,
          thesis_reason: "Radar imobiliario: caso publicado depois da tela ja estar aberta.",
          operation_plan: "Renda / Plano B | Chaves na Mao | Flat | Dentro do teto",
          source_url: "https://www.chavesnamao.com.br/flat/sp-campinas/alphaville/",
          real_estate_analysis: {
            score: 82,
            confidence: 33,
            max_purchase_price: 190000,
            suggested_status: "Aberto com pendencias",
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 250000, net_profit: 62000, roi_pct: 96.88 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar fonte oficial." }],
          },
        },
      ],
    };

    vi.stubGlobal("fetch", vi.fn((url) => {
      const path = String(url);
      if (path.includes("/api/frontend/version")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }
      if (path.includes("/api/dashboard/summary/1")) {
        dashboardRequests += 1;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(dashboardRequests === 1 ? { thesis_open_operations: [] } : updatedDashboardSummary),
        });
      }
      if (path.includes("/api/theses/current-monitor/latest")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ theses: [] }) });
      }
      if (path.includes("/api/real-estate/candidates")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ candidates: [] }) });
      }
      if (path.includes("/api/real-estate/strategy-territory-candidates")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ matrix_briefs: [] }) });
      }
      return Promise.reject(new Error(`unexpected ${path}`));
    }));

    render(<App />);

    const portfolio = await screen.findByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).queryByText(/Alphaville Campinas flat/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Atualizar radar/i }));

    await waitFor(() => {
      const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
      expect(within(openPortfolio).getByText(/Alphaville Campinas flat Ibis Styles 32m2/i)).toBeInTheDocument();
    });
    expect(dashboardRequests).toBeGreaterThan(1);
  });

  it("labels direct-sale source links as announcements, not auctions", () => {
    const data = {
      thesisRows: [
        {
          thesisId: "IM-DIRECT-01",
          front: "Imóveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Jardim das Colinas SJC 65m2 regiao Shopping",
          entryPrice: 460000,
          currentPrice: 598650,
          targetPrice: 598650,
          expectedPct: 33.47,
          operation: "Arbitragem sem reforma + venda direta",
          sourceUrl: "https://www.imovelweb.com.br/propriedades/apartamento-para-venda-regiao-do-jardim-colinas.html",
          realEstateAnalysis: {
            score: 72,
            confidence: 30,
            source_validation: {
              status: "valid",
              reason: "Fonte individual validada.",
            },
            max_purchase_price: 423377.9,
            suggested_status: "Aberto com pendencias",
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 598650, net_profit: 48831, roi_pct: 33.47 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar fonte oficial." }],
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} />);

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(openPortfolio).getByRole("link", { name: /Ver anúncio Jardim das Colinas/i })).toHaveAttribute(
      "href",
      "https://www.imovelweb.com.br/propriedades/apartamento-para-venda-regiao-do-jardim-colinas.html",
    );
    expect(within(openPortfolio).queryByRole("link", { name: /Ver leilão Jardim das Colinas/i })).not.toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Compra para revenda · score 72\/100/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Fonte validada/i)).toBeInTheDocument();
    expect(within(openPortfolio).queryByText(/Leilão \+ HF · score 72\/100/i)).not.toBeInTheDocument();
  });

  it("shows discarded direct-source candidates only in the closed portfolio", () => {
    const data = {
      thesisRows: [
        {
          thesisId: "IM-RADAR-20",
          front: "Imóveis",
          status: "Fechada",
          statusGroup: "Histórica",
          isOpen: false,
          asset: "REAL - Jardim das Colinas SJC 65m2 regiao Shopping",
          entryPrice: 460000,
          currentPrice: 598650,
          targetPrice: 598650,
          expectedPct: 33.47,
          operation: "Preco pedido R$ 460,000.00 | Caixa necessario R$ 145,900.00",
          structure: "Arbitragem sem reforma + venda direta | Imovelweb | Apartamento",
          sourceUrl: "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
          outcome: "Descartado pelo radar",
          exitRule: "Anuncio Imovelweb finalizado pelo anunciante.",
          realEstateAnalysis: {
            score: 72,
            confidence: 30,
            suggested_status: "Descartado",
            next_action: "Anuncio finalizado",
            scenarios: { base: { sale_price: 598650, net_profit: 48831, roi_pct: 33.47 } },
            candidate: {
              origin: "Imovelweb",
              strategy: "Arbitragem sem reforma + venda direta",
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} />);

    const openPortfolio = screen.queryByTestId("radar-imobiliario-abertos");
    const closedPortfolio = screen.getByTestId("radar-imobiliario-fechados");
    expect(openPortfolio).not.toBeInTheDocument();
    expect(within(closedPortfolio).getByText(/Jardim das Colinas/i)).toBeInTheDocument();
    expect(within(closedPortfolio).getByRole("link", { name: /Ver anúncio Jardim das Colinas/i })).toHaveAttribute(
      "href",
      "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
    );
    expect(within(closedPortfolio).queryByText(/Leilão \+ HF/i)).not.toBeInTheDocument();
  });
});
