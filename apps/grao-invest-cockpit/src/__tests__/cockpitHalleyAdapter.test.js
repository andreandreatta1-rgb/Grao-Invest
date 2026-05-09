import { afterEach, describe, expect, it, vi } from "vitest";
import { normalizeCockpitHalley, statusToUi } from "../data/cockpitHalleyAdapter.js";
import { fetchCockpitPayloads } from "../data/cockpitHalleyApi.js";
import { mockCockpitHalleyPayloads } from "../data/mockCockpitHalley.js";

const now = new Date("2026-05-03T12:00:00Z");

const fixturePayloads = {
  dashboardSummary: {
    updated_at: "2026-05-03T10:00:00Z",
    thesis_history_overview: {
      total_tested: 1727,
      success_rate_pct: 67.52,
      expectancy_net_pct: 2.683,
      applied_learnings_count: 12,
    },
    front_overview: {
      b3: { total_tested: 900, success_rate_pct: 64.1, updated_at: "2026-05-03T09:00:00Z" },
      crypto: { total_tested: 503, success_rate_pct: 70.4, updated_at: "2026-05-03T09:15:00Z" },
      real_estate: { total_tested: 324, success_rate_pct: 68.2, updated_at: "2026-05-03T09:30:00Z" },
    },
    learning_notes: [
      {
        pain: "Entradas sem confirmação de volume aumentaram falsos rompimentos.",
        remedy: "Exigir volume acima da média antes de promover a tese para go-live.",
        expected_impact: "Reduzir entradas frágeis nas próximas validações de B3 e cripto.",
        applied_to: ["PETR4", "BTCUSDT"],
        evidence_count: 7,
      },
    ],
    thesis_open_operations: [
      {
        phase: "analysis",
        thesis_number: 301,
        thesis_id: "IM-001",
        thesis_raised_at: "2026-04-30T12:00:00Z",
        action: "Galpão logístico Campinas",
        front: "real_estate",
        direction: "bullish",
        thesis_reason: "Vacância baixa e reajuste contratual sustentam prêmio de risco.",
        expected_result_pct: 7.06,
        moment_result_pct: 0,
        entry_price_brl: 850000,
        current_price_brl: 850000,
        target_price_brl: 910000,
        stop_price_brl: 820000,
        operation_plan: "Análise para aquisição com margem de segurança.",
        structured_operation: "Tese imobiliária com margem de segurança",
        exit_rule: "Alvo R$ 910K · piso R$ 820K",
        status: "Observando",
        outcome: "Observando",
        learning_note: "Comparar prazo de maturação com liquidez esperada do ativo.",
      },
    ],
  },
  currentMonitor: {
    theses: [
      {
        id: "B3-001",
        instrument: "PETR4",
        direction: "Alta",
        hypothesis: "Rompimento com volume crescente pode sustentar nova perna de alta.",
        evidence: ["Volume confirmou o movimento", "Fluxo comprador segue resiliente"],
        entry_price: 38.2,
        current_price: 39.1,
        target_price: 42.4,
        stop_price: 36.8,
        expected_pct: 10.99,
        current_pct: 2.36,
        thesis_raised_at: "2026-04-29T12:00:00Z",
        status: "monitoring",
        learning: "Esperar confirmação de volume antes de aumentar exposição.",
        jane_state: "tracking",
        jane_message: "Patrick Jane acompanha a força do rompimento.",
        operation: "Compra tática em PETR4 com alvo e stop definidos.",
        invalidation: "Perde força se fechar abaixo do suporte com volume alto.",
      },
      {
        id: "CR-001",
        instrument: "BTCUSDT",
        direction: "Alta",
        hypothesis: "Compressão de volatilidade pode liberar movimento direcional.",
        evidence: ["Amplitude estreita", "Livro absorvendo vendas"],
        entry_price: 62400,
        current_price: 63800,
        target_price: 67000,
        stop_price: 60400,
        thesis_raised_at: "2026-05-01T12:00:00Z",
        status: "target_hit",
        learning: "Calibrar alvo parcial quando a volatilidade realizada dispara.",
        operation: "Compra em BTCUSDT com alvo parcial.",
        invalidation: "Perde validade se romper a mínima da compressão.",
      },
    ],
  },
  realEstateCandidates: {
    candidates: [
      {
        id: "IM-001",
        name: "Galpão logístico Campinas",
        status: "analysis",
        candidate_date: "2026-04-30T12:00:00Z",
        hypothesis: "Vacância baixa e reajuste contratual sustentam prêmio de risco.",
        evidence: ["Contrato atípico", "Cap rate acima do par"],
        entry_price: 850000,
        current_price: 850000,
        target_price: 910000,
        stop_price: 820000,
        expected_pct: 7.06,
        learning: "Comparar prazo de maturação com liquidez esperada do ativo.",
        operation: "Análise para aquisição com margem de segurança.",
        invalidation: "Descartar se diligência revelar vacância oculta.",
      },
    ],
  },
  realEstateStrategyTerritoryCandidates: {
    generated_at: "2026-05-08T02:32:50Z",
    summary: {
      strategy_count: 8,
      territory_count: 12,
      matrix_brief_count: 96,
      source_candidate_count: 16,
      source_confirmed_requalification_count: 4,
    },
    matrix_briefs: [
      {
        brief_id: "IM-BUSCA-centro-condominio",
        trust_level: "hypothesis",
        strategy_id: "condominio_antigo_requalificacao",
        strategy_label: "Condominio antigo em requalificacao",
        territory_label: "Centro / Republica / Bela Vista",
        title: "BUSCA - Condominio antigo em requalificacao - Centro",
        decision_rule: "Nao virar tese de compra ate existir unidade, preco e comparaveis.",
      },
    ],
    strategy_candidate_watchlist: [
      {
        brief_id: "IM-FONTE-vivareal-wish-675",
        brief_type: "strategy_source_candidate",
        trust_level: "source_listed",
        strategy_id: "lancamentos_ciclo_entrega",
        strategy_label: "Lancamentos / ciclo de entrega",
        territory_label: "Agua Funda / Jabaquara / Saude",
        title: "VivaReal - WISH 675 / Vila Monte Alegre",
        source_name: "VivaReal Lancamentos",
        source_url: "https://www.vivareal.com.br/imoveis-lancamentos/wish-675-id-2876400406/",
        source_summary: "Pagina de lancamento usada para acompanhar preco, entrega, estoque e risco de prazo.",
        candidate_angle: "Validar prazo e preco contra usado reformado.",
      },
    ],
    condominium_requalification_watchlist: [
      {
        brief_id: "IM-SINAL-lotus",
        trust_level: "source_confirmed",
        strategy_id: "condominio_antigo_requalificacao",
        strategy_label: "Condominio antigo em requalificacao",
        territory_label: "Centro / Republica / Bela Vista",
        title: "Cond Edif Lotus - Bela Vista",
        source_name: "Lello Imoveis",
        source_summary: "Pagina de condominio descreve predio com fachada reformada.",
      },
    ],
  },
};

