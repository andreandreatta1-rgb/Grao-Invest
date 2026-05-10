import type {
  AtivoMercado,
  CockpitResumo,
  Completion,
  DataHealthSnapshot,
  Decisao,
  FonteDados,
  FreshnessStatus,
  Frente,
  FrenteApi,
  SpecificB3,
  SpecificImovel,
  SpecificMicrotrade,
  StatusTese,
  TheseEnvelope,
} from "@/types/domain";
import { isOpenThesis } from "@/types/domain";
import {
  cryptoAssetLabel,
  cryptoInstrumentFromText,
  cryptoSymbolFromText,
  formatCryptoScope,
} from "./crypto-display";

type BackendMonitorEvent = {
  event_time?: string;
  event_type?: string;
  severity?: string;
  message?: string;
  market_price?: number;
};

export type BackendCurrentMonitorThesis = {
  thesis_id?: string;
  instrument?: string;
  direction?: string;
  why_thesis?: string[];
  thesis_raised_at?: string;
  suggested_entry_time?: string;
  suggested_exit_time?: string;
  entry_price?: number;
  target_price?: number;
  stop_price?: number;
  latest_price?: number;
  latest_event_time?: string;
  monitor_status?: string;
  suggested_action?: string;
  expected_financial_pct?: number;
  unrealized_financial_pct?: number;
  confidence_tese_pct?: number;
  confidence_now_pct?: number;
  confidence_delta_pct?: number;
  support_rate_pct?: number;
  technical_support_pct?: number;
  fundamental_support_pct?: number;
  news_support_pct?: number;
  geo_oil_support_pct?: number;
  fundamental_available?: boolean;
  news_available?: boolean;
  geo_oil_available?: boolean;
  progress_to_target_pct?: number;
  distance_to_stop_pct?: number;
  executive_status?: string;
  executive_status_label?: string;
  executive_action?: string;
  thesis_validity?: string;
  revaluation_reason?: string;
  next_trigger?: string;
  learning_signal?: string;
  monitoring_events?: BackendMonitorEvent[];
  asset_front?: string;
  front_label?: string;
};

type BackendMonitorScanFront = {
  scanner_candidates?: BackendCurrentMonitorThesis[];
};

type BackendMonitorScanScope = {
  scanner_candidates?: BackendCurrentMonitorThesis[];
  fronts?: Record<string, BackendMonitorScanFront | undefined>;
};

export type BackendCurrentMonitorPayload = {
  generated_at?: string;
  user_id?: number;
  thesis_count?: number;
  theses?: BackendCurrentMonitorThesis[];
  scan_scope?: BackendMonitorScanScope;
  summary?: {
    target_hits?: number;
    stop_alerts?: number;
    monitoring_count?: number;
    avg_unrealized_financial_pct?: number;
    needs_attention_count?: number;
    notes?: string[];
  };
  data_quality?: {
    status?: string;
    generated_at?: string;
    source_generated_at?: string;
    notes?: string[];
    reused?: boolean;
  };
};

type BackendDecisionOption = {
  option_id?: string;
  label?: string;
};

type BackendDecisionRecord = {
  decision_id?: string;
  title?: string;
  context?: string;
  question?: string;
  options?: BackendDecisionOption[];
  priority?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  answer?: {
    option_id?: string;
    option_label?: string;
    free_text?: string;
    answered_at?: string;
  };
};

export type BackendAssistantDecisionInbox = {
  generated_at?: string;
  summary?: {
    total_count?: number;
    pending_count?: number;
    answered_count?: number;
    high_priority_count?: number;
  };
  decisions?: BackendDecisionRecord[];
};

type BackendPendingItem = {
  key?: string;
  title?: string;
  priority?: string;
  status?: string;
  action?: string;
};

type BackendClarifiedItem = {
  key?: string;
  title?: string;
  status?: string;
  detail?: string;
};

type BackendRealEstateScenario = {
  sale_price?: number;
  roi_pct?: number;
};

type BackendRealEstateAnalysis = {
  score?: number;
  confidence?: number;
  suggested_status?: string;
  next_action?: string;
  pending_items?: BackendPendingItem[];
  clarified_items?: BackendClarifiedItem[];
  scenarios?: {
    conservative?: BackendRealEstateScenario;
    base?: BackendRealEstateScenario;
    optimistic?: BackendRealEstateScenario;
  };
  breakeven_sale_price?: number;
  max_purchase_price?: number;
  price_gap_to_ceiling?: number;
  price_ceiling_status?: string;
  target_roi_pct?: number;
  cash_needed?: number;
  base_profit_pct?: number;
};

export type BackendRealEstateCandidate = {
  id?: number;
  title?: string;
  source_url?: string;
  origin?: string;
  strategy?: string;
  city?: string;
  neighborhood?: string;
  property_type?: string;
  private_area_m2?: number;
  bedrooms?: number;
  parking_spaces?: number;
  asking_price?: number;
  appraisal_value?: number;
  market_value_estimate?: number;
  estimated_sale_conservative?: number;
  estimated_sale_base?: number;
  estimated_sale_optimistic?: number;
  estimated_rent_conservative?: number;
  accepts_financing?: boolean;
  financing_validated?: boolean;
  occupancy_status?: string;
  has_registration?: boolean;
  has_edital?: boolean;
  condo_debt_known?: boolean;
  iptu_debt_known?: boolean;
  renovation_type?: string;
  renovation_budget?: number;
  carrying_months?: number;
  monthly_carrying_cost?: number;
  acquisition_costs?: number;
  selling_commission_pct?: number;
  cash_needed?: number;
  sale_comparables_count?: number;
  rent_comparables_count?: number;
  first_operation?: boolean;
  plan_a?: string;
  plan_b?: string;
  plan_c?: string;
  notes?: string;
  status?: string;
  discard_reason?: string;
  created_at?: string;
  updated_at?: string;
  analysis?: BackendRealEstateAnalysis;
};

export type BackendRealEstateCandidatesResponse = {
  summary?: {
    total?: number;
    status_counts?: Record<string, number>;
  };
  items?: BackendRealEstateCandidate[];
};

export type BackendDashboardSummary = {
  user_id?: number;
  investor_profile?: string | null;
  latest_signals?: Array<{
    signal_id?: number;
    instrument?: string;
    asset_class?: string;
    asset_class_label?: string;
    signal_type?: string;
    confidence?: number;
    rationale?: string;
  }>;
  market_coverage?: {
    generated_at?: string;
    latest_market_event_time?: string;
    latest_ingest_time?: string;
    total_instruments_covered?: number;
    asset_class_counts?: Record<string, number>;
  };
  data_quality_gate?: {
    generated_at?: string;
    summary?: {
      gate_status?: string;
      quality_score_pct?: number;
    };
    market?: {
      fresh_coverage_pct?: number;
      coverage_pct?: number;
    };
    fundamentals?: {
      fresh_coverage_pct?: number;
    };
    news?: {
      recent_news_coverage_pct?: number;
    };
  };
  historical_analysis_summary?: {
    thesis_count?: number;
    avg_expected_pct?: number;
    avg_return_pct?: number;
    avg_win_rate_pct?: number;
    approved_count?: number;
  };
  thesis_history_overview?: {
    total_tested?: number;
    success_rate_pct?: number;
    expectancy_net_pct?: number;
    event_count?: number;
    open_count?: number;
    resolution_sample_count?: number;
  };
};

