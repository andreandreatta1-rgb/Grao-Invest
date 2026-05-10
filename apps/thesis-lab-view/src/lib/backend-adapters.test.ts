import { describe, expect, it } from "vitest";
import type { SpecificImovel, SpecificMicrotrade, TheseEnvelope } from "@/types/domain";
import {
  adaptCockpitFromData,
  adaptCurrentMonitorTheses,
  adaptDataHealthFromCurrentMonitor,
  adaptMicrotradesAutopilotLatest,
  adaptRealEstateCandidates,
  type BackendCurrentMonitorPayload,
  type BackendMicrotradesAutopilotLatestPayload,
  type BackendRealEstateCandidatesResponse,
} from "./backend-adapters";

describe("backend adapters", () => {
  it("maps closed crypto monitor snapshots to microtrade envelopes", () => {
    const payload: BackendCurrentMonitorPayload = {
      theses: [
        {
          thesis_id: "TH-BTCUSDT-range-1",
          instrument: "BTCUSDT",
          direction: "range",
          thesis_raised_at: "2000-01-01T00:00:00Z",
          suggested_entry_time: "2000-01-01T00:00:00Z",
          suggested_exit_time: "2000-01-01T00:40:00Z",
          entry_price: 100,
          target_price: 102,
          stop_price: 98,
          latest_price: 101,
          latest_event_time: "2000-01-01T00:40:00Z",
          monitor_status: "monitoring",
          expected_financial_pct: 0.8,
          unrealized_financial_pct: 0.4,
          confidence_tese_pct: 70,
          confidence_now_pct: 65,
          support_rate_pct: 80,
          technical_support_pct: 75,
          monitoring_events: [{ event_type: "exit_snapshot" }],
          asset_front: "cripto",
        },
      ],
    };

    const [thesis] = adaptCurrentMonitorTheses(payload);
    const specific = thesis.specific as SpecificMicrotrade;

    expect(thesis.front).toBe("cripto");
    expect(thesis.status).toBe("encerrada_tempo");
    expect(thesis.closed_at).toBeTruthy();
    expect(thesis.asset_label).toBe("Bitcoin (BTC)");
    expect(specific.kind).toBe("microtrade");
    expect(specific.window_min).toBe(40);
  });

  it("maps real estate radar candidates to dossiers with completion", () => {
    const payload: BackendRealEstateCandidatesResponse = {
      items: [
        {
          id: 42,
          title: "REAL - Tatuape teste",
          city: "Sao Paulo",
          neighborhood: "Tatuape",
          property_type: "Apartamento",
          asking_price: 100000,
          market_value_estimate: 130000,
          estimated_sale_base: 140000,
          accepts_financing: true,
          financing_validated: false,
          occupancy_status: "desconhecido",
          has_registration: false,
          has_edital: true,
          condo_debt_known: false,
          iptu_debt_known: true,
          renovation_budget: 5000,
          carrying_months: 6,
          monthly_carrying_cost: 800,
          sale_comparables_count: 1,
          rent_comparables_count: 0,
          plan_a: "Visitar e validar custos",
          plan_b: "Se a tese piorar, descartar",
          created_at: "2026-05-04T00:00:00Z",
          updated_at: "2026-05-04T12:00:00Z",
          status: "Aberto com pendencias",
          analysis: {
            score: 82,
            confidence: 39,
            next_action: "Confirmar ocupacao",
            pending_items: [{ title: "Confirmar ocupacao" }],
            scenarios: {
              base: { sale_price: 140000, roi_pct: 18 },
            },
            max_purchase_price: 95000,
            price_ceiling_status: "Dentro do teto",
            base_profit_pct: 12.3,
          },
        },
      ],
    };

    const [thesis] = adaptRealEstateCandidates(payload);
    const specific = thesis.specific as SpecificImovel;

    expect(thesis.front).toBe("imoveis");
    expect(thesis.status).toBe("confirmando");
    expect(thesis.target_value).toBe(140000);
    expect(thesis.completion.pending_items).toContain("Confirmar ocupacao");
    expect(specific.kind).toBe("imovel");
    expect(specific.imovel_status).toBe("diligencia");
    expect(specific.ceiling_price).toBe(95000);
  });

  it("builds cockpit metrics from adapted theses", () => {
    const theses = adaptRealEstateCandidates({
      items: [
        {
          id: 7,
          title: "REAL - Radar aberto",
          city: "Sao Paulo",
          neighborhood: "Mooca",
          property_type: "Apartamento",
          asking_price: 120000,
          market_value_estimate: 150000,
          created_at: "2026-05-04T00:00:00Z",
          updated_at: "2026-05-04T12:00:00Z",
          status: "Aberto com pendencias",
          analysis: {
            score: 78,
            confidence: 70,
            next_action: "Revisar docs",
            scenarios: { base: { sale_price: 160000, roi_pct: 15 } },
            max_purchase_price: 118000,
          },
        },
        {
          id: 8,
          title: "REAL - Radar descartado",
          city: "Sao Paulo",
          neighborhood: "Bras",
          property_type: "Studio",
          asking_price: 90000,
          market_value_estimate: 95000,
          created_at: "2026-05-01T00:00:00Z",
          updated_at: "2026-05-02T12:00:00Z",
          status: "Descartado",
          analysis: {
            score: 30,
            confidence: 30,
            next_action: "Descartar",
            scenarios: { base: { sale_price: 94000, roi_pct: -2 } },
            max_purchase_price: 85000,
          },
        },
      ],
    });

    const cockpit = adaptCockpitFromData(
      {
        thesis_history_overview: {
          total_tested: 120,
          success_rate_pct: 62,
          expectancy_net_pct: 2.4,
          event_count: 18,
        },
      },
      theses,
    );

    expect(cockpit.tesesTestadas).toBe(120);
    expect(cockpit.tesesAtivas).toBe(1);
    expect(cockpit.validacaoHistoricaPct).toBe(0.62);
    expect(cockpit.frentes.Imoveis.ativas).toBe(1);
  });

  it("adapts the latest autopilot cycle for the lab header", () => {
    const payload: BackendMicrotradesAutopilotLatestPayload = {
      status: "partial",
      error: "Token Finnhub ausente. Etapa live ignorada.",
      run_started_at: "2026-05-04T10:00:00Z",
      run_finished_at: "2026-05-04T10:00:12Z",
      config: {
        interval: "5m",
        instruments: ["BTCUSDT", "ETHUSDT"],
      },
      steps: [
        { title: "historico", status: "ok", meta: "100 candles processados." },
        { title: "cotacao", status: "warning", meta: "Token Finnhub ausente. Etapa live ignorada." },
      ],
      monitor: {
        thesis_count: 2,
        summary: {
          monitoring_count: 2,
          needs_attention_count: 1,
        },
      },
      decision: {
        status: "created",
        decision_id: "dec-42",
      },
      worker: {
        worker_name: "microtrades_autopilot_worker",
        status: "idle",
        last_run_at: "2026-05-04T10:00:12Z",
        next_run_at: "2026-05-04T10:30:12Z",
        cycles_today: 3,
      },
      runtime: {
        running: true,
      },
    };

    const cycle = adaptMicrotradesAutopilotLatest(payload);

    expect(cycle).toBeTruthy();
    expect(cycle?.cycleStatus).toBe("partial");
    expect(cycle?.isRunning).toBe(true);
    expect(cycle?.agentRunning).toBe(true);
    expect(cycle?.cycleLabel).toBe("Rodando");
    expect(cycle?.monitoringCount).toBe(2);
    expect(cycle?.needsAttentionCount).toBe(1);
    expect(cycle?.decisionStatus).toBe("created");
    expect(cycle?.stepCounts.warning).toBe(1);
    expect(cycle?.cyclesToday).toBe(3);
    expect(cycle?.statusDetail).toContain("Token Finnhub ausente");
  });

  it("uses the freshest autopilot activity and does not mark stale cycles as currently running", () => {
    const payload: BackendMicrotradesAutopilotLatestPayload = {
      status: "partial",
      error: "Token Finnhub ausente. Etapa live ignorada.",
      run_started_at: "2026-05-04T10:00:00Z",
      run_finished_at: "2026-05-04T10:00:12Z",
      config: {
        interval: "5m",
        instruments: ["BTCUSDT", "ETHUSDT"],
      },
      steps: [
        { title: "historico", status: "ok", meta: "100 candles processados." },
        { title: "cotacao", status: "warning", meta: "Token Finnhub ausente. Etapa live ignorada." },
      ],
      monitor: {
        thesis_count: 2,
        summary: {
          monitoring_count: 2,
          needs_attention_count: 1,
        },
      },
      decision: {
        status: "created",
        decision_id: "dec-42",
      },
      worker: {
        worker_name: "microtrades_autopilot_worker",
        status: "running",
        last_run_at: "2026-05-04T19:22:44Z",
        next_run_at: "2026-05-04T19:27:44Z",
        cycles_today: 18,
      },
      runtime: {
        running: false,
      },
    };

    const cycle = adaptMicrotradesAutopilotLatest(payload);

    expect(cycle).toBeTruthy();
    expect(cycle?.isRunning).toBe(false);
    expect(cycle?.agentRunning).toBe(true);
    expect(cycle?.lastActivityAt).toBe("2026-05-04T19:22:44.000Z");
    expect(cycle?.cycleLabel).toBe("Parcial");
    expect(cycle?.statusHeadline).toBe("Ultimo ciclo concluido com ressalvas");
  });

  it("extracts dedicated crypto radar candidates without mixing them into executive cards", () => {
    const payload: BackendMicrotradesAutopilotLatestPayload = {
      status: "success",
      run_finished_at: "2026-05-04T10:00:12Z",
      config: {
        interval: "5m",
        instruments: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
      },
      monitor: {
        thesis_count: 2,
        summary: {
          monitoring_count: 2,
          needs_attention_count: 0,
        },
        scan_scope: {
          fronts: {
            cripto: {
              scanner_candidates: [
                {
                  thesis_id: "TH-ETHUSDT-RADAR-1",
                  instrument: "ETHUSDT",
                  direction: "bullish",
                  thesis_raised_at: "2026-05-04T09:55:00Z",
                  suggested_entry_time: "2026-05-04T09:55:00Z",
                  suggested_exit_time: "2026-05-04T10:25:00Z",
                  entry_price: 3200,
                  target_price: 3264,
                  stop_price: 3174,
                  latest_price: 3211,
                  latest_event_time: "2026-05-04T10:00:00Z",
                  monitor_status: "monitoring",
                  suggested_action: "confirmar_entrada",
                  expected_financial_pct: 2,
                  unrealized_financial_pct: 0.3,
                  confidence_tese_pct: 76,
                  confidence_now_pct: 74,
                  support_rate_pct: 71,
                  technical_support_pct: 73,
                  fundamental_support_pct: 58,
                  news_support_pct: 54,
                  geo_oil_support_pct: 50,
                  fundamental_available: true,
                  news_available: true,
                  geo_oil_available: false,
                  progress_to_target_pct: 18,
                  distance_to_stop_pct: 0.8,
                  executive_status: "mantida",
                  executive_status_label: "Radar amplo",
                  executive_action: "confirmar_entrada",
                  thesis_validity: "valida",
                  revaluation_reason: "Radar amplo separado dos cards executivos",
                  next_trigger: "Rearmar entrada na confirmacao",
                  monitoring_events: [],
                  asset_front: "cripto",
                  front_label: "Cripto",
                },
              ],
            },
          },
        },
      },
    };

    const cycle = adaptMicrotradesAutopilotLatest(payload);

    expect(cycle?.statusDetail).toContain("Bitcoin (BTC)");
    expect(cycle?.radarCandidates).toHaveLength(1);
    expect(cycle?.radarCandidates[0]?.asset_label).toBe("Ethereum (ETH)");
    expect(cycle?.radarCandidates[0]?.id).toBe("TH-ETHUSDT-RADAR-1");
  });

  it("counts only lifecycle-open theses as active even when closed_at is missing", () => {
    const teses: TheseEnvelope[] = [
      {
        id: "b3-open",
        front: "b3",
        title: "Banco em monitoramento",
        asset_label: "ITUB4",
        hypothesis: "Seguir monitorando suporte",
        status: "monitorando",
        opened_at: "2026-05-04T10:00:00Z",
        updated_at: "2026-05-04T12:00:00Z",
        expected_result_pct: 2.4,
        current_result_pct: 0.8,
        confidence_pct: 74,
        entry_value: 30,
        current_value: 30.24,
        target_value: 30.72,
        stop_or_invalidation: "Perder suporte intraday",
        suggested_action: "Manter monitoramento",
        learning_note: "Fluxo institucional sustentado",
        data_quality: {
          freshness_status: "fresh",
          last_update_at: "2026-05-04T12:00:00Z",
          confidence_in_data_pct: 80,
        },
        specific: {},
        completion: {
          is_complete: true,
          completion_pct: 92,
          missing_fields: [],
          pending_items: [],
          next_required_action: "Continuar monitorando",
        },
      },
      {
        id: "b3-closed-status-only",
        front: "b3",
        title: "Petroleira validada",
        asset_label: "PETR4",
        hypothesis: "Alvo de curto prazo atingido",
        status: "validada",
        opened_at: "2026-05-03T10:00:00Z",
        updated_at: "2026-05-04T11:00:00Z",
        expected_result_pct: 3.2,
        current_result_pct: 3.1,
        confidence_pct: 88,
        entry_value: 35,
        current_value: 36.09,
        target_value: 36.12,
        stop_or_invalidation: "Perder rompimento",
        suggested_action: "Registrar aprendizado",
        learning_note: "Ganho confirmado",
        data_quality: {
          freshness_status: "fresh",
          last_update_at: "2026-05-04T11:00:00Z",
          confidence_in_data_pct: 84,
        },
        specific: {},
        completion: {
          is_complete: true,
          completion_pct: 96,
          missing_fields: [],
          pending_items: [],
          next_required_action: "Encerrar tese",
        },
      },
    ];

    const cockpit = adaptCockpitFromData(undefined, teses);

    expect(cockpit.tesesAtivas).toBe(1);
    expect(cockpit.frentes.B3.ativas).toBe(1);
  });

  it("explains when the latest monitor is a preserved stale fallback", () => {
    const health = adaptDataHealthFromCurrentMonitor({
      generated_at: "2026-05-05T20:00:00Z",
      thesis_count: 8,
      data_quality: {
        status: "stale_reused",
        source_generated_at: "2026-05-04T19:30:00Z",
        notes: ["Dados de mercado sem frescor; mantendo ultimo monitor valido."],
      },
      summary: {
        monitoring_count: 8,
        needs_attention_count: 1,
      },
      theses: [
        {
          thesis_id: "TH-BTCUSDT-LIVE-0001",
          instrument: "BTCUSDT",
          asset_front: "cripto",
          latest_event_time: "2026-05-04T19:20:00Z",
        },
      ],
    });

    expect(health.status).toBe("stale_reused");
    expect(health.saude).toBe("parcial");
    expect(health.fallbackActive).toBe(true);
    expect(health.headline).toContain("preservado");
    expect(health.thesisCount).toBe(8);
    expect(health.frontCounts.Cripto).toBe(1);
    expect(health.notes).toEqual(["Dados de mercado sem frescor; mantendo ultimo monitor valido."]);
  });
});
