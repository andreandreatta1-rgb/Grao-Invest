import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import { normalizeCockpitHalley } from "../data/cockpitHalleyAdapter.js";
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

  it("surfaces source access blockers with the credential file requested by the app", () => {
    const data = {
      thesisRows: [
        {
          thesisId: "IM-RADAR-ACCESS-1234",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL TARGET - Pinheiros Alves Guimaraes",
          sourceUrl: "https://www.webleiloes.com.br/lote/12345",
          entryPrice: 420000,
          currentPrice: 650000,
          targetPrice: 650000,
          expectedPct: 22,
          realEstateAnalysis: {
            score: 66,
            confidence: 40,
            max_purchase_price: 430000,
            next_action: "Acesso ao leiloeiro necessario",
            source_validation: {
              status: "access_required",
              reason: "Fonte exige cadastro/login para continuar.",
              user_action: "Criar cadastro/login no leiloeiro e anexar credenciais.",
              credential_file_hint: "data/secure/real_estate_sources/www.webleiloes.com.br.credentials.json",
            },
            scenarios: { base: { sale_price: 650000, net_profit: 90000, roi_pct: 22 } },
            pending_items: [
              {
                key: "source_access",
                priority: "P0",
                title: "Acesso ao leiloeiro necessario",
                action: "Criar cadastro/login no leiloeiro e anexar credenciais.",
              },
            ],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Alves Guimaraes",
              strategy: "Leilao extrajudicial + HF leve",
              origin: "Leilao Imovel / WebLeiloes",
              private_area_m2: 45,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const openPortfolio = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(openPortfolio).getByText(/Acesso necessario/i)).toBeInTheDocument();
    expect(within(openPortfolio).getByText(/www\.webleiloes\.com\.br\.credentials\.json/i)).toBeInTheDocument();
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
    expect(within(openPortfolio).getAllByTestId("candidate-identifier-number").some((node) => node.textContent === "37570")).toBe(true);
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
    expect(within(openPortfolio).getByTestId("candidate-identifier-number")).toHaveTextContent("3885");
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
          id: "3968",
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
          id: "3968",
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
    expect(within(openPortfolio).getAllByTestId("candidate-identifier-number")[0]).toHaveTextContent("3968");
  });

  it("blocks target candidates with occupied unit, ceiling breach, and weak sale proof", () => {
    const data = {
      thesisRows: [
        {
          id: "3970",
          thesisId: "IM-RADAR-TARGET-PIN-03",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL TARGET - Pinheiros Alves Guimaraes cobertura 147m",
          operation: "Leilao extrajudicial + HF leve | Leilao Imovel | Cobertura | Acima do teto",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-apto-cobertura-duplex-147m-02-vagas-pinheiros-sao-paulo-sp-imovel-banco-santander-2810257",
          entryPrice: 821000,
          currentPrice: 1098416.67,
          targetPrice: 1098416.67,
          realEstateAnalysis: {
            score: 58,
            confidence: 43,
            max_purchase_price: 776000,
            source_validation: {
              status: "ambiguous",
              reason: "Checar ocupacao, debitos condominiais e liquidez de cobertura antes de lance.",
            },
            valuation_evidence: { sale_comparables_count: 0 },
            scenarios: {
              base: { sale_price: 1098416.67, net_profit: 50502, roi_pct: 6.29 },
              conservative: { sale_price: 980000, net_profit: -78000, roi_pct: -9.1 },
            },
            suggested_status: "Aberto com pendencias",
            next_action: "Checar ocupacao e plano juridico",
            pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar desocupacao." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Alves Guimaraes, 866",
              occupancy_status: "ocupado",
              asking_price: 821000,
              estimated_sale_base: 1098416.67,
              sale_comparables_count: 0,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const blocked = screen.getByTestId("radar-imobiliario-bloqueados");
    expect(within(blocked).getByText(/Sao Paulo \/ Pinheiros \/ Rua Alves Guimaraes/i)).toBeInTheDocument();
    expect(within(blocked).getByTestId("candidate-identifier-number")).toHaveTextContent("3970");
    expect(within(blocked).getAllByText(/Bloqueado por prova/i).length).toBeGreaterThan(0);
    expect(within(blocked).getByText(/imovel ocupado/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/entrada acima do Teto Halley/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/sem 3 comparaveis/i)).toBeInTheDocument();

    const advance = screen.queryByTestId("radar-imobiliario-avancar");
    expect(advance ? within(advance).queryByText(/Rua Alves Guimaraes/i) : null).not.toBeInTheDocument();
  });

  it("blocks generic neighborhood source urls from the advance queue", () => {
    const data = {
      thesisRows: [
        {
          id: "3975",
          thesisId: "IM-RADAR-TARGET-CAMPO-02",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL TARGET - Campo Belo generico",
          operation: "Leilao extrajudicial + HF leve | Leilao Imovel | Apartamento | Dentro do teto",
          sourceUrl: "https://www.leilaoimovel.com.br/leilao-de-imovel/sp/sao-paulo/campo-belo",
          entryPrice: 420000,
          currentPrice: 620000,
          targetPrice: 620000,
          realEstateAnalysis: {
            score: 78,
            confidence: 50,
            max_purchase_price: 460000,
            source_validation: {
              status: "ambiguous",
              reason: "Fonte de bairro; abrir lote individual antes de proposta.",
            },
            valuation_evidence: { sale_comparables_count: 4 },
            local_demand_evidence: {
              risk_level: "baixo",
              status_label: "Demanda local ok",
            },
            scenarios: {
              base: { sale_price: 620000, net_profit: 92000, roi_pct: 21.9 },
              conservative: { sale_price: 590000, net_profit: 42000, roi_pct: 10 },
            },
            suggested_status: "Aberto com pendencias",
            next_action: "Abrir lote individual",
            pending_items: [{ priority: "P0", title: "Abrir lote individual", action: "Substituir link generico." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Campo Belo",
              street: "Rua Joao de Sousa Dias",
              occupancy_status: "desocupado",
              sale_comparables_count: 4,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const blocked = screen.getByTestId("radar-imobiliario-bloqueados");
    expect(within(blocked).getByText(/Sao Paulo \/ Campo Belo \/ Rua Joao de Sousa Dias/i)).toBeInTheDocument();
    expect(within(blocked).getAllByText(/Bloqueado por prova/i).length).toBeGreaterThan(0);
    expect(within(blocked).getByText(/fonte generica/i)).toBeInTheDocument();

    const advance = screen.queryByTestId("radar-imobiliario-avancar");
    expect(advance ? within(advance).queryByText(/Campo Belo generico/i) : null).not.toBeInTheDocument();
  });

  it("blocks auction candidates with rights, fractional ownership, or bare ownership terms", () => {
    const data = {
      thesisRows: [
        {
          id: "4101",
          thesisId: "IM-RADAR-LEGAL-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Direitos sobre studio Pinheiros",
          operation: "Direitos sobre imovel + opcionalidade",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/direitos-studio-pinheiros-imovel-4101",
          entryPrice: 313600,
          currentPrice: 522666,
          targetPrice: 522666,
          realEstateAnalysis: {
            score: 88,
            confidence: 82,
            max_purchase_price: 340000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 522666, net_profit: 110000, roi_pct: 35 },
              conservative: { sale_price: 480000, net_profit: 65000, roi_pct: 20 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Galeno de Almeida",
              occupancy_status: "desocupado",
              sale_comparables_count: 3,
              strategy: "Direitos sobre imovel + opcionalidade",
            },
          },
        },
        {
          id: "4102",
          thesisId: "IM-RADAR-LEGAL-02",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Fracao ideal Faria Lima",
          operation: "Fracao comercial em eixo premium",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/fracao-conjunto-comercial-4102",
          entryPrice: 704997,
          currentPrice: 1409994,
          targetPrice: 1409994,
          realEstateAnalysis: {
            score: 86,
            confidence: 80,
            max_purchase_price: 860000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 1409994, net_profit: 250000, roi_pct: 35 },
              conservative: { sale_price: 1200000, net_profit: 90000, roi_pct: 12 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Avenida Brigadeiro Faria Lima",
              occupancy_status: "desocupado",
              sale_comparables_count: 3,
              property_type: "Fracao de conjunto comercial",
            },
          },
        },
        {
          id: "4103",
          thesisId: "IM-RADAR-LEGAL-03",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Nua propriedade Perdizes",
          operation: "Nua propriedade com usufruto vigente",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/nua-propriedade-perdizes-4103",
          entryPrice: 250000,
          currentPrice: 500000,
          targetPrice: 500000,
          realEstateAnalysis: {
            score: 87,
            confidence: 81,
            max_purchase_price: 320000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 500000, net_profit: 140000, roi_pct: 42 },
              conservative: { sale_price: 430000, net_profit: 75000, roi_pct: 22 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Perdizes",
              street: "Rua Cardoso de Almeida",
              occupancy_status: "desocupado",
              sale_comparables_count: 3,
              notes: "Oferta da nua propriedade.",
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const blocked = screen.getByTestId("radar-imobiliario-bloqueados");
    expect(within(blocked).getByText(/Rua Galeno de Almeida/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/Avenida Brigadeiro Faria Lima/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/Rua Cardoso de Almeida/i)).toBeInTheDocument();
    expect(within(blocked).getAllByText(/direitos sobre/i).length).toBeGreaterThan(0);
    expect(within(blocked).getAllByText(/fracao ideal/i).length).toBeGreaterThan(0);
    expect(within(blocked).getAllByText(/nua propriedade/i).length).toBeGreaterThan(0);

    const advance = screen.queryByTestId("radar-imobiliario-avancar");
    expect(advance ? within(advance).queryByText(/Galeno de Almeida/i) : null).not.toBeInTheDocument();
    expect(advance ? within(advance).queryByText(/Faria Lima/i) : null).not.toBeInTheDocument();
    expect(advance ? within(advance).queryByText(/Cardoso de Almeida/i) : null).not.toBeInTheDocument();
  });

  it("blocks auction candidates without official docs, debt total, or possession plan", () => {
    const data = {
      thesisRows: [
        {
          id: "4201",
          thesisId: "IM-RADAR-DOCS-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Leilao sem edital oficial",
          operation: "Leilao Caixa sem edital anexado",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-sem-edital-4201",
          entryPrice: 260000,
          currentPrice: 420000,
          targetPrice: 420000,
          realEstateAnalysis: {
            score: 88,
            confidence: 78,
            max_purchase_price: 320000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 420000, net_profit: 95000, roi_pct: 35 },
              conservative: { sale_price: 390000, net_profit: 60000, roi_pct: 20 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Sem Edital",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: false,
              condo_debt_known: true,
              iptu_debt_known: true,
              sale_comparables_count: 3,
            },
          },
        },
        {
          id: "4202",
          thesisId: "IM-RADAR-DEBT-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Leilao sem custo total de debitos",
          operation: "Leilao judicial com debitos a levantar",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-debitos-4202",
          entryPrice: 240000,
          currentPrice: 390000,
          targetPrice: 390000,
          realEstateAnalysis: {
            score: 86,
            confidence: 76,
            max_purchase_price: 310000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 390000, net_profit: 90000, roi_pct: 37 },
              conservative: { sale_price: 360000, net_profit: 55000, roi_pct: 20 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Moema",
              street: "Rua Sem Debitos",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: true,
              condo_debt_known: false,
              iptu_debt_known: false,
              sale_comparables_count: 3,
            },
          },
        },
        {
          id: "4203",
          thesisId: "IM-RADAR-POSSE-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Ocupado sem plano de posse",
          operation: "Desocupacao por conta do adquirente",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-ocupado-4203",
          entryPrice: 300000,
          currentPrice: 520000,
          targetPrice: 520000,
          realEstateAnalysis: {
            score: 84,
            confidence: 72,
            max_purchase_price: 360000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            listing_reading: { buyer_responsible_for_eviction: true },
            scenarios: {
              base: { sale_price: 520000, net_profit: 120000, roi_pct: 40 },
              conservative: { sale_price: 480000, net_profit: 80000, roi_pct: 25 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Campo Belo",
              street: "Rua Sem Posse",
              occupancy_status: "ocupado",
              first_operation: false,
              has_registration: true,
              has_edital: true,
              condo_debt_known: true,
              iptu_debt_known: true,
              sale_comparables_count: 3,
            },
          },
        },
        {
          id: "4204",
          thesisId: "IM-RADAR-FRAUD-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Leilao com pagamento suspeito",
          operation: "Leilao extrajudicial com Pix fora do edital",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-pix-4204",
          entryPrice: 240000,
          currentPrice: 390000,
          targetPrice: 390000,
          realEstateAnalysis: {
            score: 86,
            confidence: 76,
            max_purchase_price: 310000,
            source_validation: { status: "valid", reason: "Pix em conta de terceiro fora do edital." },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 390000, net_profit: 90000, roi_pct: 37 },
              conservative: { sale_price: 360000, net_profit: 55000, roi_pct: 20 },
            },
            pending_items: [{ key: "source_payment_risk", priority: "P0", title: "Validar fonte e pagamento oficial", action: "Conta de pagamento diverge do edital." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Moema",
              street: "Rua Pix Suspeito",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: true,
              condo_debt_known: true,
              iptu_debt_known: true,
              sale_comparables_count: 3,
            },
          },
        },
        {
          id: "4205",
          thesisId: "IM-RADAR-FIN-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Leilao com FGTS sem prova",
          operation: "Leilao Caixa depende de FGTS e financiamento",
          sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-fgts-4205",
          entryPrice: 260000,
          currentPrice: 420000,
          targetPrice: 420000,
          realEstateAnalysis: {
            score: 87,
            confidence: 78,
            max_purchase_price: 320000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 420000, net_profit: 95000, roi_pct: 35 },
              conservative: { sale_price: 390000, net_profit: 60000, roi_pct: 20 },
            },
            pending_items: [{ key: "financing_dependency", priority: "P0", title: "Validar financiamento/FGTS", action: "Confirmar se edital e banco permitem." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Saude",
              street: "Rua FGTS Sem Prova",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: true,
              condo_debt_known: true,
              iptu_debt_known: true,
              financing_required: true,
              financing_validated: false,
              sale_comparables_count: 3,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const blocked = screen.getByTestId("radar-imobiliario-bloqueados");
    expect(within(blocked).getByText(/Rua Sem Edital/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/Rua Sem Debitos/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/Rua Sem Posse/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/Rua Pix Suspeito/i)).toBeInTheDocument();
    expect(within(blocked).getByText(/Rua FGTS Sem Prova/i)).toBeInTheDocument();
    expect(within(blocked).getAllByText(/sem edital oficial/i).length).toBeGreaterThan(0);
    expect(within(blocked).getAllByText(/debitos sem custo total/i).length).toBeGreaterThan(0);
    expect(within(blocked).getAllByText(/desocupacao sem plano/i).length).toBeGreaterThan(0);
    expect(within(blocked).getAllByText(/fonte\/pagamento nao oficial/i).length).toBeGreaterThan(0);
    expect(within(blocked).getAllByText(/financiamento\/FGTS nao comprovado/i).length).toBeGreaterThan(0);
  });

  it("surfaces positive sourcing score for clean ugly candidates", () => {
    const data = {
      thesisRows: [
        {
          id: "4301",
          thesisId: "IM-RADAR-GARIMPO-01",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Imovel feio com documentacao limpa",
          operation: "Leiloeiro regional oficial, reforma leve e revenda",
          sourceUrl: "https://leiloeiro-regional.example/lote-881",
          entryPrice: 180000,
          currentPrice: 320000,
          targetPrice: 320000,
          realEstateAnalysis: {
            score: 88,
            confidence: 82,
            max_purchase_price: 230000,
            source_validation: { status: "valid", reason: "Lote individual em leiloeiro oficial de cauda longa." },
            valuation_evidence: { sale_comparables_count: 3 },
            sourcing: {
              score: 86,
              tier: "garimpo_qualificado",
              signals: ["reforma precificavel", "saida clara", "fonte oficial individual"],
            },
            scenarios: {
              base: { sale_price: 320000, net_profit: 70000, roi_pct: 31 },
              conservative: { sale_price: 285000, net_profit: 32000, roi_pct: 14 },
            },
            pending_items: [],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Mooca",
              street: "Rua do Garimpo",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: true,
              condo_debt_known: true,
              iptu_debt_known: true,
              sale_comparables_count: 3,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getAllByText(/Garimpo 86\/100/i).length).toBeGreaterThan(1);
    expect(within(portfolio).getByText(/reforma precificavel/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/saida clara/i)).toBeInTheDocument();
  });

  it("infers a blocked garimpo score when the backend has not sent sourcing yet", () => {
    const data = {
      thesisRows: [
        {
          id: "4501",
          thesisId: "IM-RADAR-GARIMPO-PENDING",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Candidato sem score de garimpo",
          operation: "Leilao Caixa com fonte ainda em validacao",
          sourceUrl: "https://leilao.example/lote-4501",
          entryPrice: 210000,
          currentPrice: 340000,
          targetPrice: 340000,
          realEstateAnalysis: {
            score: 64,
            confidence: 40,
            max_purchase_price: 230000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 340000, net_profit: 50000, roi_pct: 20 },
            },
            pending_items: [{ priority: "P0", title: "Validar fonte", action: "Confirmar edital e lote individual." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Saude",
              street: "Rua Sem Garimpo",
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    expect(within(portfolio).getAllByText(/Garimpo bloqueado 45\/100/i).length).toBeGreaterThan(1);
    expect(within(portfolio).getByText(/fonte oficial individual/i)).toBeInTheDocument();
  });

  it("prioritizes the watchlist by sourcing score without moving P0 candidates to advance", () => {
    const data = {
      thesisRows: [
        {
          id: "4401",
          thesisId: "IM-RADAR-GARIMPO-LOW",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Pinheiros score alto sem garimpo",
          operation: "Leilao extrajudicial com prova financeira incompleta",
          sourceUrl: "https://leiloeiro-regional.example/lote-4401",
          entryPrice: 220000,
          currentPrice: 360000,
          targetPrice: 360000,
          realEstateAnalysis: {
            score: 92,
            confidence: 80,
            max_purchase_price: 260000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            sourcing: {
              score: 25,
              tier: "bloqueado_por_p0",
              signals: ["fonte oficial individual"],
            },
            scenarios: {
              base: { sale_price: 360000, net_profit: 80000, roi_pct: 30 },
              conservative: { sale_price: 330000, net_profit: 45000, roi_pct: 17 },
            },
            pending_items: [{ priority: "P0", title: "Aprovar capital final", action: "Confirmar limite interno antes de proposta." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Score Alto",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: true,
              condo_debt_known: true,
              iptu_debt_known: true,
              financing_validated: true,
            },
          },
        },
        {
          id: "4402",
          thesisId: "IM-RADAR-GARIMPO-HIGH",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Perdizes garimpo primeiro",
          operation: "Leiloeiro regional oficial, reforma leve e revenda",
          sourceUrl: "https://leiloeiro-regional.example/lote-4402",
          entryPrice: 180000,
          currentPrice: 320000,
          targetPrice: 320000,
          realEstateAnalysis: {
            score: 70,
            confidence: 80,
            max_purchase_price: 230000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            sourcing: {
              score: 75,
              tier: "bloqueado_por_p0",
              signals: ["fonte oficial individual", "reforma precificavel", "saida clara"],
            },
            scenarios: {
              base: { sale_price: 320000, net_profit: 70000, roi_pct: 31 },
              conservative: { sale_price: 285000, net_profit: 32000, roi_pct: 14 },
            },
            pending_items: [{ priority: "P0", title: "Aprovar capital final", action: "Confirmar limite interno antes de proposta." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Perdizes",
              street: "Rua Garimpo Primeiro",
              occupancy_status: "desocupado",
              has_registration: true,
              has_edital: true,
              condo_debt_known: true,
              iptu_debt_known: true,
              financing_validated: true,
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const watchlist = screen.getByTestId("radar-imobiliario-watchlist");
    const buttons = within(watchlist).getAllByRole("button", { name: /Abrir/i });
    expect(buttons[0]).toHaveAccessibleName(/Perdizes garimpo primeiro/i);
    expect(within(watchlist).getAllByText(/Garimpo bloqueado 75\/100/i).length).toBeGreaterThan(1);
    expect(screen.queryByTestId("radar-imobiliario-avancar")).not.toBeInTheDocument();
  });

  it("keeps overview and active candidate counts scoped to the same open radar queue", () => {
    const data = {
      thesisRows: [
        {
          id: "501",
          thesisId: "IM-RADAR-501",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Watchlist coerente",
          entryPrice: 300000,
          currentPrice: 420000,
          targetPrice: 420000,
          sourceUrl: "https://www.exemplo.com.br/imovel/watchlist-501",
          realEstateAnalysis: {
            score: 72,
            confidence: 52,
            max_purchase_price: 340000,
            source_validation: { status: "valid" },
            valuation_evidence: { sale_comparables_count: 3 },
            scenarios: {
              base: { sale_price: 420000, net_profit: 70000, roi_pct: 23 },
              conservative: { sale_price: 390000, net_profit: 25000, roi_pct: 8 },
            },
            pending_items: [{ priority: "P0", title: "Confirmar matricula", action: "Validar matricula." }],
            candidate: { city: "Sao Paulo", neighborhood: "Saude", street: "Rua Coerente" },
          },
        },
        {
          id: "502",
          thesisId: "IM-RADAR-502",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "REAL - Bloqueado coerente",
          entryPrice: 500000,
          currentPrice: 650000,
          targetPrice: 650000,
          sourceUrl: "https://www.leilaoimovel.com.br/leilao-de-imovel/sp/sao-paulo/campo-belo",
          realEstateAnalysis: {
            score: 66,
            confidence: 50,
            max_purchase_price: 560000,
            source_validation: { status: "ambiguous" },
            valuation_evidence: { sale_comparables_count: 4 },
            scenarios: {
              base: { sale_price: 650000, net_profit: 80000, roi_pct: 18 },
              conservative: { sale_price: 610000, net_profit: 30000, roi_pct: 6 },
            },
            pending_items: [{ priority: "P0", title: "Trocar link generico", action: "Abrir lote individual." }],
            candidate: { city: "Sao Paulo", neighborhood: "Campo Belo", street: "Rua Generica" },
          },
        },
        {
          id: "503",
          thesisId: "IM-RADAR-503",
          front: "imoveis",
          status: "Fechada",
          statusGroup: "Historica",
          isOpen: false,
          asset: "REAL - Fechado aprendizado",
          entryPrice: 450000,
          currentPrice: 450000,
          targetPrice: 450000,
          realEstateAnalysis: {
            score: 42,
            confidence: 20,
            max_purchase_price: 360000,
            scenarios: { base: { sale_price: 450000, net_profit: -20000, roi_pct: -4 } },
          },
        },
        {
          id: "504",
          thesisId: "IM-RADAR-504",
          front: "imoveis",
          status: "Descartado",
          statusGroup: "Historica",
          isOpen: false,
          asset: "REAL - Descartado aprendizado",
          entryPrice: 600000,
          currentPrice: 600000,
          targetPrice: 600000,
          realEstateAnalysis: {
            score: 35,
            confidence: 18,
            max_purchase_price: 420000,
            scenarios: { base: { sale_price: 600000, net_profit: -50000, roi_pct: -8 } },
          },
        },
      ],
    };

    const overviewRender = render(<RadarImobiliario data={data} />);

    const hero = screen.getByTestId("radar-imobiliario-hero");
    expect(hero).toHaveTextContent(/Candidatos abertos/i);
    expect(hero).toHaveTextContent(/2/);
    expect(hero).toHaveTextContent(/Fechados\/aprendizados/i);
    expect(hero).toHaveTextContent(/fora da fila ativa/i);
    expect(hero).not.toHaveTextContent(/Investigar\/monitorar/i);
    overviewRender.unmount();

    render(<RadarImobiliario data={data} section="candidatos" />);

    const decisionStrip = screen.getByLabelText(/Resumo de decis/i);
    expect(within(decisionStrip).getByText("1 candidato com prova pendente")).toBeInTheDocument();
    expect(within(decisionStrip).getByText("1 caso travado por prova")).toBeInTheDocument();
    expect(within(decisionStrip).getByText("2 casos para calibracao")).toBeInTheDocument();
    expect(screen.getByText(/Fila ativa - 2 candidatos reais abertos/i)).toBeInTheDocument();
    expect(screen.getByText(/As tres raias abaixo somam so os abertos/i)).toBeInTheDocument();
    expect(screen.getByText(/2 casos reais encerrados ficam fora desta mesa/i)).toBeInTheDocument();
  });

  it("shows thesis code and property type for closed real estate candidates", () => {
    const data = {
      thesisRows: [
        {
          id: "4002",
          thesisId: "IM-RADAR-TARGET-PIN-04",
          front: "imoveis",
          status: "Fechada",
          statusGroup: "Historica",
          isOpen: false,
          asset: "Sao Paulo / Pinheiros / Rua Padre Carvalho / Entrada 1.179M Saida 1.350M",
          entryPrice: 1179000,
          currentPrice: 1350000,
          targetPrice: 1350000,
          realEstateAnalysis: {
            score: 48,
            confidence: 58,
            max_purchase_price: 691296,
            scenarios: { base: { sale_price: 1350000, net_profit: -29320, roi_pct: -2.1 } },
            suggested_status: "Descartado",
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Padre Carvalho, 129",
              property_type: "Casa em vila",
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const closed = screen.getByTestId("radar-imobiliario-fechados");
    expect(within(closed).getByText(/Tese IM-RADAR-TARGET-PIN-04/i)).toBeInTheDocument();
    expect(within(closed).getByText(/Casa em vila/i)).toBeInTheDocument();
    expect(within(closed).getByTestId("candidate-identifier-number")).toHaveTextContent("4002");
  });

  it("renders API real estate candidates with raw asking price and top-level address in open candidates", () => {
    const comparableUrl = "https://www.chavesnamao.com.br/imovel/casa-a-venda-2-quartos-com-garagem-sp-sao-paulo-pinheiros-200m2-RS3200000/id-39888317/";
    const data = normalizeCockpitHalley(
      {
        realEstateCandidates: {
          candidates: [
            {
              id: 26,
              title: "PIN-06 / Casa 5 Padre Carvalho, 129",
              status: "Aberto com pendencias",
              candidate_date: "2026-05-23T16:10:00-03:00",
              source_url: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-casa-a-venda-em-leilao-imovel-bradesco-2844902",
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              street: "Rua Padre Carvalho, 129 - Casa 5",
              property_type: "Casa em vila",
              asking_price: 1610827.63,
              estimated_sale_base: 2880000,
              occupancy_status: "ocupado",
              source_validation_status: "valid",
              source_validation_reason: "Fonte individual do Leilao Imovel para a Casa 5.",
              sale_comparables_count: 1,
              sale_comparables: [
                {
                  source: "ChavesNaMao",
                  source_url: comparableUrl,
                  price: 3200000,
                  area_m2: 200,
                  evidence_type: "same_address_listing",
                },
              ],
              analysis: {
                score: 61,
                confidence: 63,
                max_purchase_price: 1610827.63,
                scenarios: {
                  base: { sale_price: 2880000, net_profit: 480000, roi_pct: 29.8 },
                  conservative: { sale_price: 2600000, net_profit: 120000, roi_pct: 7.4 },
                },
                suggested_status: "Aberto com pendencias",
                pending_items: [{ priority: "P0", title: "Confirmar divida de condominio", action: "Validar antes de proposta." }],
              },
            },
          ],
        },
      },
      new Date("2026-05-23T19:10:00Z"),
    );

    render(<RadarImobiliario data={data} section="candidatos" />);

    const openCandidates = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(openCandidates).getByText(/Sao Paulo \/ Pinheiros \/ Rua Padre Carvalho, 129 - Casa 5/i)).toBeInTheDocument();
    expect(within(openCandidates).getByText(/Casa 5 Padre Carvalho, 129/i)).toBeInTheDocument();
    expect(within(openCandidates).getByText(/Origem: PIN-06 \/ Casa 5 Padre Carvalho, 129/i)).toBeInTheDocument();
    expect(within(openCandidates).getByText(/R\$ 1\.610\.828/i)).toBeInTheDocument();
    expect(within(openCandidates).getByTestId("candidate-identifier-number")).toHaveTextContent("26");
  });

  it("keeps the property name visible when an API candidate has a title but no parsed street", () => {
    const data = normalizeCockpitHalley(
      {
        realEstateCandidates: {
          candidates: [
            {
              id: 26,
              title: "PIN-06 / Casa 5 Padre Carvalho, 129",
              status: "Aberto com pendencias",
              candidate_date: "2026-05-23T16:10:00-03:00",
              source_url: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-casa-a-venda-em-leilao-imovel-bradesco-2844902",
              city: "Sao Paulo",
              neighborhood: "Pinheiros",
              property_type: "Casa em vila",
              asking_price: 1610827.63,
              estimated_sale_base: 2880000,
              source_validation_status: "valid",
              sale_comparables_count: 1,
              analysis: {
                score: 61,
                confidence: 63,
                max_purchase_price: 1598995,
                scenarios: { base: { sale_price: 2880000, net_profit: 480000, roi_pct: 29.8 } },
                suggested_status: "Aberto com pendencias",
                pending_items: [{ priority: "P0", title: "Confirmar divida de condominio", action: "Validar antes de proposta." }],
              },
            },
          ],
        },
      },
      new Date("2026-05-23T19:10:00Z"),
    );

    render(<RadarImobiliario data={data} section="candidatos" />);

    const openCandidates = screen.getByTestId("radar-imobiliario-abertos");
    expect(within(openCandidates).getByText(/Sao Paulo \/ Pinheiros \/ Casa 5 Padre Carvalho, 129/i)).toBeInTheDocument();
    expect(within(openCandidates).queryByText(/PIN Padre Carvalho,/i)).not.toBeInTheDocument();
  });

  it("links real sale comparables in the competitor map for radar candidates", async () => {
    const user = userEvent.setup();
    const comparableUrl = "https://www.chavesnamao.com.br/imovel/apartamento-a-venda-campo-belo-real/id-42367031/";
    const data = {
      thesisRows: [
        {
          id: "3975",
          thesisId: "IM-RADAR-TARGET-CAM-02",
          front: "imoveis",
          status: "Aberta - Atencao",
          statusGroup: "Go-live",
          isOpen: true,
          asset: "Campo Belo Helbor 65m",
          operation: "Leilao extrajudicial + HF leve | Leilao Imovel | Apartamento",
          sourceUrl: "https://www.frazaoleiloes.com.br/Auction/LotDetails/37570",
          entryPrice: 852901,
          targetPrice: 680000,
          expectedPct: -111.6,
          realEstateAnalysis: {
            score: 42,
            confidence: 52,
            max_purchase_price: 430000,
            valuation_evidence: {
              sale_comparables_count: 1,
              comparables: [
                {
                  price: 680000,
                  area_m2: 65.09,
                  source: "Chaves na Mao",
                  source_url: comparableUrl,
                  note: "mesmo endereco e area privativa",
                },
              ],
            },
            scenarios: {
              base: { sale_price: 680000, net_profit: -172901, roi_pct: -20.3 },
              conservative: { sale_price: 650000, net_profit: -210000, roi_pct: -24.6 },
            },
            suggested_status: "Aberto com pendencias",
            next_action: "Revalidar saida com anuncios do mesmo predio",
            pending_items: [{ priority: "P0", title: "Validar saida", action: "Abrir comparavel real antes de proposta." }],
            candidate: {
              city: "Sao Paulo",
              neighborhood: "Campo Belo",
              street: "Rua Vieira de Morais, 2098",
              private_area_m2: 65.09,
              asking_price: 852901,
              sale_comparables_count: 1,
              sale_comparables: [
                {
                  price: 680000,
                  area_m2: 65.09,
                  source: "Chaves na Mao",
                  source_url: comparableUrl,
                  note: "mesmo endereco e area privativa",
                },
              ],
            },
          },
        },
      ],
    };

    render(<RadarImobiliario data={data} section="candidatos" />);

    const portfolio = screen.getByTestId("radar-imobiliario-portfolio");
    await user.click(within(portfolio).getByRole("button", { name: /Abrir Campo Belo Helbor 65m/i }));

    expect(within(portfolio).getByText(/Mapa de concorrentes/i)).toBeInTheDocument();
    const comparableLink = within(portfolio).getByRole("link", { name: /Abrir link real da Ref\. venda 01/i });
    expect(comparableLink).toHaveAttribute("href", comparableUrl);
    expect(within(portfolio).getByText(/Chaves na Mao/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/1 links reais/i)).toBeInTheDocument();
    expect(within(portfolio).queryByRole("link", { name: /Abrir link real da Ref\. venda 02/i })).not.toBeInTheDocument();
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