type BackendAutopilotStep = {
  title?: string;
  status?: string;
  meta?: string;
};

export type BackendWorkerStatus = {
  worker_name?: string;
  status?: string;
  last_run_at?: string;
  next_run_at?: string;
  last_error?: string | null;
  cycles_today?: number;
};

export type BackendMicrotradesAutopilotLatestPayload = {
  run_started_at?: string;
  run_finished_at?: string;
  user_id?: number;
  status?: string;
  config?: {
    interval?: string;
    instruments?: string[];
  };
  steps?: BackendAutopilotStep[];
  monitor?: {
    thesis_count?: number;
    scan_scope?: BackendMonitorScanScope;
    summary?: {
      monitoring_count?: number;
      needs_attention_count?: number;
      avg_unrealized_financial_pct?: number;
    };
  };
  decision?: {
    status?: string;
    decision_id?: string;
  };
  error?: string | null;
  worker?: BackendWorkerStatus;
  runtime?: {
    running?: boolean;
    started_at?: string | null;
  };
};

export type MicrotradesAutopilotLatest = {
  cycleStatus: "success" | "partial" | "failed" | "disabled" | "unknown";
  cycleLabel: string;
  isRunning: boolean;
  agentRunning: boolean;
  runStartedAt?: string;
  runFinishedAt?: string;
  lastRunAt?: string;
  lastActivityAt?: string;
  nextRunAt?: string;
  intervalLabel: string;
  instruments: string[];
  thesisCount: number;
  monitoringCount: number;
  needsAttentionCount: number;
  decisionStatus: string;
  decisionId?: string;
  cyclesToday: number;
  lastError?: string;
  statusHeadline: string;
  statusDetail: string;
  stepCounts: {
    ok: number;
    warning: number;
    error: number;
  };
  radarCandidates: TheseEnvelope[];
};

const DEFAULT_USER_ID = 1;

export function getConfiguredUserId(): number {
  if (typeof window === "undefined") return DEFAULT_USER_ID;
  try {
    const raw = window.localStorage.getItem("graoinvest.user_id");
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_USER_ID;
  } catch {
    return DEFAULT_USER_ID;
  }
}

export function adaptCurrentMonitorTheses(payload: BackendCurrentMonitorPayload): TheseEnvelope[] {
  return (payload.theses ?? [])
    .map(mapCurrentMonitorThesis)
    .filter((item): item is TheseEnvelope => item !== null)
    .sort((a, b) => sortByUpdatedDesc(a.updated_at, b.updated_at));
}

export function adaptDataHealthFromCurrentMonitor(
  payload?: BackendCurrentMonitorPayload,
): DataHealthSnapshot {
  const theses = payload?.theses ?? [];
  const generatedAt = safeIso(payload?.data_quality?.generated_at || payload?.generated_at);
  const sourceGeneratedAt = safeOptionalIso(payload?.data_quality?.source_generated_at);
  const frontCounts = buildMonitorFrontCounts(theses);
  const freshnessList = theses.map((item) => {
    const front = monitorFrontToApi(item.asset_front);
    return freshnessFromTimestamp(safeIso(item.latest_event_time || item.suggested_exit_time || payload?.generated_at), front);
  });
  const aggregate = aggregateFreshness(freshnessList);
  const backendStatus = cleanText(payload?.data_quality?.status).toLowerCase();
  const thesisCount = safeNumber(payload?.thesis_count, theses.length);
  const monitoringCount = safeNumber(payload?.summary?.monitoring_count, thesisCount);
  const needsAttentionCount = safeNumber(payload?.summary?.needs_attention_count);
  const notes = uniqueTexts([
    ...(payload?.data_quality?.notes ?? []),
    ...(payload?.summary?.notes ?? []),
  ]);

  const status: DataHealthSnapshot["status"] =
    backendStatus === "stale_reused" || payload?.data_quality?.reused
      ? "stale_reused"
      : !payload || aggregate === "missing"
        ? "missing"
        : aggregate === "fresh"
          ? "fresh"
          : "partial";
  const fallbackActive = status === "stale_reused";
  const lastUpdateAt = newestDate([
    sourceGeneratedAt,
    generatedAt,
    ...theses.map((item) => item.latest_event_time || item.suggested_exit_time),
  ]);

  return {
    status,
    saude: dataHealthStatusToSaude(status),
    headline: dataHealthHeadline(status),
    detail: dataHealthDetail(status, thesisCount, needsAttentionCount),
    generatedAt,
    lastUpdateAt,
    thesisCount,
    monitoringCount,
    needsAttentionCount,
    notes,
    fallbackActive,
    frontCounts,
  };
}

export function adaptRealEstateCandidates(payload: BackendRealEstateCandidatesResponse): TheseEnvelope[] {
  return (payload.items ?? [])
    .map(mapRealEstateCandidate)
    .filter((item): item is TheseEnvelope => item !== null)
    .sort((a, b) => sortByUpdatedDesc(a.updated_at, b.updated_at));
}

export function adaptAssistantDecisions(payload?: BackendAssistantDecisionInbox): Decisao[] {
  return (payload?.decisions ?? [])
    .map((item) => {
      const createdAt = safeIso(item.created_at);
      const title = cleanText(item.title) || "Decisao pendente";
      const context = cleanText(item.question) || cleanText(item.context) || "Revisar contexto";
      const instrument = inferInstrument(`${title} ${context}`);
      return {
        id: cleanText(item.decision_id) || `dec-${title.toLowerCase().replace(/\s+/g, "-")}`,
        tipo: inferDecisionType(item.priority, title, context),
        titulo: title,
        resumo: context,
        criadaEm: createdAt,
        status: mapDecisionStatus(item.status),
        ativoRelacionado: instrument || undefined,
        frente: inferFrontLabel(instrument, title, context),
      };
    })
    .sort((a, b) => sortByUpdatedDesc(a.criadaEm, b.criadaEm));
}

export function synthesizeDecisionsFromTeses(teses: TheseEnvelope[]): Decisao[] {
  const openRealEstate = teses
    .filter((item) => item.front === "imoveis" && isOpenThesis(item))
    .slice(0, 3)
    .map((item) => ({
      id: `syn-imoveis-${item.id}`,
      tipo: "alerta_revisao" as const,
      titulo: `Imovel com pendencias: ${item.asset_label}`,
      resumo: item.completion.pending_items[0] || item.suggested_action,
      criadaEm: item.updated_at,
      status: "pendente" as const,
      ativoRelacionado: item.asset_label,
      frente: "Imoveis" as const,
    }));

  const monitorAlerts = teses
    .filter((item) => item.front !== "imoveis")
    .filter((item) => item.status === "refutada" || item.status === "confirmando" || item.status === "monitorando")
    .slice(0, 4)
    .map((item) => ({
      id: `syn-monitor-${item.id}`,
      tipo: item.status === "refutada" ? "alerta_revisao" as const : "confirmacao_hipotese" as const,
      titulo:
        item.status === "refutada"
          ? `Revisar tese encerrada: ${item.asset_label}`
          : `Confirmar tese ativa: ${item.asset_label}`,
      resumo: item.suggested_action || item.hypothesis,
      criadaEm: item.updated_at,
      status: "pendente" as const,
      ativoRelacionado: item.asset_label,
      frente: frontApiToFrontLabel(item.front),
    }));

  return [...openRealEstate, ...monitorAlerts]
    .sort((a, b) => sortByUpdatedDesc(a.criadaEm, b.criadaEm))
    .slice(0, 8);
}

