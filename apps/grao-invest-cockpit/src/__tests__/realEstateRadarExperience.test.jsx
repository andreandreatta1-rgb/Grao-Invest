import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Teses from "../screens/Teses.jsx";

const realEstateRows = [
  {
    id: "LEILAO-1",
    thesisId: "LEILAO-1",
    asset: "REAL - Caixa Tatuape Serra de Jurea 1206",
    front: "Im\u00f3veis",
    direction: "Alta",
    expectedPct: 21,
    structure: "Leil\u00e3o / venda online Caixa",
    entryPrice: 118000,
    currentPrice: 196000,
    sourceUrl: "https://www.caixa.gov.br/imoveis/imovel-exemplo",
    openedAt: "2026-05-04T10:00:00.000Z",
    exitRule: "Confirmar ocupacao e debitos",
    outcome: "Pend\u00eancias abertas",
    days: 0,
    status: "Aberta - Atencao",
    statusGroup: "Go-live",
    resultPct: 0,
    resultKind: "estimate",
    isOpen: true,
    hypothesis: "Imovel de leilao com desconto potencial.",
    learning: "Confirmar pendencias antes da proposta.",
    realEstateAnalysis: {
      score: 82,
      confidence: 42,
      suggested_status: "Aberto com pendencias",
      next_action: "Confirmar ocupacao, matricula e debitos",
      price_ceiling_status: "Dentro do teto",
      max_purchase_price: 124000,
      price_gap_to_ceiling: -6000,
      cash_needed: 26000,
      breakeven_sale_price: 160000,
      target_roi_pct: 18,
      base_profit_pct: 21,
      scenarios: {
        base: { sale_price: 196000, net_profit: 22000, roi_pct: 21 },
      },
      pending_items: [
        { key: "ocupacao", priority: "P0", title: "Confirmar ocupacao", action: "Validar ocupacao antes de proposta." },
      ],
      clarified_items: [],
      score_breakdown: [],
      confidence_breakdown: [],
    },
  },
  {
    id: "HF-1",
    thesisId: "IM-RADAR-17",
    asset: "Pinheiros apartamento para reforma leve",
    front: "Im\u00f3veis",
    direction: "Alta",
    expectedPct: 15,
    structure: "House Flipping com reforma leve e revenda",
    entryPrice: 240000,
    currentPrice: 305000,
    exitRule: "Validar custo de obra",
    outcome: "Observando",
    days: 0,
    statusGroup: "Em an\u00e1lise",
    resultPct: 0,
    resultKind: "estimate",
    isOpen: true,
    hypothesis: "Compra com reforma curta.",
    learning: "Orcar reforma antes de proposta.",
    realEstateAnalysis: {
      score: 67,
      confidence: 35,
      pending_items: [],
      next_action: "Orcar reforma leve",
      scenarios: {
        base: { sale_price: 340000, net_profit: 48000, roi_pct: 16.4 },
      },
      candidate: {
        building_condition: "Hall e elevadores modernizados; fachada em bom estado; portaria organizada.",
        condo_condition: "bom",
        building_age_profile: "Antigo em modernização",
        facade_condition: "Fachada em bom estado",
        hall_condition: "Hall modernizado",
        elevators_condition: "Elevadores modernizados",
        concierge_condition: "Portaria organizada",
        garage_condition: "Garagem funcional",
        extra_fee_status: "Sem chamada extra informada",
        avcb_status: "Pendente",
        renovation_budget: 40000,
        transaction_costs: 12000,
      },
    },
  },
  {
    id: "DIRECT-1",
    thesisId: "DIRECT-1",
    asset: "QuintoAndar Belenzinho 25m2",
    front: "Im\u00f3veis",
    direction: "Alta",
    expectedPct: 11,
    structure: "Compra direta pelo QuintoAndar",
    entryPrice: 199000,
    currentPrice: 230000,
    sourceUrl: "https://www.quintoandar.com.br/imovel/123",
    openedAt: "2026-05-03T12:00:00.000Z",
    exitRule: "Simular negociacao",
    outcome: "Observando",
    days: 1,
    statusGroup: "Em an\u00e1lise",
    resultPct: 0,
    resultKind: "estimate",
    isOpen: true,
    hypothesis: "Vendedor direto com espaco para negociacao.",
    learning: "Testar preco negociado.",
    realEstateAnalysis: {
      score: 61,
      confidence: 48,
      suggested_status: "Estudar com cautela",
      next_action: "Simular proposta com desconto",
      price_ceiling_status: "Acima do teto",
      max_purchase_price: 180000,
      price_gap_to_ceiling: 19000,
      scenarios: {
        base: { sale_price: 230000, net_profit: 12000, roi_pct: 8.5 },
      },
      pending_items: [],
      clarified_items: [],
      score_breakdown: [],
      confidence_breakdown: [],
    },
  },
  {
    id: "RENDA-1",
    thesisId: "RENDA-1",
    asset: "Studio com plano B de aluguel",
    front: "Im\u00f3veis",
    direction: "Alta",
    expectedPct: 7,
    structure: "Renda / plano B com locacao",
    entryPrice: 220000,
    currentPrice: 235000,
    exitRule: "Validar aluguel",
    outcome: "Observando",
    days: 0,
    statusGroup: "Em an\u00e1lise",
    resultPct: 0,
    resultKind: "estimate",
    isOpen: true,
    hypothesis: "Plano B por aluguel se venda demorar.",
    learning: "Validar renda mensal.",
    realEstateAnalysis: { score: 58, confidence: 33, pending_items: [], next_action: "Validar aluguel de mercado" },
  },
  {
    id: "PLANTA-1",
    thesisId: "PLANTA-1",
    asset: "Lancamento zona leste",
    front: "Im\u00f3veis",
    direction: "Alta",
    expectedPct: 6,
    structure: "Lancamento / imovel na planta",
    entryPrice: 180000,
    currentPrice: 190000,
    exitRule: "Monitorar entrega",
    outcome: "Observando",
    days: 0,
    statusGroup: "Em an\u00e1lise",
    resultPct: 0,
    resultKind: "estimate",
    isOpen: true,
    hypothesis: "Ciclo longo de valorizacao.",
    learning: "Acompanhar risco de prazo.",
    realEstateAnalysis: { score: 44, confidence: 24, pending_items: [], next_action: "Monitorar ciclo de obra" },
  },
];

