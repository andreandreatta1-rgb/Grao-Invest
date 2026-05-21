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

    expect(screen.getByTestId("radar-imobiliario-visao-geral")).toBeInTheDocument();
    expect(screen.queryByTestId("radar-imobiliario-garimpo")).not.toBeInTheDocument();
    expect(screen.queryByTestId("radar-imobiliario-portfolio")).not.toBeInTheDocument();
  });

  it("supports direct deep link and expands one property story at a time", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    window.history.replaceState(null, "", "/#radar-imobiliario/candidatos");
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByTestId("radar-imobiliario-portfolio")).toBeInTheDocument();
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

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getByText(/2 casos reais no radar/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Água Funda Parque do Estado/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Compra direta \+ HF/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Caixa Tatuapé apto para reforma/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Leilão \+ HF/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Ícones por tipo de tese/i)).toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Água Funda Parque do Estado/i }));
    expect(within(portfolio).getAllByText(/Preço entrada/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Teto Halley/i).length).toBeGreaterThan(0);
  });

  it("shows structured auctioneer sourcing as a separate radar area", () => {
    const data = {
      realEstateStrategyTerritoryCandidates: {
        auctioneerSourcing: {
          summary: {
            officialDirectoryCount: 1,
            officialContactCount: 2,
            longTailDirectoryCount: 1,
            contactSourceCount: 1,
            outreachSentCount: 2,
            outreachResponseCount: 1,
            outreachNoRealEstateCount: 1,
            outreachPendingResponseCount: 1,
            nextFollowUpAt: "2026-05-22",
            scopeCities: ["Sao Paulo", "Campinas"],
            actionability: "Garimpo de cauda longa com base oficial JUCESP para sao paulo capital e campinas.",
          },
          officialDirectories: [
            {
              id: "auctioneer-jucesp-sp-campinas",
              uf: "SP",
              sourceName: "JUCESP - Consulta de Leiloeiros e Tradutores",
              sourceUrl: "https://www.institucional.jucesp.sp.gov.br/consultaLeilao.html",
              contactPath: "Consulta oficial por municipio, situacao, telefone, e-mail e site.",
              contactStrategy: "Filtrar Atuante Regular em Sao Paulo capital e Campinas.",
              visibilityTier: "cauda_longa",
              qualityFilter: ["situacao regular", "matricula informada"],
            },
          ],
          officialContacts: [
            {
              id: "auctioneer-sp-547",
              name: "CARLOS CHUI",
              registration: "547",
              city: "Sao Paulo",
              neighborhood: "Ipiranga",
              phones: ["(11)2272-7170", "(11)97014-2280"],
              email: "contato@arremataronline.com.br",
              status: "Atuante Regular",
              competitionTier: "estabelecido",
              competitionReason: "Dominio de leilao e multiplos telefones sugerem maior exposicao.",
              contactStrategy: "Entrar no mailing e monitorar lotes imobiliarios.",
              outreachStatus: "respondido_sem_imoveis",
              outreachChannel: "Gmail",
              outreachSentAt: "2026-05-19",
              responseReceivedAt: "2026-05-19",
              responseSummary: "Carlos respondeu que nao trabalha com imoveis.",
            },
            {
              id: "auctioneer-campinas-716",
              name: "ANA CLARA DE MELLO E SILVA",
              registration: "716",
              city: "Campinas",
              neighborhood: "Centro",
              phones: ["(19)3849-7675", "(19)99695-3050"],
              email: "anaclarademello@bol.com.br",
              status: "Atuante Regular",
              competitionTier: "cauda_longa",
              competitionReason: "E-mail gratuito e recorte regional indicam menor disputa inicial.",
              contactStrategy: "Contato direto para pauta de imoveis em Campinas.",
              outreachStatus: "enviado",
              outreachChannel: "Gmail",
              outreachSentAt: "2026-05-19",
              nextFollowUpAt: "2026-05-22",
            },
          ],
          outreachPlaybook: [
            {
              stage: "coleta_oficial",
              action: "Extrair nome, matricula, situacao, site, e-mail e telefone publicados pela Junta Comercial.",
            },
            {
              stage: "primeiro_contato",
              action: "Pedir mailing institucional de lotes imobiliarios no ticket alvo.",
            },
          ],
          scoringModel: {
            lowCompetitionSignals: ["site simples ou pouco indexado"],
            qualitySignals: ["matricula regular", "edital claro"],
          },
        },
      },
    };

    render(<RadarImobiliario data={data} section="garimpo" />);

    const panel = screen.getByTestId("radar-imobiliario-garimpo");
    expect(within(panel).getByText(/Garimpo estruturado/i)).toBeInTheDocument();
    expect(within(panel).getByText(/Base propria de leiloeiros oficiais/i)).toBeInTheDocument();
    expect(within(panel).getAllByText(/JUCESP/i).length).toBeGreaterThan(0);
    expect(within(panel).getByText(/Leiloeiros SP\/Campinas/i)).toBeInTheDocument();
    expect(within(panel).getByText(/CARLOS CHUI/i)).toBeInTheDocument();
    expect(within(panel).getByText(/ANA CLARA DE MELLO E SILVA/i)).toBeInTheDocument();
    expect(within(panel).getAllByText(/Estabelecido/i).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/Cauda longa/i).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/E-mail enviado/i).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/Sem imóveis/i).length).toBeGreaterThan(0);
    expect(within(panel).getByText(/Carlos respondeu que nao trabalha com imoveis/i)).toBeInTheDocument();
    expect(within(panel).getAllByText(/resposta 19\/05\/26/i).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/follow-up 22\/05\/26/i).length).toBeGreaterThan(0);
    expect(within(panel).getByText(/Roteiro de contato/i)).toBeInTheDocument();
    expect(within(panel).getByText(/site simples ou pouco indexado/i)).toBeInTheDocument();
  });

  it("keeps the auctioneer radar visible when sourcing data has not loaded", () => {
    render(<RadarImobiliario data={{ realEstateStrategyTerritoryCandidates: {} }} section="garimpo" />);

    const panel = screen.getByTestId("radar-imobiliario-garimpo");
    expect(within(panel).getByText(/Radar de leiloeiros/i)).toBeInTheDocument();
    expect(within(panel).getByText(/Aguardando diretorios oficiais/i)).toBeInTheDocument();
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

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getByText(/2 casos reais no radar/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Caixa Portal Cantareira apto 43 BL09/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Bras Rangel Pestana studios alugados/i).length).toBeGreaterThan(0);
    expect(within(portfolio).queryByText(/Rua Turiassú, 362/i)).not.toBeInTheDocument();

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    const closedPortfolio = screen.getByTestId("radar-imobiliario-fechados");
    expect(within(openPortfolio).getAllByText(/Caixa Portal Cantareira apto 43 BL09/i).length).toBeGreaterThan(0);
    expect(within(openPortfolio).getByTestId("candidate-identifier-number")).toHaveTextContent("01");
    expect(within(openPortfolio).getByRole("link", { name: /Ver leilão Caixa Portal Cantareira apto 43 BL09/i })).toHaveAttribute(
      "href",
      "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=8787708775466",
    );
    expect(within(openPortfolio).queryByText(/Bras Rangel Pestana studios alugados/i)).not.toBeInTheDocument();
    expect(within(closedPortfolio).getAllByText(/Bras Rangel Pestana studios alugados/i).length).toBeGreaterThan(0);
    expect(within(closedPortfolio).getByTestId("candidate-identifier-number")).toHaveTextContent("02");
    expect(within(closedPortfolio).queryByText(/Caixa Portal Cantareira apto 43 BL09/i)).not.toBeInTheDocument();

    await user.click(within(closedPortfolio).getByRole("button", { name: /Abrir Bras Rangel Pestana/i }));
    expect(within(closedPortfolio).getAllByText(/Caso real encerrado/i).length).toBeGreaterThan(0);
    expect(within(closedPortfolio).getByText(/-31,2%/i)).toBeInTheDocument();
  });

  it("moves local-demand failures to closed learning with an explicit buyer-demand warning", async () => {
    const user = userEvent.setup();
    const data = {
      thesisRows: [
        {
          thesisId: "IM-SAUDE-OPEN",
          front: "Imóveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Saude Rua Abagiba 74m2",
          entryPrice: 388700,
          currentPrice: 600000,
          expectedPct: 64,
          realEstateAnalysis: {
            score: 71,
            confidence: 44,
            suggested_status: "Aberto com pendencias",
            next_action: "Buscar matricula",
            max_purchase_price: 420000,
            scenarios: { base: { sale_price: 600000, net_profit: 106378, roi_pct: 64 } },
            pending_items: [{ priority: "P0", title: "Buscar matricula", action: "Conferir onus." }],
            candidate: { city: "Sao Paulo", neighborhood: "Saude", private_area_m2: 74.14, asking_price: 388700 },
          },
        },
        {
          thesisId: "IM-FOLHA-FRAZAO-BUTANTA-37467",
          front: "Imóveis",
          status: "Fechada",
          statusGroup: "Histórica",
          isOpen: false,
          outcome: "Descartado pelo radar",
          asset: "REAL - Frazao Itau Butanta Piazza Morumbi 232m2",
          entryPrice: 749600,
          currentPrice: 1040000,
          exitRule: "Descartado por demanda local reprovada.",
          realEstateAnalysis: {
            score: 47,
            confidence: 30,
            suggested_status: "Descartado",
            next_action: "Fechar candidato: demanda local reprovada",
            max_purchase_price: 617228,
            scenarios: { base: { sale_price: 1040000, net_profit: 29424, roi_pct: 7.62 } },
            pending_items: [
              {
                priority: "P0",
                title: "Validar demanda local e comprador",
                action: "Fechar o candidato e registrar aprendizado.",
              },
            ],
            local_demand_evidence: {
              risk_level: "critico",
              status_label: "Demanda local reprovada",
              buyer_profile: "Comprador de alto ticket para apartamento grande.",
              signals: ["Morumbi/Vila Andrade exige prova micro de comprador, nao apenas m2 barato."],
              caveat: "Preco por m2 barato nao compensa se o comprador final evita a micro-regiao.",
              required_action: "So reabrir com 3 vendas equivalentes e liquidez da rua confirmada.",
              should_discard: true,
            },
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Butanta / Morumbi",
              property_type: "Apartamento",
              private_area_m2: 232.23,
              asking_price: 749600,
              estimated_sale_base: 1040000,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    expect(screen.getByText(/2 casos reais no radar \(1 aberto \/ 1 encerrado\)/i)).toBeInTheDocument();
    const closed = screen.getByTestId("radar-imobiliario-fechados");
    expect(within(closed).getByText(/Demanda local critica/i)).toBeInTheDocument();

    await user.click(within(closed).getByRole("button", { name: /Abrir Frazao Itau Butanta Piazza Morumbi/i }));

    expect(within(closed).getByText(/Demanda local \/ publico comprador/i)).toBeInTheDocument();
    expect(within(closed).getByText(/bloqueada por demanda local/i)).toBeInTheDocument();
    expect(within(closed).getByText(/Comprador de alto ticket/i)).toBeInTheDocument();
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
          thesisId: "IM-FOLHA-FRAZAO-PARADA-INGLESA-37570",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Frazão Itaú Parada Inglesa casa vila 105m2",
          sourceUrl: "https://www.frazaoleiloes.com.br/Auction/LotDetails/37570",
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
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Parada Inglesa / Tucuruvi",
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

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(portfolio).getByText(/16 casos reais no radar/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Frazão Itaú Parada Inglesa/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Sao Paulo \/ Parada Inglesa \/ Tucuruvi \/ Rua a validar \/ Entrada R\$ 285\.000 \/ Saida R\$ 430\.000/i)).toBeInTheDocument();
    expect(within(openPortfolio).getAllByTestId("candidate-identifier-number").some((node) => node.textContent === "16")).toBe(true);
    expect(within(openPortfolio).getByText(/Fonte validada/i)).toBeInTheDocument();
    expect(within(openPortfolio).getAllByRole("button", { name: /Abrir/i })).toHaveLength(16);
  });

  it("names radar candidates by city, neighborhood, street, entry and exit", () => {
    const data = {
      thesisRows: [
        {
          thesisId: "IM-FOLHA-FRAZAO-SAUDE-37528",
          thesisNumber: 3885,
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Frazão Itaú Saúde Rua Abagiba 74m2",
          entryPrice: 388700,
          currentPrice: 600000,
          targetPrice: 600000,
          expectedPct: 64.05,
          realEstateAnalysis: {
            score: 71,
            confidence: 44,
            suggested_status: "Aberto com pendencias",
            next_action: "Ler edital, matricula e risco de ocupacao",
            scenarios: { base: { sale_price: 600000, net_profit: 120000, roi_pct: 64.05 } },
            pending_items: [{ priority: "P0", title: "Avaliar risco de imovel ocupado", action: "Validar ocupacao." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Saude",
              asking_price: 388700,
              market_value_estimate: 600000,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(openPortfolio).getByText(/Sao Paulo \/ Saude \/ Rua Abagiba \/ Entrada R\$ 388\.700 \/ Saida R\$ 600\.000/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/Origem: Frazão Itaú Saúde Rua Abagiba 74m2/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByTestId("candidate-identifier-number")).toHaveTextContent("01");
  });

  it("shows commercial payment scenarios for a real estate candidate", async () => {
    const user = userEvent.setup();
    const data = {
      thesisRows: [
        {
          thesisId: "IM-FOLHA-FRAZAO-PARADA-INGLESA-37570",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Frazão Itaú Parada Inglesa casa vila 105m2",
          sourceUrl: "https://www.frazaoleiloes.com.br/Auction/LotDetails/37570",
          entryPrice: 399400,
          currentPrice: 585000,
          targetPrice: 585000,
          expectedPct: 35.31,
          realEstateAnalysis: {
            score: 76,
            confidence: 45,
            max_purchase_price: 390133.2,
            suggested_status: "Aberto com pendencias",
            next_action: "Ler edital, matricula e risco de ocupacao",
            scenarios: { base: { sale_price: 585000, net_profit: 65336, roi_pct: 35.31 } },
            pending_items: [{ priority: "P0", title: "Avaliar risco de imovel ocupado", action: "Validar ocupacao." }],
            commercial_terms: {
              recommended_scenario_key: "cash_discount",
              recommended_decision: "melhora_margem",
              summary: "A vista com desconto melhora a margem; parcelamento longo com IPCA vira risco financeiro.",
              scenarios: [
                {
                  key: "cash_discount",
                  label: "A vista com 10% de desconto",
                  initial_cash: 359460,
                  effective_purchase_price: 359460,
                  total_nominal_cost: 359460,
                  risk_level: "baixo",
                  decision: "melhora_margem",
                  reading: "Desconto a vista reduz preco de entrada e melhora margem.",
                },
                {
                  key: "down_20_8x_no_interest",
                  label: "20% de sinal + 8 parcelas sem juros",
                  initial_cash: 79880,
                  monthly_payment: 39940,
                  effective_purchase_price: 399400,
                  total_nominal_cost: 399400,
                  risk_level: "medio",
                  decision: "preserva_caixa_mas_reduz_margem",
                  reading: "Melhora caixa inicial, mas perde o desconto a vista.",
                },
                {
                  key: "down_30_78x_price_ipca",
                  label: "30% de sinal + 78 parcelas Price + IPCA",
                  initial_cash: 119820,
                  monthly_payment: 4827.7,
                  effective_purchase_price: 496380.83,
                  total_nominal_cost: 496380.83,
                  risk_level: "alto",
                  decision: "alto_custo_financeiro",
                  reading: "Parcelamento longo indexado exige cenario de IPCA antes de defender a tese.",
                },
              ],
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    await user.click(within(portfolio).getByRole("button", { name: /Abrir Frazão Itaú Parada Inglesa/i }));

    expect(within(portfolio).getByText(/Condições comerciais/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/A vista com 10% de desconto/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/R\$ 359\.460/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getByText(/20% de sinal \+ 8 parcelas sem juros/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/IPCA vira risco financeiro/i)).toBeInTheDocument();
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

    render(<RadarImobiliario data={data} onRefresh={onRefresh} section="candidatos" />);

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    await user.click(within(openPortfolio).getByRole("button", { name: /Descartar Parque do Estado Agua Funda/i }));

    expect(fetchMock).toHaveBeenCalledWith("/api/real-estate/candidates/17/discard", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ reason: "Sem fonte individual e P0 demais para manter aberto." }),
    }));
    await waitFor(() => expect(onRefresh).toHaveBeenCalled());
  });

  it("recovers from fallback and replaces demo stories when the real feed comes back", async () => {
    window.history.replaceState(null, "", "/#radar-imobiliario/candidatos");
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
    window.history.replaceState(null, "", "/#radar-imobiliario/candidatos");
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

    render(<RadarImobiliario data={data} section="candidatos" />);

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

    render(<RadarImobiliario data={data} section="candidatos" />);

    const openPortfolio = screen.queryByTestId("radar-imobiliario-abertos");
    const closedPortfolio = screen.getByTestId("radar-imobiliario-fechados");
    expect(openPortfolio).not.toBeInTheDocument();
    expect(within(closedPortfolio).getAllByText(/Jardim das Colinas/i).length).toBeGreaterThan(0);
    expect(within(closedPortfolio).getByRole("link", { name: /Ver anúncio Jardim das Colinas/i })).toHaveAttribute(
      "href",
      "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
    );
    expect(within(closedPortfolio).queryByText(/Leilão \+ HF/i)).not.toBeInTheDocument();
  });

  it("surfaces target neighborhood candidates in the dedicated real estate radar", async () => {
    const user = userEvent.setup();
    const data = {
      thesisRows: [
        {
          thesisId: "IM-RADAR-TARGET-PIN-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL TARGET - Pinheiros Mourato Coelho 84m 2q",
          operation: "House flipping leve | Imovelweb | Apartamento | Acima do teto",
          entryPrice: 800000,
          currentPrice: 920000,
          expectedPct: -19.71,
          realEstateAnalysis: {
            score: 53,
            confidence: 38,
            max_purchase_price: 632400,
            next_action: "Validar fonte manualmente",
            scenarios: { base: { sale_price: 920000, net_profit: -55200, roi_pct: -19.71 } },
            pending_items: [{ priority: "P0", title: "Validar fonte manualmente", action: "Confirmar disponibilidade." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Mourato Coelho",
              strategy: "House flipping leve",
              origin: "Imovelweb",
              private_area_m2: 84,
              source_validation_status: "ambiguous",
            },
          },
        },
        {
          thesisId: "IM-RADAR-TARGET-CAM-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL TARGET - Campo Belo Joao de Sousa Dias 70m",
          operation: "Arbitragem sem reforma | Imovelweb | Apartamento | Acima do teto",
          entryPrice: 640000,
          currentPrice: 760000,
          expectedPct: -8.2,
          realEstateAnalysis: {
            score: 58,
            confidence: 35,
            max_purchase_price: 560000,
            next_action: "Validar anuncio individual",
            scenarios: { base: { sale_price: 760000, net_profit: -21000, roi_pct: -8.2 } },
            pending_items: [{ priority: "P0", title: "Validar anuncio individual", action: "Confirmar preco e fonte." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Campo Belo",
              street: "Rua Joao de Sousa Dias",
              strategy: "Arbitragem sem reforma",
              origin: "Imovelweb",
              private_area_m2: 70,
              source_validation_status: "ambiguous",
            },
          },
        },
        {
          thesisId: "IM-RADAR-OLD-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Alphaville Campinas flat Ibis Styles 32m2",
          operation: "Renda / Plano B | Chaves na Mao | Flat | Dentro do teto",
          entryPrice: 152000,
          currentPrice: 250000,
          expectedPct: 96.88,
          realEstateAnalysis: {
            score: 82,
            confidence: 33,
            max_purchase_price: 190000,
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 250000, net_profit: 62000, roi_pct: 96.88 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar fonte oficial." }],
            candidate: { neighborhood: "Alphaville Campinas", strategy: "Renda / Plano B" },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} />);

    const panel = screen.getByTestId("radar-imobiliario-bairros-alvo");
    expect(within(panel).getByText(/Bairros-alvo para amanha/i)).toBeInTheDocument();
    expect(within(panel).getByText(/2 candidatos-alvo/i)).toBeInTheDocument();
    expect(within(panel).getAllByText(/Pinheiros/i).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/Campo Belo/i).length).toBeGreaterThan(0);
    expect(within(panel).getByText(/Sao Paulo \/ Pinheiros \/ Rua Mourato Coelho/i)).toBeInTheDocument();
    expect(within(panel).getByText(/Sao Paulo \/ Campo Belo \/ Rua Joao de Sousa Dias/i)).toBeInTheDocument();
    expect(within(panel).queryByText(/Alphaville Campinas/i)).not.toBeInTheDocument();

    await user.click(within(panel).getByRole("button", { name: /Campo Belo/i }));

    expect(within(panel).getByText(/Sao Paulo \/ Campo Belo \/ Rua Joao de Sousa Dias/i)).toBeInTheDocument();
    expect(within(panel).queryByText(/Sao Paulo \/ Pinheiros \/ Rua Mourato Coelho/i)).not.toBeInTheDocument();
    expect(within(panel).getByText(/1 candidato neste bairro/i)).toBeInTheDocument();
  });

  it("promotes target neighborhood candidates to the top of active real estate candidates", () => {
    const data = {
      thesisRows: [
        {
          thesisId: "IM-RADAR-OLD-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Alphaville Campinas flat Ibis Styles 32m2",
          operation: "Renda / Plano B | Chaves na Mao | Flat | Dentro do teto",
          entryPrice: 152000,
          currentPrice: 250000,
          realEstateAnalysis: {
            score: 82,
            confidence: 33,
            max_purchase_price: 190000,
            next_action: "Confirmar ocupacao",
            scenarios: { base: { sale_price: 250000, net_profit: 62000, roi_pct: 96.88 } },
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar fonte oficial." }],
            candidate: { city: "Campinas", neighborhood: "Alphaville Campinas", strategy: "Renda / Plano B" },
          },
        },
        {
          thesisId: "IM-RADAR-TARGET-PIN-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL TARGET - Pinheiros Capote Valente 33m 1q",
          operation: "Leilao extrajudicial + HF leve | Leilao Imovel | Apartamento | Teto a validar",
          entryPrice: 339845.69,
          currentPrice: 566409.48,
          realEstateAnalysis: {
            score: 70,
            confidence: 28,
            max_purchase_price: 350000,
            next_action: "Validar fonte manualmente",
            scenarios: { base: { sale_price: 566409.48, net_profit: 80000, roi_pct: 23.5 } },
            pending_items: [{ priority: "P0", title: "Validar fonte manualmente", action: "Confirmar edital." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Capote Valente",
              strategy: "Leilao extrajudicial + HF leve",
              origin: "Leilao Imovel",
              private_area_m2: 33.5,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    const buttons = within(openPortfolio).getAllByRole("button", { name: /Abrir/i });
    expect(buttons[0]).toHaveAccessibleName(/Abrir REAL TARGET - Pinheiros Capote Valente/i);
    expect(within(openPortfolio).getAllByTestId("candidate-identifier-number")[0]).toHaveTextContent("01");
  });

  it("renders radar subareas as isolated content views", () => {
    render(<RadarImobiliario data={{ realEstateStrategyTerritoryCandidates: {} }} section="garimpo" />);

    expect(screen.getByTestId("radar-imobiliario-garimpo")).toBeInTheDocument();
    expect(screen.getByText(/Aguardando diretorios oficiais/i)).toBeInTheDocument();
    expect(screen.queryByTestId("radar-imobiliario-visao-geral")).not.toBeInTheDocument();
    expect(screen.queryByTestId("radar-imobiliario-bairros-alvo")).not.toBeInTheDocument();
    expect(screen.queryByTestId("radar-imobiliario-portfolio")).not.toBeInTheDocument();
  });
});