export function adaptCockpitFromData(
  dashboard: BackendDashboardSummary | undefined,
  teses: TheseEnvelope[],
): CockpitResumo {
  const history = dashboard?.thesis_history_overview;
  const historical = dashboard?.historical_analysis_summary;
  const latestUpdate = newestDate([
    ...teses.map((item) => item.updated_at),
    dashboard?.market_coverage?.generated_at,
    dashboard?.data_quality_gate?.generated_at,
  ]);

  return {
    tesesTestadas:
      safeNumber(history?.total_tested) ||
      safeNumber(historical?.thesis_count) ||
      teses.length,
    validacaoHistoricaPct:
      pctToRatio(safeNumber(history?.success_rate_pct) || safeNumber(historical?.avg_win_rate_pct)),
    expectativaLiquidaMedia:
      pctToRatio(safeNumber(history?.expectancy_net_pct) || safeNumber(historical?.avg_return_pct)),
    tesesAtivas: teses.filter((item) => isOpenThesis(item)).length,
    aprendizadosAplicados:
      safeNumber(history?.event_count) ||
      safeNumber(history?.resolution_sample_count) ||
      safeNumber(historical?.approved_count),
    ultimaAtualizacao: latestUpdate,
    frentes: {
      B3: buildFrontSummary("b3", teses),
      Cripto: buildFrontSummary("cripto", teses),
      Imoveis: buildFrontSummary("imoveis", teses),
    },
  };
}

export function adaptMarketAssetsFromTeses(teses: TheseEnvelope[]): AtivoMercado[] {
  const byFront = (front: FrenteApi) =>
    teses
      .filter((item) => item.front === front)
      .sort((a, b) => {
        const freshnessDelta = freshnessWeight(b.data_quality.freshness_status) - freshnessWeight(a.data_quality.freshness_status);
        if (freshnessDelta !== 0) return freshnessDelta;
        return b.confidence_pct - a.confidence_pct;
      });

  const selected = [
    ...byFront("b3").slice(0, 3),
    ...byFront("cripto").slice(0, 3),
    ...byFront("imoveis").slice(0, 2),
  ];

  return selected.map((item, index) => ({
    ticker: marketTicker(item),
    nome: item.title || item.hypothesis,
    frente: frontApiToFrontLabel(item.front),
    preco: safeNumber(item.current_value),
    variacao: safeNumber(item.current_result_pct),
    destaque: index < 3,
  }));
}

export function adaptFontesFromTeses(teses: TheseEnvelope[]): FonteDados[] {
  return (["b3", "cripto", "imoveis"] as FrenteApi[]).map((front) => {
    const items = teses.filter((item) => item.front === front);
    const freshness = aggregateFreshness(items.map((item) => item.data_quality.freshness_status));
    return {
      nome: sourceName(front),
      frente: frontApiToFrontLabel(front),
      ultimaAtualizacao: newestDate(items.map((item) => item.updated_at)),
      saude: freshnessToSaude(freshness),
    };
  });
}

function adaptMonitorThesisList(items?: BackendCurrentMonitorThesis[]): TheseEnvelope[] {
  return (items ?? [])
    .map(mapCurrentMonitorThesis)
    .filter((item): item is TheseEnvelope => item !== null)
    .sort((a, b) => sortByUpdatedDesc(a.updated_at, b.updated_at));
}

function extractMicrotradeRadarCandidates(
  scope?: BackendMonitorScanScope,
): TheseEnvelope[] {
  const cryptoFrontCandidates = adaptMonitorThesisList(scope?.fronts?.cripto?.scanner_candidates)
    .filter((item) => item.front === "cripto");
  if (cryptoFrontCandidates.length) return cryptoFrontCandidates;

  return adaptMonitorThesisList(scope?.scanner_candidates)
    .filter((item) => item.front === "cripto");
}

export function adaptMicrotradesAutopilotLatest(
  payload?: BackendMicrotradesAutopilotLatestPayload,
): MicrotradesAutopilotLatest | undefined {
  if (!payload) return undefined;

  const cycleStatus = normalizeCycleStatus(payload.status);
  const workerStatus = cleanText(payload.worker?.status).toLowerCase();
  const runtimeRunning = Boolean(payload.runtime?.running);
  const runStartedAt = safeOptionalIso(payload.run_started_at);
  const runFinishedAt = safeOptionalIso(payload.run_finished_at);
  const lastRunAt = safeOptionalIso(payload.worker?.last_run_at);
  const lastActivityAt = newestOptionalIso([lastRunAt, runFinishedAt, runStartedAt]);
  const nextRunAt = safeOptionalIso(payload.worker?.next_run_at);
  const isRunning = inferAutopilotCycleRunning({
    runtimeRunning,
    runStartedAt,
    runFinishedAt,
  });
  const agentRunning = inferAutopilotAgentRunning({
    cycleStatus,
    runtimeRunning,
    workerStatus,
    nextRunAt,
  });
  const instruments = (payload.config?.instruments ?? [])
    .map((item) => cleanText(item).toUpperCase())
    .filter(Boolean);
  const intervalLabel = cleanText(payload.config?.interval) || "5m";
  const stepCounts = (payload.steps ?? []).reduce(
    (acc, step) => {
      const status = cleanText(step.status).toLowerCase();
      if (status === "ok") acc.ok += 1;
      else if (status === "warning") acc.warning += 1;
      else if (status === "error") acc.error += 1;
      return acc;
    },
    { ok: 0, warning: 0, error: 0 },
  );
  const monitoringCount = safeNumber(payload.monitor?.summary?.monitoring_count, safeNumber(payload.monitor?.thesis_count));
  const needsAttentionCount = safeNumber(payload.monitor?.summary?.needs_attention_count);
  const thesisCount = safeNumber(payload.monitor?.thesis_count, monitoringCount);
  const radarCandidates = extractMicrotradeRadarCandidates(payload.monitor?.scan_scope);
  const decisionStatus = cleanText(payload.decision?.status).toLowerCase() || "skipped";
  const lastError =
    cleanText(payload.error) ||
    cleanText(payload.worker?.last_error) ||
    cleanText((payload.steps ?? []).find((step) => cleanText(step.status).toLowerCase() !== "ok")?.meta) ||
    undefined;

  return {
    cycleStatus,
    cycleLabel: buildAutopilotCycleLabel(cycleStatus, isRunning),
    isRunning,
    agentRunning,
    runStartedAt,
    runFinishedAt,
    lastRunAt,
    lastActivityAt,
    nextRunAt,
    intervalLabel,
    instruments,
    thesisCount,
    monitoringCount,
    needsAttentionCount,
    decisionStatus,
    decisionId: cleanText(payload.decision?.decision_id) || undefined,
    cyclesToday: safeNumber(payload.worker?.cycles_today),
    lastError,
    statusHeadline: buildAutopilotHeadline(cycleStatus, isRunning),
    statusDetail: buildAutopilotDetail({
      cycleStatus,
      isRunning,
      lastError,
      monitoringCount,
      needsAttentionCount,
      intervalLabel,
      instruments,
      decisionStatus,
      stepCounts,
    }),
    stepCounts,
    radarCandidates,
  };
}