const strategyTerritoryReport = {
  summary: {
    strategyCount: 8,
    territoryCount: 12,
    matrixBriefCount: 96,
    sourceCandidateCount: 16,
    sourceConfirmedRequalificationCount: 4,
  },
  matrixBriefs: [
    {
      id: "IM-BUSCA-centro-condominio",
      trustLevel: "hypothesis",
      strategyId: "condominio_antigo_requalificacao",
      strategyLabel: "Condominio antigo em requalificacao",
      territoryLabel: "Centro / Republica / Bela Vista",
      title: "BUSCA - Condominio antigo em requalificacao - Centro",
      decisionRule: "Nao virar tese de compra ate existir unidade, preco e comparaveis.",
      nextSearchQueries: [
        "\"Bela Vista\" \"condominio antigo\" \"fachada reformada\" apartamento Sao Paulo",
      ],
    },
    {
      id: "IM-BUSCA-pinheiros-flip",
      trustLevel: "hypothesis",
      strategyId: "house_flipping_leve",
      strategyLabel: "House flipping leve",
      territoryLabel: "Pinheiros",
      title: "BUSCA - House flipping leve - Pinheiros",
      decisionRule: "Nao virar tese sem unidade e preco teto.",
    },
  ],
  strategyCandidateWatchlist: [
    {
      id: "IM-FONTE-vivareal-wish-675",
      type: "strategy_source_candidate",
      trustLevel: "source_listed",
      strategyId: "lancamentos_ciclo_entrega",
      strategyLabel: "Lancamentos / ciclo de entrega",
      territoryLabel: "Agua Funda / Jabaquara / Saude",
      title: "VivaReal - WISH 675 / Vila Monte Alegre",
      sourceName: "VivaReal Lancamentos",
      sourceSummary: "Pagina de lancamento usada para acompanhar preco, entrega, estoque e risco de prazo.",
      candidateAngle: "Validar prazo e preco contra usado reformado.",
      decisionRule: "Nao vira tese de compra ate existir unidade, preco pedido, comparaveis e P0 fechados.",
    },
    {
      id: "IM-FONTE-caixa-zona-leste",
      type: "strategy_source_candidate",
      trustLevel: "source_listed",
      strategyId: "leilao_venda_online",
      strategyLabel: "Leilao/venda online",
      territoryLabel: "Zona Leste preco baixo",
      title: "CAIXA - Residencial Nova Itaquera",
      sourceName: "CAIXA Imoveis",
      sourceSummary: "Fonte de leilao Caixa para triagem de apartamento compacto em Sao Paulo.",
      candidateAngle: "Comparar lance minimo, avaliacao, ocupacao e custo juridico.",
      decisionRule: "Nao vira tese de compra ate existir unidade, preco pedido, comparaveis e P0 fechados.",
    },
  ],
  condominiumRequalificationWatchlist: [
    {
      id: "IM-SINAL-lotus",
      trustLevel: "source_confirmed",
      strategyId: "condominio_antigo_requalificacao",
      strategyLabel: "Condominio antigo em requalificacao",
      territoryLabel: "Centro / Republica / Bela Vista",
      title: "Cond Edif Lotus - Bela Vista",
      sourceName: "Lello Imoveis",
      sourceSummary: "Pagina de condominio descreve predio com fachada reformada.",
    },
  ],
};