describe("cockpitHalleyAdapter", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps backend status values to UI badges", () => {
    expect(statusToUi("monitoring")).toEqual({ label: "Observando", badge: "info" });
    expect(statusToUi("target_hit")).toEqual({ label: "Validada", badge: "success" });
    expect(statusToUi("stop_alert")).toEqual({ label: "Alerta", badge: "warning" });
  });

  it("normalizes B3, crypto and real estate feeds for the cockpit", () => {
    const result = normalizeCockpitHalley(fixturePayloads, now);

    expect(result.scientificSummary.testedTheses).toBe(1727);
    expect(result.scientificSummary.goLiveCount).toBe(3);
    expect(result.fronts.map((front) => front.id)).toEqual(["b3", "crypto", "real_estate"]);
    expect(result.fronts.find((front) => front.id === "b3").goLive).toBe(1);
    expect(result.fronts.find((front) => front.id === "crypto").goLive).toBe(1);
    expect(result.fronts.find((front) => front.id === "real_estate").goLive).toBe(1);
    expect(result.goLiveTheses[0].daysOpen).toBe(4);
    expect(result.learningLoops.length).toBeGreaterThan(0);
  });

  it("derives front summaries and directional prices when front_overview and explicit target fields are missing", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          updated_at: "2026-05-09T01:42:52Z",
          thesis_history_overview: {
            total_tested: 2,
            success_rate_pct: 50,
            expectancy_net_pct: 2.4,
          },
          historical_analysis_summary: {
            thesis_count: 2,
          },
          thesis_open_operations: [
            {
              thesis_number: 1,
              thesis_id: "TH-PETR4-bullish-0001",
              action: "PETR4",
              is_open: false,
              status: "Fechada",
              expected_result_pct: 2.2,
              moment_result_pct: 3.1,
              operation_plan: "Compra ate - legado sem preco persistido",
            },
            {
              thesis_number: 2,
              thesis_id: "TH-GGBR4-bullish-0104",
              action: "GGBR4",
              is_open: true,
              status: "Aberta - Atencao",
              expected_result_pct: 2.6109,
              moment_result_pct: 0,
              entry_price_brl: 23.77,
              current_price_brl: 23.77,
              operation_plan: "Compra até 2026-05-19. Plano: buscar alta de 23.77 para perto de 25.43. Se cair para 22.77, encerramos para proteger a posição. Retorno esperado: 2.61%.",
              structured_operation: "Bull Call Spread | ganho max 5.40% | perda max 2.20%",
            },
          ],
        },
      },
      now,
    );

    const b3Front = result.fronts.find((front) => front.id === "b3");
    const thesis = result.goLiveTheses.find((item) => item.asset === "GGBR4");

    expect(b3Front.tested).toBe(2);
    expect(b3Front.validatedPct).toBeGreaterThan(0);
    expect(thesis.targetPrice).toBe(25.43);
    expect(thesis.stopPrice).toBe(22.77);
  });

  it("sorts calibration cycles chronologically before exposing method evolution", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_history_overview: {
            success_rate_pct: 67.52,
          },
          calibration_cycles: [
            { ciclo: "Cal.18", success_rate_pct: 67.52 },
            { ciclo: "Cal.17", success_rate_pct: 66.3 },
            { ciclo: "Cal.16", success_rate_pct: 65.4 },
            { ciclo: "Cal.15", success_rate_pct: 64.2 },
            { ciclo: "Cal.14", success_rate_pct: 62.9 },
            { ciclo: "Cal.13", success_rate_pct: 61.7 },
            { ciclo: "Cal.12", success_rate_pct: 60.3 },
            { ciclo: "Cal.11", success_rate_pct: 59.1 },
            { ciclo: "Cal.10", success_rate_pct: 57.8 },
            { ciclo: "Cal.09", success_rate_pct: 56.4 },
            { ciclo: "Cal.08", success_rate_pct: 55 },
          ],
        },
      },
      now,
    );

    expect(result.backtest.accuracyCycles.map((item) => item.ciclo)).toEqual([
      "Cal.08",
      "Cal.09",
      "Cal.10",
      "Cal.11",
      "Cal.12",
      "Cal.13",
      "Cal.14",
      "Cal.15",
      "Cal.16",
      "Cal.17",
      "Cal.18",
    ]);
    expect(result.backtest.accuracyCycles[0].taxa).toBe(55);
    expect(result.backtest.accuracyCycles.at(-1).taxa).toBe(67.52);
  });

  it("marks method evolution cycles as synthetic when the backend has no calibration history", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_history_overview: {
            total_tested: 2543,
            success_count: 1167,
            success_rate_pct: 45.89,
            last_3_weeks: [
              { label: "Semana 1", total_tested: 9, success_count: 8, avg_result_pct: 3.83 },
              { label: "Semana 2", total_tested: 144, success_count: 135, avg_result_pct: 3.01 },
              { label: "Semana 3", total_tested: 2390, success_count: 1024, avg_result_pct: 1.87 },
            ],
          },
        },
      },
      now,
    );

    expect(result.backtest.accuracyCycleSource).toBe("synthetic");
    expect(result.backtest.accuracyCycles.at(-1).taxa).toBe(45.89);
  });

  it("uses thesis_open_operations as the canonical source for real estate open theses", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_open_operations: [
            {
              phase: "analysis",
              thesis_number: 301,
              thesis_id: "IM-301",
              thesis_raised_at: "2026-05-01T12:00:00Z",
              action: "Galpão logístico Jundiaí",
              direction: "bullish",
              thesis_reason: "Vacância baixa e preço abaixo dos comparáveis sustentam a hipótese imobiliária.",
              expected_result_pct: 8.5,
              moment_result_pct: 1.42,
              entry_price_brl: 700000,
              current_price_brl: 710000,
              target_price_brl: 770000,
              stop_price_brl: 650000,
              operation_plan: "Análise imobiliária com margem de segurança e diligência documental.",
              structured_operation: "Imóvel com alvo, piso e gatilhos de diligência.",
              exit_rule: "Alvo R$ 770K · piso R$ 650K",
              status: "Observando",
              outcome: "Observando",
              learning_note: "Registrar prazo de maturação e liquidez antes do go-live financeiro.",
            },
          ],
        },
        currentMonitor: {
          theses: [
            {
              id: "B3-001",
              instrument: "PETR4",
              direction: "Alta",
              entry_price: 38.2,
              current_price: 39.1,
              target_price: 42.4,
              stop_price: 36.8,
              thesis_raised_at: "2026-04-29T12:00:00Z",
              status: "monitoring",
            },
          ],
        },
        realEstateCandidates: {
          candidates: [
            {
              id: "IM-CAND",
              name: "Candidato apenas radar",
              status: "analysis",
              candidate_date: "2026-04-30T12:00:00Z",
              entry_price: 500000,
              target_price: 560000,
            },
          ],
        },
      },
      now,
    );

    expect(result.goLiveTheses.map((thesis) => thesis.asset)).toContain("Galpão logístico Jundiaí");
    expect(result.goLiveTheses.map((thesis) => thesis.asset)).not.toContain("Candidato apenas radar");
    const realEstateThesis = result.activeTheses.find((thesis) => thesis.asset === "Galpão logístico Jundiaí");
    expect(realEstateThesis).toMatchObject({
      front: "Imóveis",
      status: "analysis",
      currentPrice: 710000,
      expectedPct: 8.5,
      currentPct: 1.42,
    });
    expect(result.thesisRows.find((row) => row.asset === "Galpão logístico Jundiaí").statusGroup).toBe("Em análise");
  });

  it("treats closed real estate theses as estimates, not realized performance", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_open_operations: [
            {
              thesis_number: 1880,
              thesis_id: "IM-1880",
              action: "REAL - Caixa Tatuapé",
              front: "imoveis",
              status: "Fechada",
              is_open: false,
              expected_result_pct: -15.9,
              moment_result_pct: 48.97,
              entry_price_brl: 142000,
              current_price_brl: 211000,
              operation_plan: "Leilão/venda online com pendências abertas.",
              structured_operation: "Radar imobiliário",
              exit_rule: "Confirmar ocupação antes de reabrir.",
              learning_note: "Candidato descartado pelo radar.",
            },
          ],
        },
      },
      now,
    );

    const thesis = result.thesisRows[0];

    expect(thesis).toMatchObject({
      front: "Imóveis",
      direction: "Descartada",
      statusGroup: "Histórica",
      isOpen: false,
      resultKind: "estimate",
      expectedPct: -15.9,
      resultPct: -15.9,
    });
  });

  it("preserves real estate analysis details and source URL from thesis_open_operations", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_open_operations: [
            {
              thesis_number: 1888,
              thesis_id: "IM-RADAR-3",
              action: "REAL - VivaReal Colonia",
              front: "imoveis",
              source_url: "https://example.com/imovel",
              status: "Fechada",
              outcome: "Descartado pelo radar",
              is_open: false,
              expected_result_pct: -31.92,
              moment_result_pct: -31.92,
              entry_price_brl: 215000,
              current_price_brl: 240000,
              real_estate_analysis: {
                score: 63,
                confidence: 51,
                suggested_status: "Descartado",
                next_action: "Rever preco maximo ou descartar",
                price_ceiling_status: "Acima do teto",
                max_purchase_price: 160400,
                pending_items: [{ priority: "P0", title: "Confirmar ocupacao", action: "Validar fonte oficial." }],
              },
            },
          ],
        },
      },
      now,
    );

    expect(result.thesisRows[0]).toMatchObject({
      sourceUrl: "https://example.com/imovel",
      realEstateAnalysis: {
        score: 63,
        confidence: 51,
        suggested_status: "Descartado",
        next_action: "Rever preco maximo ou descartar",
        price_ceiling_status: "Acima do teto",
        max_purchase_price: 160400,
      },
    });
  });

  it("normalizes the real current monitor thesis shape", () => {
    const result = normalizeCockpitHalley(
      {
        currentMonitor: {
          theses: [
            {
              thesis_id: "TH-PETR4-bullish-0162",
              instrument: "PETR4",
              direction: "bullish",
              why_thesis: ["momento bullish", "volume confirmou"],
              reason_category: "grafico/tecnico + fundamentalista",
              thesis_raised_at: "2026-04-29T12:00:00Z",
              entry_price: 40.12,
              latest_price: 41.3,
              target_price: 43.5,
              stop_price: 38.9,
              monitor_status: "stop_alert",
              expected_financial_pct: 4.82,
              unrealized_financial_pct: -1.23,
              suggested_operation: {
                strategy_id: "BULL_CALL_SPREAD",
                strategy_name: "Bull Call Spread",
                rationale: "Estrutura alinhada ao cenário bullish com risco definido.",
              },
              revaluation_reason: "O padrão perdeu força perto do stop.",
              next_trigger: "Sai abaixo de R$ 38,90.",
              learning_signal: "Exigir confirmação adicional de volume.",
            },
          ],
        },
      },
      now,
    );

    const thesis = result.goLiveTheses[0];

    expect(thesis.currentPrice).toBe(41.3);
    expect(thesis.status).toBe("stop_alert");
    expect(thesis.expectedPct).toBe(4.82);
    expect(thesis.currentPct).toBe(-1.23);
    expect(thesis.evidence).toEqual(["momento bullish", "volume confirmou"]);
    expect(thesis.hypothesis).toContain("grafico/tecnico + fundamentalista");
    expect(thesis.operation).toContain("Bull Call Spread");
    expect(thesis.operation).toContain("Estrutura alinhada ao cenário bullish");
    expect(thesis.invalidation).toContain("Sai abaixo");
    expect(thesis.learning).toContain("Exigir confirmação");
    expect(thesis.janeMessage).toContain("O padrão perdeu força");
  });

  it("marks repeated crypto range plans as plans over fewer covered assets", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_history_overview: {
            total_tested: 879,
            success_rate_pct: 76.34,
            expectancy_net_pct: 3.01,
          },
        },
        currentMonitor: {
          theses: [
            {
              thesis_id: "TH-ETHUSDT-range-0001",
              instrument: "ETHUSDT",
              direction: "range",
              entry_price: 2361.92,
              latest_price: 2369.53,
              target_price: 2361.92,
              stop_price: 2326.49,
              range_lower_price: 2326.49,
              range_upper_price: 2397.35,
              thesis_raised_at: "2026-05-05T22:45:00Z",
              monitor_status: "stop_alert",
            },
            {
              thesis_id: "TH-ETHUSDT-range-0002",
              instrument: "ETHUSDT",
              direction: "range",
              entry_price: 2369.53,
              latest_price: 2369.53,
              target_price: 2369.53,
              stop_price: 2333.99,
              thesis_raised_at: "2026-05-05T23:15:00Z",
              monitor_status: "monitoring",
            },
            {
              thesis_id: "TH-BTCUSDT-range-0001",
              instrument: "BTCUSDT",
              direction: "range",
              entry_price: 81212.04,
              latest_price: 81212.04,
              target_price: 81212.04,
              stop_price: 79993.86,
              thesis_raised_at: "2026-05-05T23:15:00Z",
              monitor_status: "monitoring",
            },
          ],
        },
      },
      new Date("2026-05-06T16:15:00Z"),
    );

    const cryptoFront = result.fronts.find((front) => front.id === "crypto");

    expect(result.scientificSummary.goLiveCount).toBe(3);
    expect(result.scientificSummary.goLiveAssetCount).toBe(2);
    expect(result.scientificSummary.learningCountLabel).toBe("lições recentes");
    expect(cryptoFront.goLive).toBe(3);
    expect(cryptoFront.activeAssets).toBe(2);
    expect(cryptoFront.tested).toBe(3);
    expect(cryptoFront.validatedPct).toBe(76.34);
    expect(result.goLiveTheses[0]).toMatchObject({
      direction: "Neutra",
      hoursOpen: 17,
      priceReferenceLabel: "Faixa",
      rangeLowerPrice: 2326.49,
      rangeUpperPrice: 2397.35,
    });
  });

  it("marks a stale reused current monitor as frozen study data", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          thesis_history_overview: {
            total_tested: 879,
            success_rate_pct: 76.34,
            expectancy_net_pct: 3.01,
          },
        },
        currentMonitor: {
          data_quality: {
            status: "stale_reused",
            reason: "no_fresh_market_data",
            generated_at: "2026-05-05T23:17:17Z",
            reused_at: "2026-05-06T12:00:00Z",
          },
          theses: [
            {
              thesis_id: "TH-ETHUSDT-range-0001",
              instrument: "ETHUSDT",
              direction: "range",
              entry_price: 2361.92,
              latest_price: 2369.53,
              target_price: 2361.92,
              stop_price: 2326.49,
              thesis_raised_at: "2026-05-05T22:45:00Z",
              monitor_status: "monitoring",
            },
          ],
        },
      },
      new Date("2026-05-06T16:15:00Z"),
    );

    expect(result.monitorTrust).toMatchObject({
      status: "stale_reused",
      reason: "no_fresh_market_data",
      isFrozen: true,
      label: "Monitor congelado",
    });
    expect(result.scientificSummary.monitorFrozen).toBe(true);
    expect(result.scientificSummary.goLiveLabel).toBe("planos no último monitor");
    expect(result.scientificSummary.goLiveKpiLabel).toBe("Último monitor");
  });

  it("exposes data coverage without treating missing confirmation sources as neutral evidence", () => {
    const result = normalizeCockpitHalley(
      {
        currentMonitor: {
          generated_at: "2026-05-07T00:50:13Z",
          scan_scope: {
            fresh_instruments: ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            tick_count: 7774,
          },
          theses: [
            {
              thesis_id: "TH-BTCUSDT-range-0007",
              instrument: "BTCUSDT",
              direction: "range",
              entry_price: 81222.99,
              latest_price: 81222.99,
              target_price: 81222.99,
              stop_price: 80004.6452,
              thesis_raised_at: "2026-05-07T00:30:00Z",
              monitor_status: "monitoring",
              fundamental_available: false,
              news_available: false,
              geo_oil_available: false,
              fundamental_support_pct: 50,
              news_support_pct: 50,
            },
          ],
        },
      },
      new Date("2026-05-07T00:55:00Z"),
    );

    expect(result.coverage.market).toMatchObject({ status: "fresh", label: "Mercado atualizado" });
    expect(result.coverage.history).toMatchObject({ status: "fresh", label: "Historico disponivel" });
    expect(result.coverage.news).toMatchObject({ status: "missing", label: "Noticias sem cobertura recente" });
    expect(result.coverage.fundamentals).toMatchObject({ status: "not_applicable", label: "Fundamentos nao aplicaveis para cripto" });
    expect(result.coverage.macro).toMatchObject({ status: "disabled", label: "Macro fora do MVP atual" });
    expect(result.goLiveTheses[0].coverageNotes).toEqual(expect.arrayContaining([
      "Tese tecnica com mercado fresco.",
      "Faltam noticias recentes para confirmar contexto.",
      "Fundamentos nao se aplicam a este par cripto.",
      "Confianca reduzida por lacunas de confirmacao.",
    ]));
  });

  it("summarizes operational freshness from ops health, coverage and official thesis arrays", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          ops_health: {
            status: "ok",
            generated_at: "2026-05-08T10:00:00Z",
            stages: {
              market_feed: {
                status: "ok",
                fronts: {
                  b3: { age_days: 0.2, max_age_days: 4, latest_event_time: "2026-05-08T09:00:00Z" },
                  crypto: { age_days: 0.01, max_age_days: 1, latest_event_time: "2026-05-08T09:45:00Z" },
                },
              },
            },
          },
          thesis_history_overview: { total_tested: 879, success_rate_pct: 76.34 },
          thesis_open_operations: [
            {
              thesis_id: "IM-100",
              thesis_number: 100,
              front: "imoveis",
              action: "Apto Vila Mariana",
              status: "Observando",
              is_open: true,
              expected_result_pct: 8.4,
              real_estate_analysis: { score: 63, confidence: 51 },
            },
          ],
        },
        currentMonitor: {
          scan_scope: { fresh_instruments: ["PETR4", "BTCUSDT"], tick_count: 200 },
          theses: [
            {
              thesis_id: "TH-PETR4-bullish-0001",
              instrument: "PETR4",
              direction: "bullish",
              thesis_raised_at: "2026-05-08T09:30:00Z",
              monitor_status: "monitoring",
              news_available: true,
              fundamental_available: true,
            },
          ],
        },
      },
      new Date("2026-05-08T10:00:00Z"),
    );

    expect(result.operationalFreshness).toMatchObject({
      status: "online",
      label: "Online",
      badge: "open",
    });
    expect(result.operationalFreshness.sources.map((source) => source.key)).toEqual([
      "b3",
      "crypto",
      "imoveis",
      "historico",
      "noticias",
      "fundamentos",
      "macro",
    ]);
    expect(result.operationalFreshness.sources.find((source) => source.key === "b3")).toMatchObject({
      status: "online",
      label: "B3",
    });
    expect(result.operationalFreshness.sources.find((source) => source.key === "imoveis")).toMatchObject({
      status: "online",
      detail: "1 tese imobiliaria oficial",
    });
  });

  it("marks freshness as stale when ops health blocks the operational cycle", () => {
    const result = normalizeCockpitHalley(
      {
        dashboardSummary: {
          ops_health: {
            status: "blocked",
            message: "Feed de mercado stale.",
            recommended_actions: ["Atualizar feed B3/Cripto."],
            stages: {
              market_feed: {
                status: "blocked",
                stale_fronts: ["b3", "crypto"],
                fronts: {
                  b3: { age_days: 8, max_age_days: 4 },
                  crypto: { age_days: 2, max_age_days: 1 },
                },
              },
            },
          },
          thesis_history_overview: { total_tested: 879 },
        },
      },
      new Date("2026-05-08T10:00:00Z"),
    );

    expect(result.operationalFreshness).toMatchObject({
      status: "stale",
      label: "Desatualizado",
      badge: "warning",
      action: "Atualizar feed B3/Cripto.",
    });
    expect(result.operationalFreshness.sources.find((source) => source.key === "b3")).toMatchObject({
      status: "stale",
    });
  });

  it("returns partial API payloads when one feed fails", async () => {
    const fetchMock = vi.fn((url) => {
      if (url === "/api/dashboard/summary/1") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ dashboard: true }) });
      }
      if (url === "/api/theses/current-monitor/latest") {
        return Promise.resolve({ ok: false, status: 503, statusText: "Service Unavailable" });
      }
      if (url === "/api/real-estate/strategy-territory-candidates") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ matrix_briefs: [{ brief_id: "IM-BUSCA-1" }] }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ candidates: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchCockpitPayloads();

    expect(result.dashboardSummary).toEqual({ dashboard: true });
    expect(result.currentMonitor).toBeNull();
    expect(result.realEstateCandidates).toEqual({ candidates: [] });
    expect(result.realEstateStrategyTerritoryCandidates).toEqual({ matrix_briefs: [{ brief_id: "IM-BUSCA-1" }] });
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].feed).toBe("currentMonitor");
  });

  it("keeps strategy-territory real estate briefs separate from registered candidates", () => {
    const result = normalizeCockpitHalley(fixturePayloads, now);

    expect(result.realEstateStrategyTerritoryCandidates).toMatchObject({
      summary: {
        strategyCount: 8,
        territoryCount: 12,
        matrixBriefCount: 96,
        sourceCandidateCount: 16,
        sourceConfirmedRequalificationCount: 4,
      },
      matrixBriefs: [
        expect.objectContaining({
          id: "IM-BUSCA-centro-condominio",
          trustLevel: "hypothesis",
          strategyId: "condominio_antigo_requalificacao",
        }),
      ],
      strategyCandidateWatchlist: [
        expect.objectContaining({
          id: "IM-FONTE-vivareal-wish-675",
          trustLevel: "source_listed",
          strategyId: "lancamentos_ciclo_entrega",
          sourceName: "VivaReal Lancamentos",
        }),
      ],
      condominiumRequalificationWatchlist: [
        expect.objectContaining({
          id: "IM-SINAL-lotus",
          trustLevel: "source_confirmed",
          sourceName: "Lello Imoveis",
        }),
      ],
    });
    expect(result.thesisRows.map((row) => row.thesisId)).not.toContain("IM-BUSCA-centro-condominio");
  });

  it("ships a complete mock fallback seed", () => {
    const result = normalizeCockpitHalley(mockCockpitHalleyPayloads, now);

    expect(result.fronts.map((front) => front.id)).toEqual(["b3", "crypto", "real_estate"]);
    expect(result.goLiveTheses.map((thesis) => thesis.asset)).toEqual(expect.arrayContaining(["PETR4", "BTCUSDT", "Galpão logístico Campinas"]));
    expect(result.goLiveTheses.filter((thesis) => thesis.front === "Imóveis").length).toBeGreaterThanOrEqual(8);
    expect(result.learningLoops.length).toBeGreaterThanOrEqual(3);
  });

  it("ships enough real estate mock candidates to exercise cockpit strategy and territory flows", () => {
    const result = normalizeCockpitHalley(mockCockpitHalleyPayloads, now);
    const realEstateRows = result.thesisRows.filter((row) => row.front === "Imóveis");
    const searchable = realEstateRows.map((row) => [row.asset, row.structure, row.hypothesis, row.learning].join(" ")).join(" ");

    expect(realEstateRows.length).toBeGreaterThanOrEqual(8);
    expect(searchable).toMatch(/Caixa|leilão/i);
    expect(searchable).toMatch(/House Flipping|reforma/i);
    expect(searchable).toMatch(/Compra Direta|QuintoAndar|VivaReal|Zap/i);
    expect(searchable).toMatch(/Renda|Plano B|aluguel/i);
    expect(searchable).toMatch(/Lançamento|planta/i);
    expect(searchable).toMatch(/Pinheiros/i);
    expect(searchable).toMatch(/Perdizes|Pompéia/i);
    expect(searchable).toMatch(/Vila Mariana/i);
  });
});