function mapCurrentMonitorThesis(item: BackendCurrentMonitorThesis): TheseEnvelope | null {
  const front = monitorFrontToApi(item.asset_front);
  const instrument = cleanText(item.instrument);
  if (!instrument) return null;

  const openedAt = safeIso(item.thesis_raised_at || item.suggested_entry_time);
  const updatedAt = safeIso(item.latest_event_time || item.suggested_exit_time || openedAt);
  const expectedResultPct = round(safeNumber(item.expected_financial_pct), 4);
  const currentResultPct = round(safeNumber(item.unrealized_financial_pct), 4);
  const confidenceNow = clamp(round(safeNumber(item.confidence_now_pct, safeNumber(item.confidence_tese_pct, 0))), 1, 100);
  const closed = hasClosedSignal(item, front);
  const status = mapMonitorStatus(item, front, closed, currentResultPct, expectedResultPct);
  const closedAt = closed ? updatedAt : undefined;
  const completion = buildMonitorCompletion(item, front, status);
  const freshnessStatus = freshnessFromTimestamp(updatedAt, front);
  const dataQualityConfidence = clamp(Math.round((confidenceNow * 0.6) + (completion.completion_pct * 0.4)), 1, 100);

  return {
    id: cleanText(item.thesis_id) || `${front}-${instrument.toLowerCase()}`,
    front,
    title: buildMonitorTitle(item, front),
    asset_label: instrumentLabel(instrument),
    hypothesis: buildMonitorHypothesis(item),
    status,
    opened_at: openedAt,
    updated_at: updatedAt,
    closed_at: closedAt,
    expected_result_pct: expectedResultPct,
    current_result_pct: currentResultPct,
    confidence_pct: confidenceNow,
    entry_value: safeNumber(item.entry_price),
    current_value: safeNumber(item.latest_price, safeNumber(item.entry_price)),
    target_value: safeNumber(item.target_price, safeNumber(item.latest_price, safeNumber(item.entry_price))),
    stop_or_invalidation: cleanText(item.next_trigger) || cleanText(item.revaluation_reason) || "Rever sinais e risco antes de manter a tese.",
    stop_value: safeNumber(item.stop_price),
    suggested_action: prettifyText(cleanText(item.executive_action) || cleanText(item.suggested_action) || "manter_monitoramento"),
    learning_note: cleanText(item.learning_signal) || cleanText(item.revaluation_reason),
    data_quality: {
      freshness_status: freshnessStatus,
      last_update_at: updatedAt,
      confidence_in_data_pct: dataQualityConfidence,
    },
    specific: front === "cripto" ? buildMicrotradeSpecific(item, instrument, updatedAt) : buildB3Specific(item, instrument),
    completion,
  };
}

function mapRealEstateCandidate(item: BackendRealEstateCandidate): TheseEnvelope | null {
  const id = safeNumber(item.id);
  if (!id) return null;

  const analysis = item.analysis ?? {};
  const pendingItems = (analysis.pending_items ?? [])
    .map((entry) => cleanText(entry.title))
    .filter(Boolean);
  const clarifiedItems = (analysis.clarified_items ?? [])
    .map((entry) => cleanText(entry.title))
    .filter(Boolean);
  const completion = buildRealEstateCompletion(item, pendingItems);
  const scorePct = clamp(Math.round(safeNumber(analysis.score)), 1, 100);
  const dataConfidencePct = clamp(Math.round(safeNumber(analysis.confidence, completion.completion_pct)), 1, 100);
  const updatedAt = safeIso(item.updated_at || item.created_at);
  const status = mapRealEstateStatus(item, analysis, pendingItems.length);
  const targetValue =
    safeNumber(analysis.scenarios?.base?.sale_price) ||
    safeNumber(item.estimated_sale_base) ||
    safeNumber(item.market_value_estimate, safeNumber(item.asking_price));
  const currentValue =
    safeNumber(item.market_value_estimate) ||
    safeNumber(item.appraisal_value) ||
    safeNumber(item.asking_price);
  const stopValue = safeNumber(analysis.max_purchase_price);
  const expectedResultPct =
    round(safeNumber(analysis.scenarios?.base?.roi_pct, safeNumber(analysis.base_profit_pct)), 2);
  const currentResultPct = round(safeNumber(analysis.base_profit_pct, expectedResultPct), 2);
  const assetLabel = buildRealEstateAssetLabel(item);

  return {
    id: `imovel-${id}`,
    front: "imoveis",
    title: cleanText(item.title) || assetLabel,
    asset_label: assetLabel,
    hypothesis: buildRealEstateHypothesis(item, targetValue, stopValue),
    status,
    opened_at: safeIso(item.created_at || updatedAt),
    updated_at: updatedAt,
    closed_at: status === "refutada" ? updatedAt : undefined,
    expected_result_pct: expectedResultPct,
    current_result_pct: currentResultPct,
    confidence_pct: scorePct,
    entry_value: safeNumber(item.asking_price),
    current_value: currentValue,
    target_value: targetValue,
    stop_or_invalidation:
      cleanText(item.discard_reason) ||
      cleanText(analysis.price_ceiling_status) ||
      cleanText(analysis.next_action) ||
      "Revalidar teto, documentacao e comparaveis antes de seguir.",
    stop_value: stopValue,
    suggested_action: cleanText(analysis.next_action) || "Revisar pendencias da oportunidade",
    learning_note: cleanText(item.notes) || cleanText(item.plan_b),
    data_quality: {
      freshness_status: freshnessFromTimestamp(updatedAt, "imoveis"),
      last_update_at: updatedAt,
      confidence_in_data_pct: dataConfidencePct,
    },
    specific: buildRealEstateSpecific(item, analysis, clarifiedItems, pendingItems),
    completion,
  };
}

function buildMicrotradeSpecific(
  item: BackendCurrentMonitorThesis,
  instrument: string,
  updatedAt: string,
): SpecificMicrotrade {
  const pressure = clamp(Math.round(
    (safeNumber(item.confidence_now_pct) * 0.55) +
    (safeNumber(item.support_rate_pct) * 0.25) +
    (Math.max(0, safeNumber(item.progress_to_target_pct)) * 0.20),
  ), 0, 100);
  const evidences = (item.why_thesis ?? []).slice(0, 5).map(prettifySignal);

  return {
    kind: "microtrade",
    window_min: inferWindowMinutes(item.suggested_entry_time, item.suggested_exit_time, 40),
    expires_at: safeIso(item.suggested_exit_time || updatedAt),
    last_tick_at: updatedAt,
    is_data_delayed: freshnessFromTimestamp(updatedAt, "cripto") !== "fresh",
    trigger_pressure_pct: pressure,
    evidences,
    short_thesis_summary:
      cleanText(item.executive_status_label) || cleanText(item.revaluation_reason) || instrumentLabel(instrument),
  };
}