describe("real estate radar experience", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("opens the radar as a deal cockpit with a focused candidate and collapsed support panels", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));

    const cockpit = screen.getByTestId("real-estate-deal-cockpit");
    expect(within(cockpit).getByText(/Este candidato deve avan.ar/i)).toBeInTheDocument();
    expect(within(cockpit).getByText(/Fila de decis.o/i)).toBeInTheDocument();
    expect(within(cockpit).getByText(/Ritual de avalia..o/i)).toBeInTheDocument();
    expect(within(cockpit).getByText(/Pre.o/i)).toBeInTheDocument();
    expect(within(cockpit).getAllByText(/Pr.dio/i).length).toBeGreaterThan(0);
    expect(within(cockpit).getByText("Reforma")).toBeInTheDocument();
    expect(within(cockpit).getByText(/Sa.da/i)).toBeInTheDocument();
    expect(within(cockpit).getByText("Risco")).toBeInTheDocument();
    expect(within(cockpit).getByRole("button", { name: "Segurar" })).toBeInTheDocument();
    expect(screen.getByTestId("real-estate-support-panels")).toBeInTheDocument();
    expect(screen.getByTestId("real-estate-support-panels").querySelectorAll("details:not([open])").length).toBeGreaterThanOrEqual(3);

    fireEvent.click(screen.getByText(/Explorar estrat.gias/i));
    const frontCards = screen.getByTestId("real-estate-front-cards");
    expect(within(frontCards).getByText("Leil\u00e3o / Caixa")).toBeInTheDocument();
    expect(within(frontCards).getByText("House Flipping")).toBeInTheDocument();
    expect(within(frontCards).getByText("Compra Direta")).toBeInTheDocument();
    expect(within(frontCards).getByText("Renda / Plano B")).toBeInTheDocument();
    expect(within(frontCards).getByText("Lan\u00e7amentos")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Adicionar candidato"));
    expect(screen.getByText("Importar link")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Cole aqui o link/i)).toBeInTheDocument();
  });

  it("records a local evaluation decision from the deal cockpit", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));

    const cockpit = screen.getByTestId("real-estate-deal-cockpit");
    fireEvent.change(within(cockpit).getByLabelText(/Motivo da decis.o/i), {
      target: { value: "Aguardando ocupacao e matricula antes de proposta." },
    });
    fireEvent.click(within(cockpit).getByRole("button", { name: "Segurar" }));

    expect(within(cockpit).getByText(/Decis.o registrada: Segurar/i)).toBeInTheDocument();
    expect(within(cockpit).getAllByText(/Aguardando ocupacao/i).length).toBeGreaterThan(0);
  });

  it("shows source metadata and simulates negotiated prices inside the real estate detail", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-DIRECT-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Caso real em estudo")).toBeInTheDocument();
    expect(drawer).toHaveTextContent("Fonte: quintoandar.com.br");
    expect(drawer).toHaveTextContent("Coleta: 03/05/2026");
    expect(within(drawer).getByText("Simular pre\u00e7o negociado")).toBeInTheDocument();

    fireEvent.click(within(drawer).getByRole("button", { name: "-10%" }));

    expect(within(drawer).getByText("R$ 179,10K")).toBeInTheDocument();
    expect(within(drawer).getByText(/R\$ 900,00 abaixo do teto/i)).toBeInTheDocument();
  });

  it("opens the candidates for a strategy when clicking a real estate category card", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByText(/Explorar estrat.gias/i));
    fireEvent.click(screen.getByRole("button", { name: /Ver candidatos Leil.o \/ Caixa/i }));

    expect(screen.getByText("Candidatos em Leil\u00e3o / Caixa")).toBeInTheDocument();
    expect(screen.getByText("1 candidato filtrado")).toBeInTheDocument();
    expect(screen.getByTestId("teses-row-LEILAO-1")).toBeInTheDocument();
    expect(screen.queryByTestId("teses-row-HF-1")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Limpar filtro imobili.rio/i }));

    expect(screen.getByText("Todos os candidatos imobili\u00e1rios")).toBeInTheDocument();
    expect(screen.getByTestId("teses-row-HF-1")).toBeInTheDocument();
  });

  it("shows strategy-territory briefs as search hypotheses without mixing them into registered candidates", () => {
    render(<Teses data={{ thesisRows: realEstateRows, realEstateStrategyTerritoryCandidates: strategyTerritoryReport }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getAllByText(/Briefs por estrat.gia e territ.rio/i)[0]);

    const briefsPanel = screen.getByTestId("real-estate-strategy-territory-briefs");
    expect(within(briefsPanel).getByText("96")).toBeInTheDocument();
    expect(within(briefsPanel).getByText("16")).toBeInTheDocument();
    expect(within(briefsPanel).getAllByText(/Hip.tese de busca/i).length).toBeGreaterThan(0);
    expect(within(briefsPanel).getAllByText(/Fonte candidata/i).length).toBeGreaterThan(0);
    expect(within(briefsPanel).getAllByText(/Sinal confirmado/i).length).toBeGreaterThan(0);
    expect(within(briefsPanel).getAllByText(/Condom.nio antigo em requalifica..o/i).length).toBeGreaterThan(0);
    expect(within(briefsPanel).getByText(/Cond Edif Lotus/i)).toBeInTheDocument();
    expect(within(briefsPanel).getByText(/VivaReal - WISH 675/i)).toBeInTheDocument();
    expect(within(briefsPanel).getByText(/N.o virar? tese de compra/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Explorar estrat.gias/i));
    const requalificationCard = screen.getByTestId("real-estate-front-card-requalification");
    expect(within(requalificationCard).getByText(/Briefs busca/i)).toBeInTheDocument();
    expect(within(requalificationCard).getByText("1")).toBeInTheDocument();
    const launchCard = screen.getByTestId("real-estate-front-card-launch");
    const launchSourceCell = within(launchCard).getByText(/Fontes/i).parentElement;
    expect(launchSourceCell).not.toBeNull();
    expect(within(launchSourceCell).getByText("1")).toBeInTheDocument();
    expect(screen.queryByTestId("teses-row-IM-BUSCA-centro-condominio")).not.toBeInTheDocument();
    expect(screen.queryByTestId("teses-row-IM-FONTE-vivareal-wish-675")).not.toBeInTheDocument();
  });

  it("shows the house flipping building-fit principle in the candidate detail", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Filtro HF: prédio")).toBeInTheDocument();
    expect(within(drawer).getByText("O que não pode ser melhorado tem que estar bom")).toBeInTheDocument();
    expect(within(drawer).getByText("Prédio favorável")).toBeInTheDocument();
    expect(within(drawer).getByText(/Hall e elevadores modernizados/i)).toBeInTheDocument();
  });

  it("presents the real estate detail as a decision mind map before technical blocks", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    const map = within(drawer).getByTestId("real-estate-decision-map");
    expect(within(map).getByText(/Mapa mental da decis/i)).toBeInTheDocument();
    expect(within(map).getByText(/Este im.vel deve avan.ar/i)).toBeInTheDocument();
    expect(within(map).getAllByText(/Orcar reforma leve/i).length).toBeGreaterThan(0);
    expect(within(map).getByText("Tese")).toBeInTheDocument();
    expect(within(map).getByText(/Pr.dio/i)).toBeInTheDocument();
    expect(within(map).getByText("Reforma")).toBeInTheDocument();
    expect(within(map).getByText(/N.meros/i)).toBeInTheDocument();
    expect(within(map).getAllByText(/Decis.o/i).length).toBeGreaterThan(0);
    expect(within(map).getByText(/O que pode matar a tese/i)).toBeInTheDocument();
    expect(within(drawer).queryByTestId("real-estate-decision-summary")).not.toBeInTheDocument();

    const technicalDetails = within(drawer).getByTestId("real-estate-technical-details");
    const numbersGroup = within(technicalDetails).getByTestId("journey-detail-numeros");
    expect(numbersGroup).not.toHaveAttribute("open");
  });

  it("shows the asymmetry map with a 20 percent financing option", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Mapa de Assimetria")).toBeInTheDocument();
    expect(within(drawer).getByText("Financiamento 20% entrada")).toBeInTheDocument();
    expect(within(drawer).getByText("Caixa estimado: R$ 100K")).toBeInTheDocument();
    expect(within(drawer).getByText("Dívida financiada: R$ 192K")).toBeInTheDocument();
    expect(within(drawer).getByText("Margem estimada: R$ 48K")).toBeInTheDocument();
  });

  it("shows neighborhood and condo radar cards before selecting candidates", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));

    fireEvent.click(screen.getByText(/Explorar territ.rios/i));

    const radar = screen.getByTestId("neighborhood-condo-radar");
    expect(within(radar).getByText("Radar de bairros e condomínios")).toBeInTheDocument();
    expect(within(radar).getByText("Pinheiros")).toBeInTheDocument();
    expect(within(radar).getByText("Barreira de reposição")).toBeInTheDocument();
    expect(within(radar).getByText("Prédios antigos bons")).toBeInTheDocument();

    fireEvent.click(within(radar).getByRole("button", { name: /Filtrar candidatos Pinheiros/i }));

    expect(screen.getByText("Candidatos em Pinheiros")).toBeInTheDocument();
    expect(screen.getByTestId("teses-row-HF-1")).toBeInTheDocument();
    expect(screen.queryByTestId("teses-row-LEILAO-1")).not.toBeInTheDocument();
  });

  it("shows structured building and condominium fields in real estate details", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Prédio e condomínio")).toBeInTheDocument();
    expect(within(drawer).getByText("Antigo em modernização")).toBeInTheDocument();
    expect(within(drawer).getByText("Fachada em bom estado")).toBeInTheDocument();
    expect(within(drawer).getByText("Hall modernizado")).toBeInTheDocument();
    expect(within(drawer).getByText("Elevadores modernizados")).toBeInTheDocument();
    expect(within(drawer).getByText("Sem chamada extra informada")).toBeInTheDocument();
  });

  it("scores whether the building supports the house flipping thesis", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Score Prédio Bom")).toBeInTheDocument();
    expect(within(drawer).getAllByText("78/100").length).toBeGreaterThan(0);
    expect(within(drawer).getAllByText("Sustenta a tese HF").length).toBeGreaterThan(0);
    expect(within(drawer).getByText("Itens fortes: 7")).toBeInTheDocument();
    expect(within(drawer).getByText("Pendências: 1")).toBeInTheDocument();
  });

  it("shows a practical house flipping visit checklist", () => {
    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    expect(within(drawer).getByText("Checklist de visita HF")).toBeInTheDocument();
    expect(within(drawer).getByText("Apartamento")).toBeInTheDocument();
    expect(within(drawer).getByText("Verificar elétrica, hidráulica, piso, janelas, infiltração, luz natural e ruído.")).toBeInTheDocument();
    expect(within(drawer).getAllByText("Prédio").length).toBeGreaterThan(0);
    expect(within(drawer).getByText("Fotografar fachada, hall, elevadores, garagem, portaria e áreas comuns.")).toBeInTheDocument();
    expect(within(drawer).getByText("Corretor / vendedor")).toBeInTheDocument();
    expect(within(drawer).getByText("Confirmar motivo da venda, abertura para proposta, prazo, documentação e chamadas extras.")).toBeInTheDocument();
  });

  it("persists visit checklist evidence through the candidate API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        visit_evidence: [
          { section: "Apartamento", evidence: "Fotos da cozinha e banheiro anexadas; sem infiltração aparente." },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Teses data={{ thesisRows: realEstateRows }} />);

    fireEvent.click(screen.getByRole("button", { name: /Abrir radar imobili.rio/i }));
    fireEvent.click(screen.getByTestId("teses-row-HF-1"));

    const drawer = screen.getByText("Ficha completa da tese").closest("aside");
    const apartmentEvidence = within(drawer).getByLabelText("Evidência da visita: Apartamento");
    fireEvent.change(apartmentEvidence, { target: { value: "Fotos da cozinha e banheiro anexadas; sem infiltração aparente." } });
    fireEvent.click(within(drawer).getByRole("button", { name: "Registrar evidência Apartamento" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/real-estate/candidates/17/visit-evidence",
      expect.objectContaining({ method: "POST" }),
    ));

    const [, request] = fetchMock.mock.calls[0];
    expect(JSON.parse(request.body)).toEqual({
      section: "Apartamento",
      evidence: "Fotos da cozinha e banheiro anexadas; sem infiltração aparente.",
    });
    expect(within(drawer).getByText("Evidência registrada")).toBeInTheDocument();
    expect(within(drawer).getAllByText(/Fotos da cozinha e banheiro anexadas/i).length).toBeGreaterThan(0);
  });
});