function buildB3Specific(item: BackendCurrentMonitorThesis, instrument: string): SpecificB3 {
  const direction = monitorDirectionToPosition(item.direction);
  const technicalSupport = round(safeNumber(item.technical_support_pct), 2);
  const supportRate = round(safeNumber(item.support_rate_pct), 2);
  const fundamentalsSupport = round(safeNumber(item.fundamental_support_pct), 2);
  const newsSupport = round(safeNumber(item.news_support_pct), 2);

  return {
    kind: "b3",
    ticker: instrument,
    direction,
    evidences: (item.why_thesis ?? []).slice(0, 6).map(prettifySignal),
    technicals: [
      {
        label: "Suporte tecnico",
        value: `${technicalSupport.toFixed(2)}%`,
        bias: supportBias(technicalSupport, item.direction),
      },
      {
        label: "Suporte historico",
        value: `${supportRate.toFixed(2)}%`,
        bias: supportBias(supportRate, item.direction),
      },
      {
        label: "Confianca agora",
        value: `${round(safeNumber(item.confidence_now_pct), 1).toFixed(1)}%`,
        bias: supportBias(safeNumber(item.confidence_now_pct), item.direction),
      },
    ],
    fundamentals:
      item.fundamental_available
        ? [
            { label: "Suporte fundamental", value: `${fundamentalsSupport.toFixed(2)}%`, trend: trendFromSupport(fundamentalsSupport) },
            { label: "Suporte de noticias", value: `${newsSupport.toFixed(2)}%`, trend: trendFromSupport(newsSupport) },
          ]
        : [],
    news:
      item.news_available
        ? [
            {
              title: cleanText(item.revaluation_reason) || "Contexto de noticias influencia a tese.",
              source: "thesis_current_monitor",
              published_at: safeIso(item.latest_event_time || item.suggested_entry_time),
              sentiment: sentimentFromSupport(newsSupport, item.direction),
            },
          ]
        : [],
    invalidation_detail: cleanText(item.next_trigger) || cleanText(item.revaluation_reason),
  };
}

function buildRealEstateSpecific(
  item: BackendRealEstateCandidate,
  analysis: BackendRealEstateAnalysis,
  clarifiedItems: string[],
  pendingItems: string[],
): SpecificImovel {
  const evidences = [...clarifiedItems, ...pendingItems.map((entry) => `Pendente: ${entry}`)].slice(0, 6);

  return {
    kind: "imovel",
    source_url: cleanText(item.source_url) || undefined,
    origin: cleanText(item.origin) || undefined,
    strategy: normalizeRealEstateStrategy(item.strategy),
    city: cleanText(item.city) || undefined,
    neighborhood: cleanText(item.neighborhood) || undefined,
    property_type: cleanText(item.property_type) || undefined,
    imovel_status: mapRealEstateDossierStatus(item.status, analysis),
    score_pct: clamp(Math.round(safeNumber(analysis.score)), 0, 100),
    next_step: cleanText(analysis.next_action) || undefined,
    asking_price: safeMaybeNumber(item.asking_price),
    appraisal_value: safeMaybeNumber(item.appraisal_value),
    market_value_estimate: safeMaybeNumber(item.market_value_estimate),
    ceiling_price: safeMaybeNumber(analysis.max_purchase_price),
    cash_needed: safeMaybeNumber(analysis.cash_needed, item.cash_needed),
    renovation_budget: safeMaybeNumber(item.renovation_budget),
    carrying_months: safeMaybeNumber(item.carrying_months),
    monthly_carrying_cost: safeMaybeNumber(item.monthly_carrying_cost),
    sale_comparables_count: safeMaybeNumber(item.sale_comparables_count),
    rent_comparables_count: safeMaybeNumber(item.rent_comparables_count),
    estimated_sale_conservative: safeMaybeNumber(item.estimated_sale_conservative, analysis.scenarios?.conservative?.sale_price),
    estimated_sale_base: safeMaybeNumber(item.estimated_sale_base, analysis.scenarios?.base?.sale_price),
    estimated_sale_optimistic: safeMaybeNumber(item.estimated_sale_optimistic, analysis.scenarios?.optimistic?.sale_price),
    estimated_rent_conservative: safeMaybeNumber(item.estimated_rent_conservative),
    roi_estimated_pct: safeMaybeNumber(analysis.scenarios?.base?.roi_pct, analysis.base_profit_pct),
    prazo_estimado_meses: safeMaybeNumber(item.carrying_months),
    accepts_financing: item.accepts_financing,
    financing_validated: item.financing_validated,
    diligence: buildRealEstateDiligence(item),
    plan_a: cleanText(item.plan_a) || undefined,
    plan_b: cleanText(item.plan_b) || undefined,
    plan_c: cleanText(item.plan_c) || undefined,
    exit_rule:
      cleanText(item.discard_reason) ||
      cleanText(analysis.price_ceiling_status) ||
      cleanText(analysis.next_action) ||
      undefined,
    notes: cleanText(item.notes) || undefined,
    analysis: buildRealEstateAnalysisText(item, analysis),
    evidences: evidences.length ? evidences : undefined,
  };
}

function buildMonitorCompletion(
  item: BackendCurrentMonitorThesis,
  front: FrenteApi,
  status: StatusTese,
): Completion {
  const missingFields: string[] = [];
  if (!item.fundamental_available) missingFields.push("fundamentos");
  if (!item.news_available) missingFields.push("noticias");
  if (front === "b3" && !item.geo_oil_available) missingFields.push("contexto_macro");

  const pendingItems = [
    cleanText(item.next_trigger),
    status === "refutada" ? "Revisar regra de invalidacao no motor" : "",
  ].filter(Boolean);

  const completionPct = clamp(100 - (missingFields.length * 15), 55, 100);
  return {
    is_complete: missingFields.length === 0,
    completion_pct: completionPct,
    missing_fields: missingFields,
    pending_items: pendingItems,
    next_required_action:
      prettifyText(cleanText(item.executive_action) || cleanText(item.suggested_action) || "revisar sinais"),
  };
}

function buildRealEstateCompletion(
  item: BackendRealEstateCandidate,
  pendingItems: string[],
): Completion {
  const missingFields: string[] = [];
  if (!item.has_registration) missingFields.push("matricula");
  if (!item.financing_validated) missingFields.push("financiamento_validado");
  if (safeNumber(item.sale_comparables_count) < 3) missingFields.push("comparaveis_venda");
  if (safeNumber(item.rent_comparables_count) < 3) missingFields.push("comparaveis_aluguel");
  if (!item.condo_debt_known) missingFields.push("divida_condominio");
  if (!item.iptu_debt_known) missingFields.push("divida_iptu");

  const analysisConfidence = clamp(Math.round(safeNumber(item.analysis?.confidence, 35)), 15, 100);

  return {
    is_complete: pendingItems.length === 0 && analysisConfidence >= 85,
    completion_pct: analysisConfidence,
    missing_fields: missingFields,
    pending_items: pendingItems,
    next_required_action:
      cleanText(item.analysis?.next_action) ||
      (pendingItems[0] ? `Resolver: ${pendingItems[0]}` : "Revalidar oportunidade"),
  };
}

function buildFrontSummary(front: FrenteApi, teses: TheseEnvelope[]) {
  const items = teses.filter((item) => item.front === front);
  const openItems = items.filter((item) => isOpenThesis(item));
  return {
    ativas: openItems.length,
    saude: freshnessToSaude(aggregateFreshness(items.map((item) => item.data_quality.freshness_status))),
    ultimaIngestaoEm: newestDate(items.map((item) => item.updated_at)),
  };
}

function buildMonitorFrontCounts(theses: BackendCurrentMonitorThesis[]): DataHealthSnapshot["frontCounts"] {
  const counts: DataHealthSnapshot["frontCounts"] = {
    B3: 0,
    Cripto: 0,
    Imoveis: 0,
  };
  for (const item of theses) {
    counts[frontApiToFrontLabel(monitorFrontToApi(item.asset_front))] += 1;
  }
  return counts;
}

function dataHealthStatusToSaude(status: DataHealthSnapshot["status"]) {
  if (status === "fresh") return "atualizado";
  if (status === "missing") return "indisponivel";
  return "parcial";
}

function dataHealthHeadline(status: DataHealthSnapshot["status"]): string {
  if (status === "fresh") return "Dados frescos";
  if (status === "stale_reused") return "Monitor preservado";
  if (status === "missing") return "Dados indisponiveis";
  return "Dados parciais";
}

function dataHealthDetail(
  status: DataHealthSnapshot["status"],
  thesisCount: number,
  needsAttentionCount: number,
): string {
  if (status === "fresh") {
    return `${thesisCount} teses alimentadas com dados recentes.`;
  }
  if (status === "stale_reused") {
    return `Sem tick fresco; mantendo ${thesisCount} teses validas ate a proxima ingestao.`;
  }
  if (status === "missing") {
    return "O laboratorio nao encontrou dados suficientes para atualizar o monitor.";
  }
  if (needsAttentionCount > 0) {
    return `${needsAttentionCount} tese(s) precisam de cuidado por atraso ou cobertura parcial.`;
  }
  return "Parte das fontes esta atrasada, mas ainda ha base para acompanhamento.";
}

function mapMonitorStatus(
  item: BackendCurrentMonitorThesis,
  front: FrenteApi,
  closed: boolean,
  currentResultPct: number,
  expectedResultPct: number,
): StatusTese {
  const monitorStatus = cleanText(item.monitor_status);
  const executiveStatus = cleanText(item.executive_status);

  if (closed) {
    if (monitorStatus === "target_hit") return "validada";
    if (executiveStatus === "invalidada" || monitorStatus === "stop_alert" || currentResultPct < 0) return "refutada";
    if (currentResultPct > 0 && currentResultPct >= Math.max(expectedResultPct * 0.9, 0.4)) return "validada";
    return front === "cripto" ? "encerrada_tempo" : "encerrada_inatividade";
  }

  if (executiveStatus === "invalidada" || monitorStatus === "stop_alert") return "refutada";
  if (safeNumber(item.confidence_now_pct) >= 72 || safeNumber(item.progress_to_target_pct) >= 80) return "confirmando";
  return "monitorando";
}

function mapRealEstateStatus(
  item: BackendRealEstateCandidate,
  analysis: BackendRealEstateAnalysis,
  pendingCount: number,
): StatusTese {
  const statusText = `${cleanText(item.status)} ${cleanText(analysis.suggested_status)}`.toLowerCase();
  if (statusText.includes("descart")) return "refutada";
  if (statusText.includes("negoci")) return "confirmando";
  if (safeNumber(analysis.score) >= 75) return "confirmando";
  if (pendingCount >= 5 || safeNumber(analysis.confidence) < 45) return "preparando";
  return "monitorando";
}

function mapDecisionStatus(value?: string): Decisao["status"] {
  const normalized = cleanText(value).toLowerCase();
  if (normalized === "answered") return "concluida";
  if (normalized === "dismissed") return "rejeitada";
  return "pendente";
}

function inferDecisionType(priority?: string, title?: string, context?: string): Decisao["tipo"] {
  const joined = `${cleanText(title)} ${cleanText(context)}`.toLowerCase();
  if (cleanText(priority) === "high" || joined.includes("falha") || joined.includes("atencao") || joined.includes("alerta")) {
    return "alerta_revisao";
  }
  if (joined.includes("confirm") || joined.includes("hipotese")) return "confirmacao_hipotese";
  if (joined.includes("mensagem") || joined.includes("reporte")) return "mensagem";
  return "sugestao_tese";
}

function inferFrontLabel(instrument: string, title?: string, context?: string): Frente | undefined {
  const joined = `${instrument} ${cleanText(title)} ${cleanText(context)}`.toUpperCase();
  if (/(BTC|ETH|SOL|BNB|ADA|XRP|USDT|USDC)/.test(joined)) return "Cripto";
  if (/(APTO|APARTAMENTO|IMOVEL|LEILAO|CASA|SALA|STUDIO|KITNET)/.test(joined)) return "Imoveis";
  if (instrument) return "B3";
  return undefined;
}

function buildMonitorTitle(item: BackendCurrentMonitorThesis, front: FrenteApi): string {
  const direction = cleanText(item.direction);
  const instrument = instrumentLabel(cleanText(item.instrument));
  if (front === "cripto") {
    return `Microtrade ${direction || "monitorado"} em ${instrument}`;
  }
  return `Tese ${direction || "monitorada"} em ${instrument}`;
}

function buildMonitorHypothesis(item: BackendCurrentMonitorThesis): string {
  const evidences = (item.why_thesis ?? []).slice(0, 4).map(prettifySignal);
  if (evidences.length) return evidences.join(" | ");
  return cleanText(item.revaluation_reason) || "Tese monitorada automaticamente pelo motor.";
}

function buildRealEstateAssetLabel(item: BackendRealEstateCandidate): string {
  const locality = cleanText(item.neighborhood) || cleanText(item.city) || "Imovel";
  const property = cleanText(item.property_type) || "oportunidade";
  return `${locality} · ${property}`;
}

function buildRealEstateHypothesis(
  item: BackendRealEstateCandidate,
  targetValue: number,
  stopValue: number,
): string {
  const asking = safeNumber(item.asking_price);
  const strategy = cleanText(item.strategy) || "estrategia em estudo";
  if (asking > 0 && targetValue > 0) {
    return `Tese ${strategy}: comprar em ${formatMoney(asking)} e buscar valor base em ${formatMoney(targetValue)} com teto de seguranca em ${formatMoney(stopValue)}.`;
  }
  return cleanText(item.notes) || "Oportunidade imobiliaria em avaliacao.";
}

function buildRealEstateAnalysisText(item: BackendRealEstateCandidate, analysis: BackendRealEstateAnalysis): string {
  const score = safeNumber(analysis.score);
  const confidence = safeNumber(analysis.confidence);
  const ceilingStatus = cleanText(analysis.price_ceiling_status);
  const baseRoi = safeNumber(analysis.scenarios?.base?.roi_pct, analysis.base_profit_pct);
  const parts = [
    score ? `Score ${score}/100.` : "",
    confidence ? `Confianca de dados ${confidence}/100.` : "",
    ceilingStatus ? `${ceilingStatus}.` : "",
    baseRoi ? `ROI base estimado ${round(baseRoi, 2).toFixed(2)}%.` : "",
    cleanText(item.notes),
  ].filter(Boolean);
  return parts.join(" ");
}

function buildRealEstateDiligence(item: BackendRealEstateCandidate): SpecificImovel["diligence"] {
  const occupancy = cleanText(item.occupancy_status).toLowerCase();
  return [
    {
      label: "Matricula atualizada",
      state: item.has_registration ? "ok" : "pendente",
      detail: item.has_registration ? "Confirmada no radar." : "Precisa ser validada.",
    },
    {
      label: "Edital / fonte oficial",
      state: item.has_edital ? "ok" : "nao_validado",
      detail: item.has_edital ? "Fonte oficial localizada." : "Ainda sem fonte oficial validada.",
    },
    {
      label: "Divida de condominio",
      state: item.condo_debt_known ? "ok" : "pendente",
      detail: item.condo_debt_known ? "Campo informado no radar." : "Situacao ainda parcial.",
    },
    {
      label: "Divida de IPTU",
      state: item.iptu_debt_known ? "ok" : "pendente",
      detail: item.iptu_debt_known ? "Campo informado no radar." : "Situacao ainda parcial.",
    },
    {
      label: "Ocupacao",
      state:
        occupancy === "ocupado"
          ? "alerta"
          : occupancy === "desocupado"
            ? "ok"
            : "pendente",
      detail: cleanText(item.occupancy_status) || "Nao informado",
    },
    {
      label: "Financiamento aceito",
      state:
        item.financing_validated
          ? "ok"
          : item.accepts_financing
            ? "pendente"
            : "alerta",
      detail:
        item.financing_validated
          ? "Financiamento validado."
          : item.accepts_financing
            ? "Aceita financiamento, mas ainda sem validacao."
            : "Nao aceita financiamento.",
    },
  ];
}

function mapRealEstateDossierStatus(
  status?: string,
  analysis?: BackendRealEstateAnalysis,
): SpecificImovel["imovel_status"] {
  const normalized = `${cleanText(status)} ${cleanText(analysis?.suggested_status)}`.toLowerCase();
  if (normalized.includes("descart")) return "descartada";
  if (normalized.includes("negoci")) return "negociacao";
  if (normalized.includes("dilig") || safeNumber(analysis?.score) >= 70) return "diligencia";
  return "prospeccao";
}

function monitorFrontToApi(value?: string): FrenteApi {
  const normalized = cleanText(value).toLowerCase();
  if (normalized.includes("cripto")) return "cripto";
  if (normalized.includes("imove")) return "imoveis";
  return "b3";
}

function frontApiToFrontLabel(front: FrenteApi): Frente {
  if (front === "cripto") return "Cripto";
  if (front === "imoveis") return "Imoveis";
  return "B3";
}

function monitorDirectionToPosition(direction?: string): SpecificB3["direction"] {
  const normalized = cleanText(direction).toLowerCase();
  if (normalized === "bearish") return "short";
  if (normalized === "bullish") return "long";
  return "neutra";
}

function normalizeRealEstateStrategy(strategy?: string): SpecificImovel["strategy"] | undefined {
  const normalized = cleanText(strategy).toLowerCase();
  if (normalized.includes("flip")) return "flip";
  if (normalized.includes("hold")) return "buy_and_hold";
  if (normalized.includes("renda") || normalized.includes("alug")) return "renda";
  if (normalized.includes("arbitr")) return "arbitragem";
  if (normalized.includes("valor")) return "valorizacao";
  return undefined;
}

function supportBias(value: number, direction?: string): SpecificB3["technicals"][number]["bias"] {
  if (value < 45) return "neutral";
  const normalized = cleanText(direction).toLowerCase();
  if (normalized === "bearish") return "bear";
  if (normalized === "bullish") return "bull";
  return "neutral";
}

function trendFromSupport(value: number): "up" | "down" | "flat" {
  if (value >= 60) return "up";
  if (value <= 40) return "down";
  return "flat";
}

function sentimentFromSupport(
  value: number,
  direction?: string,
): "positivo" | "negativo" | "neutro" {
  if (value < 45) return "neutro";
  const normalized = cleanText(direction).toLowerCase();
  if (normalized === "bearish") return "negativo";
  if (normalized === "bullish") return "positivo";
  return "neutro";
}

function inferWindowMinutes(start?: string, end?: string, fallback = 40): number {
  const startMs = toTime(start);
  const endMs = toTime(end);
  if (!startMs || !endMs || endMs <= startMs) return fallback;
  const diffMin = Math.round((endMs - startMs) / 60_000);
  return clamp(diffMin, 5, 24 * 60);
}

function hasClosedSignal(item: BackendCurrentMonitorThesis, front: FrenteApi): boolean {
  const events = item.monitoring_events ?? [];
  if (events.some((event) => cleanText(event.event_type) === "exit_snapshot")) return true;

  const exitMs = toTime(item.suggested_exit_time);
  if (!exitMs) return false;

  const graceMs = front === "cripto" ? 10 * 60_000 : 24 * 60 * 60_000;
  return Date.now() - exitMs > graceMs;
}

function aggregateFreshness(list: FreshnessStatus[]): FreshnessStatus {
  if (!list.length) return "missing";
  const freshCount = list.filter((item) => item === "fresh").length;
  const usableCount = list.filter((item) => item === "fresh" || item === "partial").length;
  if (freshCount === list.length) return "fresh";
  if (usableCount > 0) return "partial";
  if (list.some((item) => item === "stale")) return "stale";
  return "missing";
}

function freshnessToSaude(status: FreshnessStatus): FonteDados["saude"] {
  if (status === "fresh") return "atualizado";
  if (status === "missing") return "indisponivel";
  return "parcial";
}

function freshnessFromTimestamp(timestamp: string, front: FrenteApi): FreshnessStatus {
  const ageMs = Date.now() - toTime(timestamp);
  if (!Number.isFinite(ageMs) || ageMs < 0) return "fresh";

  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (front === "cripto") {
    if (ageMs <= 30 * minute) return "fresh";
    if (ageMs <= 6 * hour) return "partial";
    if (ageMs <= 2 * day) return "stale";
    return "missing";
  }

  if (front === "b3") {
    if (ageMs <= day) return "fresh";
    if (ageMs <= 7 * day) return "partial";
    if (ageMs <= 21 * day) return "stale";
    return "missing";
  }

  if (ageMs <= 2 * day) return "fresh";
  if (ageMs <= 14 * day) return "partial";
  if (ageMs <= 45 * day) return "stale";
  return "missing";
}

function marketTicker(item: TheseEnvelope): string {
  if (item.front === "b3") {
    const specific = item.specific as Partial<SpecificB3>;
    return specific.ticker || item.asset_label;
  }
  if (item.front === "cripto") return cryptoSymbolFromText(item.asset_label) || item.asset_label;
  const specific = item.specific as Partial<SpecificImovel>;
  const neighborhood = cleanText(specific.neighborhood);
  if (neighborhood) return neighborhood.toUpperCase().slice(0, 10);
  return `IMV-${item.id.replace("imovel-", "")}`;
}

function sourceName(front: FrenteApi): string {
  if (front === "b3") return "B3 - motor de teses";
  if (front === "cripto") return "Cripto - laboratorio";
  return "Imoveis - radar";
}

function instrumentLabel(instrument: string): string {
  const clean = cleanText(instrument).toUpperCase();
  if (/(USDT|USDC|BUSD|FDUSD|BTC|ETH)$/.test(clean)) return cryptoAssetLabel(clean);
  return clean;
}

function normalizeCycleStatus(value?: string): MicrotradesAutopilotLatest["cycleStatus"] {
  const normalized = cleanText(value).toLowerCase();
  if (normalized === "success") return "success";
  if (normalized === "partial") return "partial";
  if (normalized === "failed") return "failed";
  if (normalized === "disabled") return "disabled";
  return "unknown";
}

function buildAutopilotCycleLabel(
  cycleStatus: MicrotradesAutopilotLatest["cycleStatus"],
  isRunning: boolean,
): string {
  if (isRunning) return "Rodando";
  if (cycleStatus === "success") return "Saudavel";
  if (cycleStatus === "partial") return "Parcial";
  if (cycleStatus === "failed") return "Falhou";
  if (cycleStatus === "disabled") return "Desativado";
  return "Sem historico";
}

function buildAutopilotHeadline(
  cycleStatus: MicrotradesAutopilotLatest["cycleStatus"],
  isRunning: boolean,
): string {
  if (isRunning) return "Ciclo automatico em execucao agora";
  if (cycleStatus === "success") return "Ultimo ciclo concluido";
  if (cycleStatus === "partial") return "Ultimo ciclo concluido com ressalvas";
  if (cycleStatus === "failed") return "Ultimo ciclo falhou";
  if (cycleStatus === "disabled") return "Autopilot desativado";
  return "Aguardando primeiro ciclo automatico";
}

function buildAutopilotDetail(input: {
  cycleStatus: MicrotradesAutopilotLatest["cycleStatus"];
  isRunning: boolean;
  lastError?: string;
  monitoringCount: number;
  needsAttentionCount: number;
  intervalLabel: string;
  instruments: string[];
  decisionStatus: string;
  stepCounts: MicrotradesAutopilotLatest["stepCounts"];
}): string {
  const scope = input.instruments.length
    ? `${formatCryptoScope(input.instruments)} em ${input.intervalLabel}`
    : `escopo configurado em ${input.intervalLabel}`;
  if (input.isRunning) {
    const warning =
      input.lastError && input.cycleStatus !== "success"
        ? ` Ressalva atual: ${prettifyText(input.lastError)}.`
        : "";
    return `Atualizando historico, cotacao e monitoramento no escopo ${scope}.${warning}`;
  }
  if (input.lastError && input.cycleStatus !== "success") {
    return prettifyText(input.lastError);
  }
  if (input.monitoringCount > 0) {
    const attention = input.needsAttentionCount > 0
      ? ` ${input.needsAttentionCount} ${pluralize(input.needsAttentionCount, "tese pede", "teses pedem")} atencao.`
      : "";
    const decision =
      input.decisionStatus === "created"
        ? " Card executivo publicado."
        : input.decisionStatus === "cooldown"
          ? " Publicacao no Centro de decisoes ficou em cooldown."
          : "";
    return `Monitorou ${input.monitoringCount} ${pluralize(input.monitoringCount, "tese", "teses")} no escopo ${scope}.${attention}${decision}`;
  }
  if (input.stepCounts.warning > 0 || input.stepCounts.error > 0) {
    return `Fluxo executado sem teses abertas no momento. Escopo ${scope}.`;
  }
  return `Sem execucoes recentes com teses elegiveis. Escopo ${scope}.`;
}

function inferAutopilotCycleRunning(input: {
  runtimeRunning: boolean;
  runStartedAt?: string;
  runFinishedAt?: string;
}): boolean {
  if (input.runtimeRunning) return true;
  if (!input.runStartedAt) return false;
  if (!input.runFinishedAt) return true;
  return toTime(input.runStartedAt) > toTime(input.runFinishedAt);
}

function inferAutopilotAgentRunning(input: {
  cycleStatus: MicrotradesAutopilotLatest["cycleStatus"];
  runtimeRunning: boolean;
  workerStatus: string;
  nextRunAt?: string;
}): boolean {
  if (input.cycleStatus === "disabled") return false;
  if (input.runtimeRunning) return true;
  if (["running", "idle", "scheduled", "waiting", "sleeping", "online"].includes(input.workerStatus)) {
    return true;
  }
  return Boolean(input.nextRunAt);
}

function inferInstrument(text: string): string {
  const cryptoInstrument = cryptoInstrumentFromText(text);
  if (cryptoInstrument) return cryptoInstrument;
  const match = cleanText(text).toUpperCase().match(/\b([A-Z]{4}\d{1,2}|[A-Z]{2,10}USDT)\b/);
  return match?.[1] ?? "";
}

function prettifySignal(value: string): string {
  return cleanText(value)
    .replace(/_/g, " ")
    .replace(/(\d+(?:\.\d+)?)pct/gi, "$1%")
    .trim();
}

function prettifyText(value: string): string {
  return cleanText(value)
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function newestDate(dates: Array<string | undefined>): string {
  const filtered = dates
    .map((item) => safeIso(item))
    .filter(Boolean)
    .sort((a, b) => sortByUpdatedDesc(a, b));
  return filtered[0] || new Date().toISOString();
}

function newestOptionalIso(dates: Array<string | undefined>): string | undefined {
  const filtered = dates
    .filter((item): item is string => Boolean(item))
    .sort((a, b) => sortByUpdatedDesc(a, b));
  return filtered[0];
}

function safeIso(value?: string): string {
  const parsed = new Date(cleanText(value));
  if (Number.isNaN(parsed.getTime())) return new Date().toISOString();
  return parsed.toISOString();
}

function safeOptionalIso(value?: string | null): string | undefined {
  const text = cleanText(value);
  if (!text) return undefined;
  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? undefined : parsed.toISOString();
}

function toTime(value?: string): number {
  const parsed = new Date(cleanText(value)).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function sortByUpdatedDesc(a?: string, b?: string): number {
  return toTime(b) - toTime(a);
}

function pctToRatio(value: number): number {
  if (!value) return 0;
  return value / 100;
}

function formatMoney(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  });
}

function safeMaybeNumber(primary?: number, fallback?: number): number | undefined {
  const value = safeNumber(primary, safeNumber(fallback, Number.NaN));
  return Number.isFinite(value) ? value : undefined;
}

function safeNumber(value?: number | null, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function round(value: number, digits = 2): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function cleanText(value?: string | null): string {
  return String(value ?? "").trim();
}

function uniqueTexts(values: Array<string | undefined>): string[] {
  return Array.from(new Set(values.map((value) => cleanText(value)).filter(Boolean)));
}

function pluralize(value: number, singular: string, plural = `${singular}s`): string {
  return value === 1 ? singular : plural;
}

function freshnessWeight(value: FreshnessStatus): number {
  if (value === "fresh") return 3;
  if (value === "partial") return 2;
  if (value === "stale") return 1;
  return 0;
}
