import { cleanText } from "../utils/text.js";

const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;

const STATUS_UI = Object.freeze({
  monitoring: { label: "Observando", badge: "info" },
  near_target: { label: "Confirmando", badge: "open" },
  target_hit: { label: "Validada", badge: "success" },
  stop_alert: { label: "Alerta", badge: "warning" },
  invalidated: { label: "Refutada", badge: "danger" },
  closed: { label: "Fechada", badge: "closed" },
  analysis: { label: "Observando", badge: "info" },
});

const FRONT_DEFS = Object.freeze([
  { id: "b3", label: "B3" },
  { id: "crypto", label: "Cripto" },
  { id: "real_estate", label: "Imóveis" },
]);

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function coalesce(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== "");
}

function toNumber(value, fallback = 0) {
  if (value === undefined || value === null || value === "") return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function toBoolean(value) {
  if (typeof value === "boolean") return value;
  const normalized = cleanText(value).toLowerCase();
  if (["true", "1", "sim", "yes", "open", "aberta"].includes(normalized)) return true;
  if (["false", "0", "nao", "não", "no", "closed", "fechada", "encerrada"].includes(normalized)) return false;
  return undefined;
}

function toIsoDate(value, fallback) {
  const date = value ? new Date(value) : null;
  if (date && !Number.isNaN(date.getTime())) return date.toISOString();
  return fallback instanceof Date ? fallback.toISOString() : new Date(fallback).toISOString();
}

function toOptionalIsoDate(value) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toISOString() : null;
}

function daysBetween(start, now) {
  const startDate = start ? new Date(start) : null;
  const endDate = now instanceof Date ? now : new Date(now);
  if (!startDate || Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return 0;
  return Math.max(0, Math.floor((endDate.getTime() - startDate.getTime()) / DAY_MS));
}

function hoursBetween(start, now) {
  const startDate = start ? new Date(start) : null;
  const endDate = now instanceof Date ? now : new Date(now);
  if (!startDate || Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return 0;
  return Math.max(0, Math.floor((endDate.getTime() - startDate.getTime()) / HOUR_MS));
}

function pctBetween(base, value) {
  const baseNumber = toNumber(base, 0);
  const valueNumber = toNumber(value, 0);
  if (!baseNumber) return 0;
  return ((valueNumber - baseNumber) / baseNumber) * 100;
}

function parsePlanNumber(value) {
  const text = cleanText(value);
  if (!text) return null;

  const normalized = text.includes(",") && text.includes(".")
    ? text.replace(/,/g, "")
    : text.replace(",", ".");
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
}

function parseOperationPlanPrices(plan) {
  const text = cleanText(plan);
  const numberPattern = "([0-9]+(?:[,.][0-9]+)?)";
  const rangeMatch = text.match(new RegExp(`entre\\s+${numberPattern}\\s+e\\s+${numberPattern}`, "i"));
  const targetMatch = text.match(new RegExp(`(?:para perto de|em dire(?:c|ç)[aã]o a)\\s+${numberPattern}`, "i"));
  const stopMatch = text.match(new RegExp(`Se\\s+(?:cair|subir)\\s+para\\s+${numberPattern}`, "i"));

  return {
    targetPrice: parsePlanNumber(targetMatch?.[1]),
    stopPrice: parsePlanNumber(stopMatch?.[1]),
    rangeLowerPrice: parsePlanNumber(rangeMatch?.[1]),
    rangeUpperPrice: parsePlanNumber(rangeMatch?.[2]),
  };
}

function calibrationCycleOrder(label, fallback) {
  const text = cleanText(label);
  const match = text.match(/(?:cal\.?|calibra(?:c|ç)[aã]o)?\s*0?(\d{1,3})/i);
  return match ? Number(match[1]) : fallback;
}

function frontIdForInstrument(instrument) {
  const asset = cleanText(instrument).toUpperCase();
  if (asset.endsWith("USDT") || asset.includes("BTC") || asset.includes("ETH") || asset.includes("SOL")) {
    return "crypto";
  }
  if (
    asset.includes("IMOVEL")
    || asset.includes("IMÓVEL")
    || asset.includes("GALP")
    || asset.includes("LOGIST")
    || asset.includes("TERRENO")
    || asset.includes("SALA")
    || asset.includes("APTO")
  ) {
    return "real_estate";
  }
  return "b3";
}

function frontLabel(frontId) {
  return FRONT_DEFS.find((front) => front.id === frontId)?.label ?? "B3";
}

function normalizeFront(value, fallbackInstrument) {
  const raw = cleanText(value);
  const lower = raw.toLowerCase();
  if (lower === "b3") return "B3";
  if (lower === "crypto" || lower === "cripto") return "Cripto";
  if (lower === "real_estate" || lower.includes("imóvel") || lower.includes("imoveis") || lower.includes("imóveis")) return "Imóveis";
  return frontLabel(frontIdForInstrument(fallbackInstrument));
}

function normalizeStatus(status) {
  const value = cleanText(status || "monitoring");
  return value === "analysis" ? "monitoring" : value;
}

function normalizeMonitorTrust(currentMonitor) {
  const dataQuality = currentMonitor?.data_quality ?? currentMonitor?.dataQuality ?? {};
  const status = cleanText(coalesce(dataQuality.status, currentMonitor?.data_quality_status, "fresh"));
  const reason = cleanText(coalesce(dataQuality.reason, currentMonitor?.data_quality_reason));
  const normalizedStatus = status.toLowerCase();
  const normalizedReason = reason.toLowerCase();
  const isFrozen = normalizedStatus === "stale_reused" || normalizedReason === "no_fresh_market_data";

  if (isFrozen) {
    return {
      status: status || "stale_reused",
      reason,
      isFrozen: true,
      label: "Monitor congelado",
      message: "Monitor congelado por falta de dados frescos. Mantemos o último retrato para estudo; novas decisões exigem atualização do feed.",
      generatedAt: toOptionalIsoDate(coalesce(dataQuality.generated_at, dataQuality.generatedAt, currentMonitor?.generated_at, currentMonitor?.generatedAt)),
      reusedAt: toOptionalIsoDate(coalesce(dataQuality.reused_at, dataQuality.reusedAt, currentMonitor?.reused_at, currentMonitor?.reusedAt)),
    };
  }

  return {
    status: status || "fresh",
    reason,
    isFrozen: false,
    label: "Monitor atualizado",
    message: "Monitor com dados frescos do laboratório.",
    generatedAt: toOptionalIsoDate(coalesce(dataQuality.generated_at, dataQuality.generatedAt, currentMonitor?.generated_at, currentMonitor?.generatedAt)),
    reusedAt: toOptionalIsoDate(coalesce(dataQuality.reused_at, dataQuality.reusedAt, currentMonitor?.reused_at, currentMonitor?.reusedAt)),
  };
}

function normalizeEvidence(value) {
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean);
  if (typeof value === "string") return [cleanText(value)].filter(Boolean);
  return [];
}

function availabilityFrom(value, supportPct) {
  const explicit = toBoolean(value);
  if (explicit !== undefined) return explicit;

  const score = toNumber(supportPct, null);
  if (score === null || score === 50) return undefined;
  return score > 50;
}

function sourceAvailabilityFor(source, front) {
  return {
    market: true,
    news: availabilityFrom(
      coalesce(source?.news_available, source?.newsAvailable, source?.has_news, source?.hasNews),
      coalesce(source?.news_support_pct, source?.newsSupportPct),
    ),
    fundamentals: front === "Cripto"
      ? false
      : availabilityFrom(
        coalesce(source?.fundamental_available, source?.fundamentalAvailable, source?.fundamentals_available, source?.fundamentalsAvailable),
        coalesce(source?.fundamental_support_pct, source?.fundamentalSupportPct, source?.fundamentals_support_pct, source?.fundamentalsSupportPct),
      ),
    macro: availabilityFrom(
      coalesce(source?.geo_oil_available, source?.geoOilAvailable, source?.macro_available, source?.macroAvailable),
      coalesce(source?.geo_oil_support_pct, source?.geoOilSupportPct, source?.macro_support_pct, source?.macroSupportPct),
    ),
  };
}

function coverageItem(status, label, detail = "") {
  return { status, label, detail };
}

function normalizeCoverage(payloads, monitorTrust, activeTheses) {
  const dashboardSummary = payloads?.dashboardSummary ?? {};
  const currentMonitor = payloads?.currentMonitor ?? {};
  const scanScope = currentMonitor?.scan_scope ?? currentMonitor?.scanScope ?? {};
  const freshInstruments = asArray(coalesce(scanScope.fresh_instruments, scanScope.freshInstruments));
  const tickCount = toNumber(coalesce(scanScope.tick_count, scanScope.tickCount), 0);
  const monitorThesisCount = asArray(currentMonitor?.theses).length;
  const marketFresh = !monitorTrust?.isFrozen && (freshInstruments.length > 0 || tickCount > 0 || monitorThesisCount > 0);
  const history = dashboardSummary?.thesis_history_overview ?? dashboardSummary?.thesisHistoryOverview ?? {};
  const hasHistory = toNumber(coalesce(history.total_tested, history.totalTested, history.success_count, history.successCount), 0) > 0;
  const fronts = new Set(activeTheses.map((thesis) => thesis.front).filter(Boolean));
  const cryptoOnly = fronts.size > 0 && [...fronts].every((front) => front === "Cripto");
  const anyNews = activeTheses.some((thesis) => thesis.sourceAvailability?.news === true);
  const anyFundamentals = activeTheses.some((thesis) => thesis.sourceAvailability?.fundamentals === true);
  const hasTheses = activeTheses.length > 0;

  return {
    market: coverageItem(
      marketFresh ? "fresh" : "stale",
      marketFresh ? "Mercado atualizado" : "Mercado sem frescor recente",
      freshInstruments.length > 0 ? `${freshInstruments.length} ativos com ticks recentes` : "",
    ),
    history: coverageItem(hasHistory || hasTheses ? "fresh" : "missing", hasHistory || hasTheses ? "Historico disponivel" : "Historico sem amostra"),
    news: coverageItem(anyNews ? "fresh" : "missing", anyNews ? "Noticias recentes conectadas" : "Noticias sem cobertura recente"),
    fundamentals: cryptoOnly
      ? coverageItem("not_applicable", "Fundamentos nao aplicaveis para cripto")
      : coverageItem(anyFundamentals ? "fresh" : "missing", anyFundamentals ? "Fundamentos conectados" : "Fundamentos sem cobertura recente"),
    macro: coverageItem("disabled", "Macro fora do MVP atual"),
  };
}

function sourceStatusFromCoverage(item) {
  if (!item) return "missing";
  if (item.status === "fresh") return "online";
  if (item.status === "stale") return "stale";
  if (item.status === "disabled" || item.status === "not_applicable") return "not_applicable";
  return "missing";
}

function freshnessSource(key, label, status, detail = "", meta = {}) {
  return {
    key,
    label,
    status,
    detail,
    updatedAt: meta.updatedAt ?? null,
    ageDays: meta.ageDays ?? null,
    maxAgeDays: meta.maxAgeDays ?? null,
  };
}

function freshnessFromFrontStage(key, label, frontStage, fallbackCoverage) {
  if (frontStage && typeof frontStage === "object") {
    const ageDays = toNumber(frontStage.age_days ?? frontStage.ageDays, null);
    const maxAgeDays = toNumber(frontStage.max_age_days ?? frontStage.maxAgeDays, null);
    const latestEvent = cleanText(coalesce(frontStage.latest_event_time, frontStage.latestEventTime));
    const hasData = toNumber(frontStage.count, 0) > 0 || latestEvent || ageDays !== null;
    const status = hasData && ageDays !== null && maxAgeDays !== null
      ? (ageDays <= maxAgeDays ? "online" : "stale")
      : hasData
        ? "online"
        : "missing";
    const detail = latestEvent
      ? `Último evento ${latestEvent}`
      : ageDays !== null && maxAgeDays !== null
        ? `${ageDays.toLocaleString("pt-BR")}d de ${maxAgeDays.toLocaleString("pt-BR")}d`
        : "Sem leitura operacional recente";

    return freshnessSource(key, label, status, detail, {
      updatedAt: latestEvent || null,
      ageDays,
      maxAgeDays,
    });
  }

  return freshnessSource(
    key,
    label,
    sourceStatusFromCoverage(fallbackCoverage),
    fallbackCoverage?.label || "Sem leitura operacional recente",
  );
}

function realEstateFreshness(payloads) {
  const operations = asArray(payloads?.dashboardSummary?.thesis_open_operations)
    .filter((row) => normalizeFront(row?.front, row?.action) === "Imóveis");
  const candidates = asArray(payloads?.realEstateCandidates?.candidates);
  const strategyBriefs = asArray(
    coalesce(
      payloads?.realEstateStrategyTerritoryCandidates?.matrix_briefs,
      payloads?.realEstateStrategyTerritoryCandidates?.matrixBriefs,
    ),
  );

  if (operations.length > 0) {
    const analysed = operations.filter((row) => row?.real_estate_analysis && typeof row.real_estate_analysis === "object").length;
    return freshnessSource(
      "imoveis",
      "Imóveis",
      analysed === operations.length ? "online" : "partial",
      `${operations.length} ${operations.length === 1 ? "tese imobiliaria oficial" : "teses imobiliarias oficiais"}`,
    );
  }

  if (candidates.length > 0 || strategyBriefs.length > 0) {
    return freshnessSource(
      "imoveis",
      "Imóveis",
      "partial",
      `${candidates.length + strategyBriefs.length} candidatos/briefs sem tese registrada`,
    );
  }

  return freshnessSource("imoveis", "Imóveis", "missing", "Sem tese ou candidato imobiliário no feed atual");
}

function summarizeFreshnessStatus({ sources, opsHealth, monitorTrust }) {
  const opsStatus = cleanText(opsHealth?.status).toLowerCase();
  const actionableSources = sources.filter((source) => source.status !== "not_applicable");
  const sourceStatuses = actionableSources.map((source) => source.status);

  if (opsStatus === "fail") {
    return {
      status: "missing",
      label: "Sem fonte",
      badge: "danger",
      message: cleanText(opsHealth?.message) || "O ciclo operacional registrou falha. O plano é não confiar em números sem nova verificação.",
    };
  }

  if (monitorTrust?.isFrozen || opsStatus === "blocked" || sourceStatuses.includes("stale")) {
    return {
      status: "stale",
      label: "Desatualizado",
      badge: "warning",
      message: cleanText(opsHealth?.message) || "Há dado fora da janela de frescor. O último retrato fica visível, mas novas decisões exigem atualização do feed.",
    };
  }

  if (sourceStatuses.includes("missing") || sourceStatuses.includes("partial")) {
    return {
      status: "partial",
      label: "Parcial",
      badge: "warning",
      message: "Parte das fontes ainda precisa de confirmação. O laboratório mostra o retrato, mas separa evidência fresca de lacuna.",
    };
  }

  return {
    status: "online",
    label: "Online",
    badge: "open",
    message: "Feeds principais dentro da janela de frescor. O laboratório pode ser conferido com dados atuais.",
  };
}

function buildOperationalFreshness(payloads, coverage, monitorTrust) {
  const dashboardSummary = payloads?.dashboardSummary ?? {};
  const opsHealth = dashboardSummary?.ops_health ?? {};
  const stages = opsHealth?.stages && typeof opsHealth.stages === "object" ? opsHealth.stages : {};
  const marketFeed = stages.market_feed && typeof stages.market_feed === "object" ? stages.market_feed : {};
  const marketFronts = marketFeed.fronts && typeof marketFeed.fronts === "object" ? marketFeed.fronts : {};
  const sources = [
    freshnessFromFrontStage("b3", "B3", marketFronts.b3, coverage.market),
    freshnessFromFrontStage("crypto", "Cripto", marketFronts.crypto, coverage.market),
    realEstateFreshness(payloads),
    freshnessSource("historico", "Histórico", sourceStatusFromCoverage(coverage.history), coverage.history?.label || ""),
    freshnessSource("noticias", "Notícias", sourceStatusFromCoverage(coverage.news), coverage.news?.label || ""),
    freshnessSource("fundamentos", "Fundamentos", sourceStatusFromCoverage(coverage.fundamentals), coverage.fundamentals?.label || ""),
    freshnessSource("macro", "Macro", sourceStatusFromCoverage(coverage.macro), coverage.macro?.label || ""),
  ];
  const summary = summarizeFreshnessStatus({ sources, opsHealth, monitorTrust });
  const recommendedActions = asArray(opsHealth?.recommended_actions)
    .map(cleanText)
    .filter(Boolean);

  return {
    ...summary,
    generatedAt: toOptionalIsoDate(coalesce(opsHealth?.generated_at, dashboardSummary?.updated_at, dashboardSummary?.generated_at)),
    action: recommendedActions[0] || "",
    sources,
  };
}

function coverageNotesForThesis(thesis, coverage) {
  const notes = [];
  const sourceAvailability = thesis.sourceAvailability ?? {};

  if (coverage?.market?.status === "fresh") {
    notes.push("Tese tecnica com mercado fresco.");
  } else {
    notes.push("Mercado precisa de novo refresh antes de ampliar risco.");
  }

  if (sourceAvailability.news !== true) {
    notes.push("Faltam noticias recentes para confirmar contexto.");
  }

  if (thesis.front === "Cripto") {
    notes.push("Fundamentos nao se aplicam a este par cripto.");
  } else if (sourceAvailability.fundamentals !== true) {
    notes.push("Faltam fundamentos recentes para confirmar a tese.");
  }

  const hasConfirmationGap = sourceAvailability.news !== true
    || (thesis.front !== "Cripto" && sourceAvailability.fundamentals !== true)
    || coverage?.macro?.status !== "fresh";
  if (hasConfirmationGap) {
    notes.push("Confianca reduzida por lacunas de confirmacao.");
  }

  return [...new Set(notes)];
}

function withCoverageNotes(thesis, coverage) {
  const sourceAvailability = thesis.sourceAvailability ?? sourceAvailabilityFor(thesis, thesis.front);
  const coverageNotes = asArray(thesis.coverageNotes).length > 0
    ? thesis.coverageNotes
    : coverageNotesForThesis({ ...thesis, sourceAvailability }, coverage);
  return { ...thesis, sourceAvailability, coverageNotes };
}

function normalizeDirection(value) {
  const direction = cleanText(value || "Alta");
  const lowerDirection = direction.toLowerCase();
  if (lowerDirection === "bullish") return "Alta";
  if (lowerDirection === "bearish") return "Baixa";
  if (lowerDirection === "range") return "Neutra";
  return direction;
}

function isRangeLikeThesis(...values) {
  const text = values.map(cleanText).join(" ").toLowerCase();
  return text.includes("range") || text.includes("iron condor") || text.includes("neutra");
}

function priceReferenceLabelFor(...values) {
  return isRangeLikeThesis(...values) ? "Faixa" : "Alvo";
}

function rangeBoundsFor({ entryPrice, targetPrice, stopPrice, rangeLowerPrice, rangeUpperPrice }) {
  const explicitLower = toNumber(rangeLowerPrice, null);
  const explicitUpper = toNumber(rangeUpperPrice, null);
  if (explicitLower !== null && explicitUpper !== null) {
    return {
      rangeLowerPrice: Math.min(explicitLower, explicitUpper),
      rangeUpperPrice: Math.max(explicitLower, explicitUpper),
    };
  }

  const entry = toNumber(entryPrice, null);
  const stop = toNumber(stopPrice, null);
  if (entry === null || stop === null || entry === stop) {
    return { rangeLowerPrice: null, rangeUpperPrice: null };
  }

  const width = Math.abs(entry - stop);
  return {
    rangeLowerPrice: Math.min(stop, entry - width),
    rangeUpperPrice: Math.max(stop, entry + width),
  };
}

function normalizeOperationOpenState(row, status, phase) {
  const explicit = toBoolean(row?.is_open);
  if (explicit !== undefined) return explicit;

  const normalizedStatus = cleanText(status).toLowerCase();
  if (
    normalizedStatus.includes("fechad")
    || normalizedStatus.includes("descart")
    || normalizedStatus.includes("encerrad")
  ) {
    return false;
  }

  return normalizePhase(phase) === "historico" ? false : undefined;
}

function realEstateDirectionLabel({ front, isOpen, status, expectedPct, fallback }) {
  if (front !== "Imóveis") return fallback;

  const normalizedStatus = cleanText(status).toLowerCase();
  if (isOpen === false) {
    return normalizedStatus.includes("fechad") || normalizedStatus.includes("descart")
      ? "Descartada"
      : "Encerrada";
  }

  return expectedPct > 0 ? "Potencial positivo" : "Revisar";
}

function directionTone(direction) {
  if (direction === "Alta") return "alta";
  if (direction === "Baixa") return "baixa";
  return "neutro";
}

function normalizeHypothesis(thesis, direction) {
  const directHypothesis = cleanText(coalesce(thesis.hypothesis, thesis.thesis, thesis.summary));
  if (directHypothesis) return directHypothesis;

  const reasonCategory = cleanText(thesis.reason_category);
  if (reasonCategory) {
    return `A hipótese sugere movimento de ${directionTone(direction)} apoiado por ${reasonCategory}.`;
  }

  return "Tese em monitoramento.";
}

function normalizeSuggestedOperation(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return cleanText(value);

  const fields = [
    value.label,
    value.name,
    value.strategy_name,
    value.strategyName,
    value.strategy,
    value.strategy_id,
    value.strategyId,
    value.rationale,
    value.type,
    value.description,
    value.summary,
  ]
    .map(cleanText)
    .filter(Boolean);
  return fields.length > 0 ? [...new Set(fields)].join(" - ") : "Operação sugerida pelo monitor.";
}

function parseJsonObject(value) {
  if (!value || typeof value !== "string") return {};

  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function normalizePhase(value) {
  const phase = cleanText(value).toLowerCase();
  if (phase.includes("histor")) return "historico";
  if (phase.includes("live") || phase.includes("atual") || phase.includes("monitor")) return "pos_go_live";
  return phase || "pos_go_live";
}

function phaseLabel(phase, status) {
  const normalizedStatus = cleanText(status).toLowerCase();
  const normalizedPhase = normalizePhase(phase);
  if (normalizedStatus.includes("anal")) return "Em análise";
  if (normalizedPhase.includes("anal")) return "Em análise";
  if (normalizedPhase === "historico") return "Histórica";
  return "Go-live";
}

function inferDirectionFromOperation(row) {
  const text = [
    row?.operation_plan,
    row?.structured_operation,
    row?.thesis_id,
    row?.thesis_reason,
  ].map(cleanText).join(" ").toLowerCase();

  if (text.includes("bearish") || text.includes("venda") || text.includes("bear put")) return "Baixa";
  if (text.includes("range") || text.includes("neutr")) return "Neutra";
  return "Alta";
}

function normalizeOperationRow(row, index, now) {
  const action = cleanText(coalesce(row.action, row.instrument, row.asset, `Tese ${index + 1}`));
  const phase = normalizePhase(row.phase);
  const status = cleanText(coalesce(row.status, phaseLabel(phase)));
  const outcome = cleanText(coalesce(row.outcome, row.desfecho, status || "Observando"));
  const raisedAt = toIsoDate(coalesce(row.thesis_raised_at, row.opened_at, row.created_at), now);
  const front = normalizeFront(row.front, action);
  const baseDirection = normalizeDirection(coalesce(row.direction, inferDirectionFromOperation(row)));
  const operation = cleanText(coalesce(row.operation_plan, row.operation, "Operação estruturada conforme a hipótese."));
  const structure = cleanText(coalesce(row.structured_operation, row.structure, "Estrutura com risco definido."));
  const parsedPlanPrices = parseOperationPlanPrices(operation);
  const entryPrice = toNumber(coalesce(row.entry_price_brl, row.entry_price, row.entryPrice), null);
  const currentPrice = toNumber(coalesce(row.current_price_brl, row.current_price, row.currentPrice, row.latest_price), entryPrice);
  const targetPrice = toNumber(coalesce(row.target_price_brl, row.target_price, row.targetPrice, parsedPlanPrices.targetPrice), null);
  const stopPrice = toNumber(coalesce(row.stop_price_brl, row.stop_price, row.stopPrice, parsedPlanPrices.stopPrice), null);
  const expectedPct = toNumber(coalesce(row.expected_result_pct, row.expected_pct, row.expectedPct), 0);
  const isOpen = normalizeOperationOpenState(row, status, phase);
  const resultIsEstimate = front === "Imóveis" && isOpen === false;
  const resultPct = resultIsEstimate
    ? expectedPct
    : toNumber(coalesce(row.moment_result_pct, row.result_pct, row.resultPct, row.current_pct), 0);
  const direction = realEstateDirectionLabel({
    front,
    isOpen,
    status,
    expectedPct,
    fallback: baseDirection,
  });
  const statusGroup = isOpen === false ? "Histórica" : phaseLabel(phase, status);
  const rangeBounds = isRangeLikeThesis(baseDirection, row.thesis_id, operation, structure)
    ? rangeBoundsFor({
        entryPrice,
        targetPrice,
        stopPrice,
        rangeLowerPrice: coalesce(row.range_lower_price, row.rangeLowerPrice, parsedPlanPrices.rangeLowerPrice),
        rangeUpperPrice: coalesce(row.range_upper_price, row.rangeUpperPrice, parsedPlanPrices.rangeUpperPrice),
      })
    : { rangeLowerPrice: null, rangeUpperPrice: null };

  return {
    id: cleanText(coalesce(row.thesis_number, row.id, index + 1)),
    thesisId: cleanText(coalesce(row.thesis_id, row.id, `tese-${index + 1}`)),
    phase,
    status,
    statusGroup,
    isOpen,
    resultKind: resultIsEstimate ? "estimate" : "performance",
    sourceUrl: cleanText(coalesce(row.source_url, row.sourceUrl)),
    realEstateAnalysis: row.real_estate_analysis ?? row.realEstateAnalysis ?? null,
    asset: action,
    front,
    direction,
    expectedPct,
    resultPct,
    entryPrice,
    currentPrice,
    targetPrice,
    stopPrice,
    rangeLowerPrice: rangeBounds.rangeLowerPrice,
    rangeUpperPrice: rangeBounds.rangeUpperPrice,
    priceReferenceLabel: priceReferenceLabelFor(baseDirection, row.thesis_id, operation, structure),
    exitRule: cleanText(coalesce(row.exit_rule, row.saida, "Saída por alvo, stop ou tempo conforme plano.")),
    outcome,
    days: toNumber(coalesce(row.duration_days, row.days_open, row.daysOpen), null),
    hoursOpen: hoursBetween(raisedAt, now),
    openedAt: raisedAt,
    hypothesis: cleanText(coalesce(row.thesis_reason, row.hypothesis, row.thesis, "Hipótese registrada pelo laboratório.")),
    operation,
    structure,
    learning: cleanText(coalesce(row.learning_note, row.learning, "Aprendizado será registrado ao encerrar a tese.")),
  };
}

function operationKey(row) {
  return `${row.thesisId || row.id}-${row.asset}-${row.statusGroup}`;
}

function rowFromGoLiveThesis(thesis, index) {
  const isOpen = true;
  const direction = realEstateDirectionLabel({
    front: thesis.front,
    isOpen,
    status: thesis.status,
    expectedPct: thesis.expectedPct,
    fallback: thesis.direction,
  });

  return {
    id: cleanText(coalesce(thesis.id, index + 1)),
    thesisId: cleanText(coalesce(thesis.thesisId, thesis.id, `go-live-${index + 1}`)),
    phase: thesis.front === "Imóveis" && thesis.status === "analysis" ? "analysis" : "pos_go_live",
    status: statusToUi(thesis.status).label,
    statusGroup: thesis.front === "Imóveis" && thesis.status === "analysis" ? "Em análise" : "Go-live",
    isOpen,
    resultKind: "performance",
    sourceUrl: thesis.sourceUrl,
    realEstateAnalysis: thesis.realEstateAnalysis,
    asset: thesis.asset,
    front: thesis.front,
    direction,
    expectedPct: thesis.expectedPct,
    resultPct: thesis.currentPct,
    entryPrice: thesis.entryPrice,
    targetPrice: thesis.targetPrice,
    stopPrice: thesis.stopPrice,
    rangeLowerPrice: thesis.rangeLowerPrice,
    rangeUpperPrice: thesis.rangeUpperPrice,
    priceReferenceLabel: thesis.priceReferenceLabel,
    exitRule: `Alvo ${thesis.targetPrice || "--"} / stop ${thesis.stopPrice || "--"}`,
    outcome: statusToUi(thesis.status).label,
    days: thesis.daysOpen,
    hoursOpen: thesis.hoursOpen,
    openedAt: thesis.openedAt,
    hypothesis: thesis.hypothesis,
    operation: thesis.operation,
    structure: thesis.operation,
    learning: thesis.learning,
  };
}

function buildThesisRows(dashboardSummary, goLiveTheses, now, operationRowsOverride) {
  const operationRows = operationRowsOverride
    ?? asArray(dashboardSummary?.thesis_open_operations).map((row, index) => normalizeOperationRow(row, index, now));
  const seen = new Set(operationRows.map(operationKey));

  const liveRows = goLiveTheses
    .map(rowFromGoLiveThesis)
    .filter((row) => {
      const key = operationKey(row);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

  return [...operationRows, ...liveRows];
}

function activeThesisFromRow(row) {
  return {
    id: row.id,
    thesisId: row.thesisId,
    front: row.front,
    asset: row.asset,
    direction: row.direction,
    hypothesis: row.hypothesis,
    evidence: [],
    entryPrice: row.entryPrice,
    currentPrice: row.currentPrice,
    targetPrice: row.targetPrice,
    stopPrice: row.stopPrice,
    rangeLowerPrice: row.rangeLowerPrice,
    rangeUpperPrice: row.rangeUpperPrice,
    priceReferenceLabel: row.priceReferenceLabel,
    expectedPct: row.expectedPct,
    currentPct: row.resultPct,
    daysOpen: row.days ?? 0,
    hoursOpen: row.hoursOpen,
    openedAt: row.openedAt,
    status: row.statusGroup === "Em análise" ? "analysis" : "monitoring",
    learning: row.learning,
    janeState: "monitoring",
    janeMessage: row.hypothesis,
    operation: row.operation,
    invalidation: row.exitRule,
    sourceUrl: row.sourceUrl,
    realEstateAnalysis: row.realEstateAnalysis,
  };
}

function isActiveOperationRow(row) {
  return row.statusGroup === "Go-live" || row.statusGroup === "Em análise";
}

function thesisKey(thesis) {
  return `${thesis.front}-${thesis.asset}`;
}

function uniqueAssetCount(theses) {
  return new Set(theses.map(thesisKey).filter(Boolean)).size;
}

function normalizeMarketThesis(thesis, index, now) {
  const asset = cleanText(coalesce(thesis.instrument, thesis.asset, thesis.symbol, `Tese ${index + 1}`));
  const front = frontLabel(frontIdForInstrument(asset));
  const direction = normalizeDirection(coalesce(thesis.direction, thesis.side, "Alta"));
  const entryPrice = toNumber(coalesce(thesis.entry_price, thesis.entryPrice, thesis.entry), 0);
  const currentPrice = toNumber(
    coalesce(thesis.latest_price, thesis.latestPrice, thesis.latest_event_price, thesis.current_price, thesis.currentPrice, thesis.current, entryPrice),
    entryPrice,
  );
  const targetPrice = toNumber(coalesce(thesis.target_price, thesis.targetPrice, thesis.target), 0);
  const openedAt = toIsoDate(coalesce(thesis.thesis_raised_at, thesis.opened_at, thesis.openedAt, thesis.created_at), now);
  const operation = cleanText(coalesce(normalizeSuggestedOperation(thesis.suggested_operation), normalizeSuggestedOperation(thesis.suggestedOperation), thesis.operation, thesis.plan, "Operação com entrada, alvo e stop definidos."));
  const priceReferenceLabel = priceReferenceLabelFor(direction, thesis.thesis_id, thesis.id, operation);
  const rangeBounds = priceReferenceLabel === "Faixa"
    ? rangeBoundsFor({
        entryPrice,
        targetPrice,
        stopPrice: toNumber(coalesce(thesis.stop_price, thesis.stopPrice, thesis.stop), 0),
        rangeLowerPrice: coalesce(thesis.range_lower_price, thesis.rangeLowerPrice),
        rangeUpperPrice: coalesce(thesis.range_upper_price, thesis.rangeUpperPrice),
      })
    : { rangeLowerPrice: null, rangeUpperPrice: null };

  return {
    id: cleanText(coalesce(thesis.id, thesis.thesis_id, `${asset}-${index + 1}`)),
    front,
    asset,
    direction,
    hypothesis: normalizeHypothesis(thesis, direction),
    evidence: normalizeEvidence(coalesce(thesis.why_thesis, thesis.evidence, thesis.evidence_items, thesis.signals)),
    entryPrice,
    currentPrice,
    targetPrice,
    stopPrice: toNumber(coalesce(thesis.stop_price, thesis.stopPrice, thesis.stop), 0),
    rangeLowerPrice: rangeBounds.rangeLowerPrice,
    rangeUpperPrice: rangeBounds.rangeUpperPrice,
    priceReferenceLabel,
    expectedPct: toNumber(coalesce(thesis.expected_financial_pct, thesis.expectedFinancialPct, thesis.expected_pct, thesis.expectedPct, thesis.expected_return_pct), pctBetween(entryPrice, targetPrice)),
    currentPct: toNumber(coalesce(thesis.unrealized_financial_pct, thesis.unrealizedFinancialPct, thesis.current_pct, thesis.currentPct, thesis.return_pct), pctBetween(entryPrice, currentPrice)),
    daysOpen: daysBetween(openedAt, now),
    hoursOpen: hoursBetween(openedAt, now),
    openedAt,
    status: normalizeStatus(coalesce(thesis.monitor_status, thesis.monitorStatus, thesis.status)),
    learning: cleanText(coalesce(thesis.learning_signal, thesis.learningSignal, thesis.learning, thesis.learning_note, "Registrar aprendizado após validação da tese.")),
    janeState: cleanText(coalesce(thesis.jane_state, thesis.janeState, "monitoring")),
    janeMessage: cleanText(coalesce(thesis.revaluation_reason, thesis.revaluationReason, thesis.jane_message, thesis.janeMessage, "Patrick Jane acompanha as evidências da tese.")),
    operation,
    invalidation: cleanText(coalesce(thesis.next_trigger, thesis.nextTrigger, thesis.invalidation, thesis.invalidation_rule, "Invalidar se as premissas principais deixarem de valer.")),
    sourceAvailability: sourceAvailabilityFor(thesis, front),
  };
}

function normalizeRealEstateCandidate(candidate, index, now) {
  const asset = cleanText(coalesce(candidate.title, candidate.name, candidate.instrument, candidate.asset, `Imóvel ${index + 1}`));
  const entryPrice = toNumber(coalesce(candidate.entry_price, candidate.entryPrice, candidate.asking_price, candidate.askingPrice, candidate.ask_price, candidate.price), 0);
  const currentPrice = toNumber(coalesce(candidate.current_price, candidate.currentPrice, entryPrice), entryPrice);
  const targetPrice = toNumber(coalesce(candidate.target_price, candidate.targetPrice, candidate.target_value, candidate.estimated_sale_base), 0);
  const openedAt = toIsoDate(coalesce(candidate.candidate_date, candidate.date, candidate.created_at, candidate.thesis_raised_at), now);
  const expectedPct = toNumber(coalesce(candidate.expected_pct, candidate.expectedPct), pctBetween(entryPrice, targetPrice));
  const rawAnalysis = candidate.real_estate_analysis ?? candidate.realEstateAnalysis ?? candidate.analysis ?? null;
  const analysisCandidate = rawAnalysis && typeof rawAnalysis === "object"
    ? coalesce(rawAnalysis.candidate, rawAnalysis.candidate_snapshot, rawAnalysis.candidateSnapshot, {})
    : {};
  const valuationEvidence = rawAnalysis && typeof rawAnalysis === "object"
    ? coalesce(rawAnalysis.valuation_evidence, rawAnalysis.valuationEvidence, {})
    : {};
  const saleComparables = [
    ...asArray(coalesce(candidate.sale_comparables, candidate.saleComparables)),
    ...asArray(coalesce(analysisCandidate.sale_comparables, analysisCandidate.saleComparables)),
    ...asArray(coalesce(rawAnalysis?.sale_comparables, rawAnalysis?.saleComparables)),
    ...asArray(coalesce(valuationEvidence.sale_comparables, valuationEvidence.saleComparables, valuationEvidence.comparables)),
  ];
  const origin = cleanText(coalesce(candidate.origin, candidate.source_origin, candidate.sourceOrigin, analysisCandidate.origin));
  const strategy = cleanText(coalesce(candidate.strategy, analysisCandidate.strategy));
  const propertyType = cleanText(coalesce(candidate.property_type, candidate.propertyType, analysisCandidate.property_type, analysisCandidate.propertyType));
  const sourceUrl = cleanText(coalesce(candidate.source_url, candidate.sourceUrl, analysisCandidate.source_url, analysisCandidate.sourceUrl));
  const sourceValidation = coalesce(
    candidate.source_validation,
    candidate.sourceValidation,
    rawAnalysis?.source_validation,
    rawAnalysis?.sourceValidation,
    analysisCandidate.source_validation,
    analysisCandidate.sourceValidation,
    {},
  );
  const candidateSnapshot = {
    ...(analysisCandidate && typeof analysisCandidate === "object" ? analysisCandidate : {}),
    title: cleanText(coalesce(analysisCandidate.title, candidate.title, candidate.name, asset)),
    city: cleanText(coalesce(analysisCandidate.city, analysisCandidate.cidade, candidate.city, candidate.cidade, candidate.municipality, candidate.municipio)),
    neighborhood: cleanText(coalesce(analysisCandidate.neighborhood, analysisCandidate.neighborhoods, analysisCandidate.bairro, analysisCandidate.district, candidate.neighborhood, candidate.neighborhoods, candidate.bairro, candidate.district)),
    street: cleanText(coalesce(analysisCandidate.street, analysisCandidate.street_name, analysisCandidate.streetName, analysisCandidate.rua, candidate.street, candidate.street_name, candidate.streetName, candidate.rua)),
    address: cleanText(coalesce(analysisCandidate.address, analysisCandidate.endereco, candidate.address, candidate.endereco)),
    origin,
    strategy,
    source_url: sourceUrl,
    source_validation: sourceValidation,
    source_validation_status: cleanText(coalesce(candidate.source_validation_status, candidate.sourceValidationStatus, analysisCandidate.source_validation_status, analysisCandidate.sourceValidationStatus)),
    source_validation_reason: cleanText(coalesce(candidate.source_validation_reason, candidate.sourceValidationReason, analysisCandidate.source_validation_reason, analysisCandidate.sourceValidationReason)),
    source_checked_at: cleanText(coalesce(candidate.source_checked_at, candidate.sourceCheckedAt, analysisCandidate.source_checked_at, analysisCandidate.sourceCheckedAt)),
    asking_price: toNumber(coalesce(analysisCandidate.asking_price, analysisCandidate.askingPrice, analysisCandidate.ask_price, candidate.asking_price, candidate.askingPrice, candidate.ask_price, candidate.entry_price, candidate.entryPrice, entryPrice), null),
    ask_price: toNumber(coalesce(analysisCandidate.ask_price, analysisCandidate.askPrice, candidate.ask_price, candidate.askPrice, candidate.asking_price, candidate.askingPrice, entryPrice), null),
    market_value_estimate: toNumber(coalesce(analysisCandidate.market_value_estimate, analysisCandidate.marketValueEstimate, candidate.market_value_estimate, candidate.marketValueEstimate), null),
    estimated_sale_base: toNumber(coalesce(analysisCandidate.estimated_sale_base, analysisCandidate.estimatedSaleBase, candidate.estimated_sale_base, candidate.estimatedSaleBase, targetPrice), null),
    occupancy_status: cleanText(coalesce(analysisCandidate.occupancy_status, analysisCandidate.occupancyStatus, analysisCandidate.ocupacao, candidate.occupancy_status, candidate.occupancyStatus, candidate.ocupacao)),
    legal_plan: cleanText(coalesce(analysisCandidate.legal_plan, analysisCandidate.legalPlan, candidate.legal_plan, candidate.legalPlan)),
    property_type: propertyType,
    private_area_m2: toNumber(coalesce(candidate.private_area_m2, candidate.privateAreaM2, analysisCandidate.private_area_m2, analysisCandidate.privateAreaM2), null),
    bedrooms: toNumber(coalesce(candidate.bedrooms, analysisCandidate.bedrooms), null),
    parking_spaces: toNumber(coalesce(candidate.parking_spaces, candidate.parkingSpaces, analysisCandidate.parking_spaces, analysisCandidate.parkingSpaces), null),
    acquisition_costs: toNumber(coalesce(candidate.acquisition_costs, candidate.acquisitionCosts, analysisCandidate.acquisition_costs, analysisCandidate.acquisitionCosts), null),
    carrying_months: toNumber(coalesce(candidate.carrying_months, candidate.carryingMonths, analysisCandidate.carrying_months, analysisCandidate.carryingMonths), null),
    monthly_carrying_cost: toNumber(coalesce(candidate.monthly_carrying_cost, candidate.monthlyCarryingCost, analysisCandidate.monthly_carrying_cost, analysisCandidate.monthlyCarryingCost), null),
    selling_commission_pct: toNumber(coalesce(candidate.selling_commission_pct, candidate.sellingCommissionPct, analysisCandidate.selling_commission_pct, analysisCandidate.sellingCommissionPct), null),
    sale_comparables_count: toNumber(coalesce(candidate.sale_comparables_count, candidate.saleComparablesCount, analysisCandidate.sale_comparables_count, analysisCandidate.saleComparablesCount), null),
    sale_comparables: saleComparables,
  };
  const realEstateAnalysis = rawAnalysis && typeof rawAnalysis === "object"
    ? { ...rawAnalysis, source_validation: sourceValidation, candidate: candidateSnapshot }
    : rawAnalysis;

  return {
    id: cleanText(coalesce(candidate.id, candidate.candidate_id, `IM-${index + 1}`)),
    thesisId: cleanText(coalesce(candidate.thesis_id, candidate.thesisId, candidate.id ? `IM-RADAR-${candidate.id}` : `IM-${index + 1}`)),
    front: "Imóveis",
    asset,
    direction: expectedPct > 0 ? "Potencial positivo" : "Revisar",
    hypothesis: cleanText(coalesce(candidate.hypothesis, candidate.thesis, candidate.summary, "Candidato imobiliário em análise.")),
    evidence: normalizeEvidence(coalesce(candidate.evidence, candidate.evidence_items, candidate.signals)),
    entryPrice,
    currentPrice,
    targetPrice,
    stopPrice: toNumber(coalesce(candidate.stop_price, candidate.stopPrice, candidate.floor_price), 0),
    expectedPct,
    currentPct: toNumber(coalesce(candidate.current_pct, candidate.currentPct), pctBetween(entryPrice, currentPrice)),
    daysOpen: daysBetween(openedAt, now),
    openedAt,
    status: normalizeStatus(candidate.status),
    learning: cleanText(coalesce(candidate.learning, candidate.learning_note, "Registrar aprendizado da diligência imobiliária.")),
    janeState: cleanText(coalesce(candidate.jane_state, candidate.janeState, "analysis")),
    janeMessage: cleanText(coalesce(candidate.jane_message, candidate.janeMessage, "Patrick Jane compara premissas, preço e risco de execução.")),
    operation: cleanText(coalesce(candidate.operation, candidate.plan, strategy, "Análise imobiliária com preço, margem de segurança e gatilhos definidos.")),
    structure: [strategy, origin, propertyType].filter(Boolean).join(" | "),
    invalidation: cleanText(coalesce(candidate.discard_reason, candidate.invalidation, candidate.invalidation_rule, "Invalidar se diligência ou liquidez quebrarem a tese.")),
    sourceUrl,
    sourceOrigin: origin,
    strategy,
    saleComparables,
    realEstateAnalysis,
    canDiscard: true,
  };
}

function normalizeRealEstateSearchBrief(brief, index) {
  return {
    id: cleanText(coalesce(brief.id, brief.brief_id, `IM-BUSCA-${index + 1}`)),
    type: cleanText(coalesce(brief.type, brief.brief_type)),
    trustLevel: cleanText(coalesce(brief.trustLevel, brief.trust_level, "hypothesis")),
    territoryId: cleanText(coalesce(brief.territoryId, brief.territory_id)),
    territoryLabel: cleanText(coalesce(brief.territoryLabel, brief.territory_label)),
    neighborhoods: asArray(coalesce(brief.neighborhoods, brief.neighborhoodLabels)).map(cleanText).filter(Boolean),
    strategyId: cleanText(coalesce(brief.strategyId, brief.strategy_id)),
    strategyLabel: cleanText(coalesce(brief.strategyLabel, brief.strategy_label)),
    title: cleanText(coalesce(brief.title, brief.label, `Brief imobiliário ${index + 1}`)),
    assetProfile: cleanText(coalesce(brief.assetProfile, brief.asset_profile)),
    territoryThesis: cleanText(coalesce(brief.territoryThesis, brief.territory_thesis)),
    targetDiscountPct: toNumber(coalesce(brief.targetDiscountPct, brief.target_discount_pct), null),
    targetRoiPct: toNumber(coalesce(brief.targetRoiPct, brief.target_roi_pct), null),
    renovationProfile: cleanText(coalesce(brief.renovationProfile, brief.renovation_profile)),
    sourceName: cleanText(coalesce(brief.sourceName, brief.source_name)),
    sourceUrl: cleanText(coalesce(brief.sourceUrl, brief.source_url)),
    sourceSummary: cleanText(coalesce(brief.sourceSummary, brief.source_summary)),
    candidateAngle: cleanText(coalesce(brief.candidateAngle, brief.candidate_angle)),
    decisionRule: cleanText(coalesce(brief.decisionRule, brief.decision_rule)),
    nextSearchQueries: asArray(coalesce(brief.nextSearchQueries, brief.next_search_queries)).map(cleanText).filter(Boolean),
    diligenceChecklist: asArray(coalesce(brief.diligenceChecklist, brief.diligence_checklist)).map(cleanText).filter(Boolean),
  };
}

function normalizeAuctioneerDirectory(directory, index) {
  return {
    id: cleanText(coalesce(directory.id, directory.source_id, `auctioneer-${index + 1}`)),
    uf: cleanText(coalesce(directory.uf, directory.state)),
    sourceName: cleanText(coalesce(directory.sourceName, directory.source_name, directory.name, `Diretorio oficial ${index + 1}`)),
    sourceUrl: cleanText(coalesce(directory.sourceUrl, directory.source_url, directory.url)),
    contactPath: cleanText(coalesce(directory.contactPath, directory.contact_path)),
    contactStrategy: cleanText(coalesce(directory.contactStrategy, directory.contact_strategy)),
    visibilityTier: cleanText(coalesce(directory.visibilityTier, directory.visibility_tier)),
    relationshipStage: cleanText(coalesce(directory.relationshipStage, directory.relationship_stage)),
    qualityFilter: asArray(coalesce(directory.qualityFilter, directory.quality_filter)).map(cleanText).filter(Boolean),
    nextAction: cleanText(coalesce(directory.nextAction, directory.next_action)),
    trustLevel: cleanText(coalesce(directory.trustLevel, directory.trust_level)),
  };
}

function normalizeAuctioneerPhones(value) {
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean);
  return cleanText(value)
    .split(/[|;,]/)
    .map(cleanText)
    .filter(Boolean);
}

function normalizeAuctioneerContact(contact, index) {
  return {
    id: cleanText(coalesce(contact.id, contact.contact_id, `auctioneer-contact-${index + 1}`)),
    name: cleanText(coalesce(contact.name, contact.nome, `Leiloeiro ${index + 1}`)),
    registration: cleanText(coalesce(contact.registration, contact.matricula)),
    city: cleanText(coalesce(contact.city, contact.cidade)),
    neighborhood: cleanText(coalesce(contact.neighborhood, contact.bairro)),
    phones: normalizeAuctioneerPhones(coalesce(contact.phones, contact.telefones, contact.phone)),
    email: cleanText(coalesce(contact.email, contact.e_mail)),
    website: cleanText(coalesce(contact.website, contact.site, contact.web_site)),
    status: cleanText(coalesce(contact.status, contact.situacao)),
    sourceUrl: cleanText(coalesce(contact.sourceUrl, contact.source_url)),
    competitionTier: cleanText(coalesce(contact.competitionTier, contact.competition_tier, "validar")),
    competitionReason: cleanText(coalesce(contact.competitionReason, contact.competition_reason)),
    relationshipStage: cleanText(coalesce(contact.relationshipStage, contact.relationship_stage)),
    contactStrategy: cleanText(coalesce(contact.contactStrategy, contact.contact_strategy)),
    outreachStatus: cleanText(coalesce(contact.outreachStatus, contact.outreach_status)),
    outreachChannel: cleanText(coalesce(contact.outreachChannel, contact.outreach_channel)),
    outreachSentAt: cleanText(coalesce(contact.outreachSentAt, contact.outreach_sent_at)),
    nextFollowUpAt: cleanText(coalesce(contact.nextFollowUpAt, contact.next_follow_up_at)),
    responseReceivedAt: cleanText(coalesce(contact.responseReceivedAt, contact.response_received_at)),
    responseSummary: cleanText(coalesce(contact.responseSummary, contact.response_summary)),
    outreachNote: cleanText(coalesce(contact.outreachNote, contact.outreach_note)),
    trustLevel: cleanText(coalesce(contact.trustLevel, contact.trust_level)),
  };
}

function normalizeAuctioneerPlaybookStep(step, index) {
  return {
    id: cleanText(coalesce(step.id, step.stage, `auctioneer-playbook-${index + 1}`)),
    stage: cleanText(coalesce(step.stage, step.title, `Etapa ${index + 1}`)),
    action: cleanText(coalesce(step.action, step.objective, step.next_action)),
  };
}

function normalizeAuctioneerSourcing(payload = {}) {
  const summary = payload.summary ?? {};
  const officialDirectories = asArray(coalesce(
    payload.officialDirectories,
    payload.official_directories,
  )).map(normalizeAuctioneerDirectory);
  const officialContacts = asArray(coalesce(
    payload.officialContacts,
    payload.official_contacts,
  )).map(normalizeAuctioneerContact);
  const outreachPlaybook = asArray(coalesce(
    payload.outreachPlaybook,
    payload.outreach_playbook,
  )).map(normalizeAuctioneerPlaybookStep);
  const scoringModel = payload.scoringModel ?? payload.scoring_model ?? {};

  return {
    summary: {
      officialDirectoryCount: toNumber(
        coalesce(summary.officialDirectoryCount, summary.official_directory_count),
        officialDirectories.length,
      ),
      officialContactCount: toNumber(
        coalesce(summary.officialContactCount, summary.official_contact_count),
        officialContacts.length,
      ),
      longTailDirectoryCount: toNumber(
        coalesce(summary.longTailDirectoryCount, summary.long_tail_directory_count),
        officialDirectories.filter((directory) => directory.visibilityTier === "cauda_longa").length,
      ),
      contactSourceCount: toNumber(
        coalesce(summary.contactSourceCount, summary.contact_source_count),
        officialDirectories.filter((directory) => directory.contactPath).length,
      ),
      outreachSentCount: toNumber(
        coalesce(summary.outreachSentCount, summary.outreach_sent_count),
        officialContacts.filter((contact) => contact.outreachSentAt).length,
      ),
      outreachResponseCount: toNumber(
        coalesce(summary.outreachResponseCount, summary.outreach_response_count),
        officialContacts.filter((contact) => contact.responseReceivedAt).length,
      ),
      outreachNoRealEstateCount: toNumber(
        coalesce(summary.outreachNoRealEstateCount, summary.outreach_no_real_estate_count),
        officialContacts.filter((contact) => contact.outreachStatus === "respondido_sem_imoveis").length,
      ),
      outreachPendingResponseCount: toNumber(
        coalesce(summary.outreachPendingResponseCount, summary.outreach_pending_response_count),
        officialContacts.filter((contact) => contact.outreachStatus === "enviado").length,
      ),
      nextFollowUpAt: cleanText(coalesce(summary.nextFollowUpAt, summary.next_follow_up_at)),
      scopeCities: asArray(coalesce(summary.scopeCities, summary.scope_cities)).map(cleanText).filter(Boolean),
      competitionTierCounts: coalesce(summary.competitionTierCounts, summary.competition_tier_counts, {}),
      actionability: cleanText(summary.actionability),
    },
    officialDirectories,
    officialContacts,
    outreachPlaybook,
    scoringModel: {
      lowCompetitionSignals: asArray(coalesce(
        scoringModel.lowCompetitionSignals,
        scoringModel.low_competition_signals,
      )).map(cleanText).filter(Boolean),
      qualitySignals: asArray(coalesce(
        scoringModel.qualitySignals,
        scoringModel.quality_signals,
      )).map(cleanText).filter(Boolean),
    },
  };
}

function normalizeRealEstateStrategyTerritoryCandidates(payload = {}) {
  const summary = payload.summary ?? {};
  const matrixBriefs = asArray(coalesce(payload.matrixBriefs, payload.matrix_briefs)).map(normalizeRealEstateSearchBrief);
  const strategyCandidateWatchlist = asArray(coalesce(
    payload.strategyCandidateWatchlist,
    payload.strategy_candidate_watchlist,
  )).map(normalizeRealEstateSearchBrief);
  const condominiumRequalificationWatchlist = asArray(coalesce(
    payload.condominiumRequalificationWatchlist,
    payload.condominium_requalification_watchlist,
  )).map(normalizeRealEstateSearchBrief);
  const auctioneerSourcing = normalizeAuctioneerSourcing(coalesce(
    payload.auctioneerSourcing,
    payload.auctioneer_sourcing,
    {},
  ));

  return {
    generatedAt: toOptionalIsoDate(coalesce(payload.generatedAt, payload.generated_at)),
    summary: {
      strategyCount: toNumber(coalesce(summary.strategyCount, summary.strategy_count), 0),
      territoryCount: toNumber(coalesce(summary.territoryCount, summary.territory_count), 0),
      matrixBriefCount: toNumber(coalesce(summary.matrixBriefCount, summary.matrix_brief_count), matrixBriefs.length),
      sourceCandidateCount: toNumber(
        coalesce(summary.sourceCandidateCount, summary.source_candidate_count),
        strategyCandidateWatchlist.length,
      ),
      sourceConfirmedRequalificationCount: toNumber(
        coalesce(summary.sourceConfirmedRequalificationCount, summary.source_confirmed_requalification_count),
        condominiumRequalificationWatchlist.length,
      ),
      auctioneerDirectoryCount: toNumber(
        coalesce(summary.auctioneerDirectoryCount, summary.auctioneer_directory_count),
        auctioneerSourcing.summary.officialDirectoryCount,
      ),
      auctioneerContactCount: toNumber(
        coalesce(summary.auctioneerContactCount, summary.auctioneer_contact_count),
        auctioneerSourcing.summary.officialContactCount,
      ),
      actionability: cleanText(summary.actionability),
    },
    strategies: asArray(payload.strategies),
    territories: asArray(payload.territories),
    matrixBriefs,
    strategyCandidateWatchlist,
    condominiumRequalificationWatchlist,
    auctioneerSourcing,
  };
}

function learningNotesFrom(payloads) {
  const activityNotes = [
    ...learningActivityNotesFrom(payloads?.currentMonitor),
    ...learningActivityNotesFrom(payloads?.dashboardSummary),
  ];
  const explicitNotes = [
    ...activityNotes,
    ...asArray(payloads?.dashboardSummary?.learning_notes),
    ...asArray(payloads?.dashboardSummary?.learningNotes),
    ...asArray(payloads?.currentMonitor?.learning_notes),
    ...asArray(payloads?.currentMonitor?.learningNotes),
    ...asArray(payloads?.realEstateCandidates?.learning_notes),
    ...asArray(payloads?.realEstateCandidates?.learningNotes),
  ];

  if (explicitNotes.length > 0) return explicitNotes;

  return asArray(payloads?.dashboardSummary?.thesis_open_operations)
    .filter((row) => cleanText(row.learning_note))
    .slice(-18)
    .map((row) => {
      const result = toNumber(row.moment_result_pct, 0);
      const expected = toNumber(row.expected_result_pct, 0);
      const outcome = cleanText(row.outcome).toLowerCase();
      const pain = outcome.includes("stop")
        ? `Tese ${row.thesis_number || ""} acionou proteção antes do alvo.`
        : result < expected
          ? `Tese ${row.thesis_number || ""} ficou abaixo do retorno esperado.`
          : `Tese ${row.thesis_number || ""} confirmou um padrão que pode ser reaplicado.`;

      return {
        pain,
        remedy: cleanText(row.learning_note),
        expected_impact: "Aplicar a lição nas próximas escolhas de tese, operação e gatilho de saída.",
        applied_to: [cleanText(row.action)].filter(Boolean),
        evidence_count: 1,
      };
    });
}

function learningActivityNotesFrom(payload) {
  const activity = payload?.learning_activity ?? payload?.learningActivity;
  if (!activity || typeof activity !== "object") return [];

  const lessons = asArray(activity.lessons);
  const rules = asArray(activity.candidate_rules ?? activity.candidateRules);
  const kpis = activity.kpis && typeof activity.kpis === "object" ? activity.kpis : {};

  return lessons.map((lesson, index) => {
    const area = cleanText(lesson.area || `Área ${index + 1}`);
    const ruleId = cleanText(lesson.candidate_rule ?? lesson.candidateRule);
    const rule = rules.find((candidate) => cleanText(candidate.rule_id ?? candidate.ruleId) === ruleId) ?? {};
    const impacted = asArray(lesson.impacted_instruments ?? lesson.impactedInstruments).map(cleanText).filter(Boolean);
    const evidence = asArray(lesson.evidence).map(cleanText).filter(Boolean);
    const evidenceCount = Math.max(
      evidence.length,
      toNumber(kpis.unique_news_events_count, 0),
      impacted.length > 0 ? 1 : 0,
    );

    return {
      pain: cleanText(`Aprendizado semanal (${area}): ${lesson.lesson || "notícia relevante mudou a leitura da tese."}`),
      remedy: cleanText(rule.action || ruleId || "Registrar a lição como regra candidata antes da próxima tese."),
      expected_impact: cleanText(
        rule.trigger
          ? `Quando ${rule.trigger}, aplicar a regra em shadow e medir acerto nas próximas teses.`
          : "Aumentar qualidade das próximas teses ao transformar notícia em critério mensurável.",
      ),
      applied_to: impacted,
      evidence_count: evidenceCount,
    };
  });
}

function normalizeLearningLoop(note, index) {
  return {
    pain: cleanText(coalesce(note.pain, note.problem, `Dor observada ${index + 1}: tese precisa de evidência mais objetiva.`)),
    remedy: cleanText(coalesce(note.remedy, note.action, `Remédio aplicado ${index + 1}: explicitar gatilho antes do go-live.`)),
    expectedImpact: cleanText(coalesce(note.expected_impact, note.expectedImpact, note.impact, "Aumentar consistência das próximas decisões monitoradas.")),
    appliedTo: Array.isArray(note.applied_to) ? note.applied_to.map(cleanText) : asArray(note.appliedTo).map(cleanText),
    evidenceCount: toNumber(coalesce(note.evidence_count, note.evidenceCount), 0),
  };
}

function frontOverviewFor(dashboardSummary, id) {
  const overview = dashboardSummary?.front_overview ?? dashboardSummary?.frontOverview ?? {};
  return overview[id] ?? overview[id.replace("_", "")] ?? {};
}

function derivedFrontStats(front, thesisRows, dashboardSummary) {
  const rows = asArray(thesisRows).filter((row) => row.front === front.label);
  const resolvedRows = rows.filter((row) => row.statusGroup === "Histórica" && Number.isFinite(Number(row.resultPct)));
  const successRows = resolvedRows.filter((row) => Number(row.resultPct) >= 0);
  const globalHistory = dashboardSummary?.thesis_history_overview ?? {};
  const globalValidated = toNumber(coalesce(globalHistory.success_rate_pct, globalHistory.successRatePct), null);

  return {
    tested: rows.length > 0 ? rows.length : null,
    validatedPct: resolvedRows.length > 0
      ? (successRows.length / resolvedRows.length) * 100
      : rows.length > 0
        ? globalValidated
        : null,
  };
}

function metricText(value) {
  return cleanText(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function isOpenRealEstateMetricRow(row) {
  if (row?.isOpen === false || row?.is_open === false) return false;
  const status = metricText(`${row?.statusGroup || ""} ${row?.status || ""} ${row?.phase || ""}`);
  if (
    status.includes("histor")
    || status.includes("fechad")
    || status.includes("descart")
    || status.includes("encerr")
  ) {
    return false;
  }
  return row?.isOpen === true
    || row?.is_open === true
    || status.includes("go-live")
    || status.includes("abert")
    || status.includes("pendenc")
    || status.includes("analise")
    || status.includes("observ")
    || status.includes("monitor");
}

function realEstateMetricKey(row, index) {
  const thesisId = cleanText(coalesce(row?.thesisId, row?.thesis_id));
  if (thesisId) return `thesis:${thesisId.toUpperCase()}`;
  const id = cleanText(coalesce(row?.candidateId, row?.candidate_id, row?.id));
  if (id) return `id:${id.toUpperCase()}`;
  const sourceUrl = cleanText(coalesce(row?.sourceUrl, row?.source_url));
  if (sourceUrl) return `source:${sourceUrl.toLowerCase()}`;
  return `row:${index}`;
}

function realEstateP0Count(row) {
  const analysis = row?.realEstateAnalysis || row?.real_estate_analysis || {};
  return asArray(coalesce(analysis.pending_items, analysis.pendingItems)).filter((item) => (
    cleanText(coalesce(item?.priority, item?.severity, item?.level)).toUpperCase() === "P0"
  )).length;
}

function buildRealEstateStats(thesisRows = [], realEstateCandidates = [], dashboardSummary = {}) {
  const overview = frontOverviewFor(dashboardSummary, "real_estate");
  const rowsByKey = new Map();
  [...asArray(realEstateCandidates), ...asArray(thesisRows).filter((row) => row.front === "Imóveis")].forEach((row, index) => {
    const key = realEstateMetricKey(row, index);
    if (!rowsByKey.has(key)) rowsByKey.set(key, row);
  });

  const rows = [...rowsByKey.values()];
  const openFromRows = rows.filter(isOpenRealEstateMetricRow).length;
  const closedFromRows = rows.length ? Math.max(rows.length - openFromRows, 0) : null;
  const overviewTotal = toNumber(coalesce(
    overview.radar_total,
    overview.radarTotal,
    overview.total_tested,
    overview.totalTested,
    overview.mapped_count,
    overview.mappedCount,
  ), null);
  const overviewOpen = toNumber(coalesce(overview.open_count, overview.openCount), null);
  const overviewClosed = toNumber(coalesce(overview.closed_count, overview.closedCount, overview.resolved_count, overview.resolvedCount), null);
  const overviewP0 = toNumber(coalesce(overview.p0_count, overview.p0Count), null);
  const hasOverviewOperationalCounts = overviewOpen !== null || overviewClosed !== null;
  const rowTotal = rows.length || null;
  const totalBase = hasOverviewOperationalCounts || !rowTotal
    ? coalesce(overviewTotal, rowTotal, 0)
    : rowTotal;
  const openCount = coalesce(overviewOpen, openFromRows, 0);
  const closedCount = coalesce(
    overviewClosed,
    closedFromRows,
    Math.max(Number(totalBase || 0) - Number(openCount || 0), 0),
  );
  const total = Math.max(
    toNumber(totalBase, 0),
    toNumber(openCount, 0) + toNumber(closedCount, 0),
  );

  return {
    total,
    openCount: toNumber(openCount, 0),
    closedCount: toNumber(closedCount, 0),
    p0Count: overviewP0 ?? rows.reduce((sum, row) => sum + realEstateP0Count(row), 0),
    source: hasOverviewOperationalCounts ? "front_overview" : "canonical_rows",
  };
}

function buildFronts(dashboardSummary, goLiveTheses, now, thesisRows = [], realEstateStats = null) {
  return FRONT_DEFS.map((front) => {
    const overview = frontOverviewFor(dashboardSummary, front.id);
    const derived = derivedFrontStats(front, thesisRows, dashboardSummary);
    const goLive = goLiveTheses.filter((thesis) => thesis.front === front.label).length;
    const activeAssets = uniqueAssetCount(goLiveTheses.filter((thesis) => thesis.front === front.label));
    const isRealEstate = front.id === "real_estate";
    const tested = coalesce(overview.total_tested, overview.tested, overview.totalTested, derived.tested);
    const resolvedCount = coalesce(overview.resolved_count, overview.resolvedCount, tested);
    const mappedCount = coalesce(overview.mapped_count, overview.mappedCount, resolvedCount);
    const countingPolicy = cleanText(coalesce(overview.counting_policy, overview.countingPolicy));
    const validatedPct = coalesce(
      overview.success_rate_pct,
      overview.validated_pct,
      overview.validatedPct,
      derived.validatedPct,
    );
    const realEstateOpenCount = toNumber(coalesce(realEstateStats?.openCount, overview.open_count, overview.openCount, goLive), goLive);
    const frontGoLive = isRealEstate ? realEstateOpenCount : goLive;

    return {
      id: front.id,
      label: front.label,
      tested: isRealEstate ? toNumber(coalesce(realEstateStats?.total, tested), null) : toNumber(tested, null),
      resolvedCount: isRealEstate ? toNumber(coalesce(realEstateStats?.closedCount, resolvedCount), null) : toNumber(resolvedCount, null),
      mappedCount: isRealEstate ? toNumber(coalesce(realEstateStats?.total, mappedCount), null) : toNumber(mappedCount, null),
      radarTotal: isRealEstate ? toNumber(coalesce(realEstateStats?.total, overview.radar_total, overview.radarTotal, mappedCount), null) : null,
      openCount: isRealEstate ? toNumber(coalesce(realEstateStats?.openCount, overview.open_count, overview.openCount, goLive), null) : null,
      closedCount: isRealEstate ? toNumber(coalesce(realEstateStats?.closedCount, overview.closed_count, overview.closedCount, resolvedCount), null) : null,
      p0Count: isRealEstate ? toNumber(coalesce(realEstateStats?.p0Count, overview.p0_count, overview.p0Count), 0) : null,
      countingPolicy: isRealEstate ? "radar_candidates" : countingPolicy,
      goLive: frontGoLive,
      activeAssets,
      validatedPct: toNumber(validatedPct, null),
      status: frontGoLive > 0 ? "atualizado" : "sem sinal",
      lastUpdatedAt: toIsoDate(coalesce(overview.updated_at, dashboardSummary?.updated_at, dashboardSummary?.last_updated_at), now),
    };
  });
}

function normalizeExecutiveSummary(dashboardSummary, scientificSummary) {
  const executive = dashboardSummary?.thesis_executive_summary ?? dashboardSummary?.thesisExecutiveSummary ?? {};
  const historical = executive.historical ?? dashboardSummary?.historical_analysis_summary ?? {};
  const current = executive.current ?? dashboardSummary?.current_simulation_summary ?? {};

  return {
    historical: {
      label: cleanText(coalesce(historical.period_label, "histórico acumulado")),
      thesisCount: toNumber(coalesce(historical.thesis_count, historical.backtest_runs), scientificSummary.testedTheses),
      expectedPct: toNumber(coalesce(historical.expected_pct, historical.avg_expected_pct), 0),
      achievedPct: toNumber(coalesce(historical.achieved_pct, historical.avg_return_pct, historical.avg_result_pct), scientificSummary.expectancyPct),
      approvedCount: toNumber(coalesce(historical.approved_count, historical.success_count), 0),
    },
    current: {
      label: cleanText(coalesce(current.period_label, "desde o go-live")),
      thesisCount: toNumber(coalesce(current.thesis_count, current.paper_orders), scientificSummary.goLiveCount),
      expectedPct: toNumber(coalesce(current.expected_pct, current.avg_expected_pct), 0),
      achievedPct: toNumber(coalesce(current.achieved_pct, current.avg_backtest_return_pct, current.avg_return_pct), 0),
      approvedCount: toNumber(coalesce(current.approved_count, current.target_hits), 0),
    },
  };
}

function buildAccuracyCycles(dashboardSummary, scientificSummary) {
  const rawCycles = asArray(dashboardSummary?.calibration_cycles ?? dashboardSummary?.calibrationCycles);
  if (rawCycles.length > 0) {
    const normalized = rawCycles
      .map((cycle, index) => {
        const ciclo = cleanText(coalesce(cycle.ciclo, cycle.label, cycle.name, `Cal.${String(index + 8).padStart(2, "0")}`));
        return {
          ciclo,
          taxa: toNumber(coalesce(cycle.taxa, cycle.accuracy_pct, cycle.success_rate_pct, cycle.value), 0),
          sortOrder: calibrationCycleOrder(ciclo, index),
          sourceOrder: index,
        };
      })
      .sort((a, b) => a.sortOrder - b.sortOrder || a.sourceOrder - b.sourceOrder)
      .slice(-11)
      .map(({ sortOrder, sourceOrder, ...cycle }) => cycle);
    if (normalized.length === 11) return normalized;
  }

  const end = toNumber(scientificSummary.validatedPct, 67.52);
  const start = Math.max(55, end - 12.52);
  return Array.from({ length: 11 }, (_, index) => {
    const value = index === 10 ? end : start + ((end - start) * index) / 10;
    return {
      ciclo: `Cal.${String(index + 8).padStart(2, "0")}`,
      taxa: Number(value.toFixed(2)),
    };
  });
}

function buildCalibrationRows(dashboardSummary, executiveSummary) {
  const weeks = asArray(dashboardSummary?.thesis_history_overview?.last_3_weeks);
  const rows = weeks
    .filter((week) => toNumber(week.total_tested, 0) > 0)
    .map((week, index) => ({
      id: index + 1,
      data: cleanText(coalesce(week.end_day, week.label, `Calibração ${index + 1}`)),
      teses: toNumber(week.total_tested, 0),
      esperado: executiveSummary.historical.expectedPct,
      alcancado: toNumber(week.avg_result_pct, executiveSummary.historical.achievedPct),
      aprovadas: toNumber(week.success_count, 0),
    }));

  const daily = asArray(dashboardSummary?.current_simulation_daily);
  daily.slice(-3).forEach((day) => {
    rows.push({
      id: rows.length + 1,
      data: cleanText(coalesce(day.day, `Go-live ${rows.length + 1}`)),
      teses: toNumber(coalesce(day.backtest_trades, day.paper_orders), 0),
      esperado: executiveSummary.current.expectedPct,
      alcancado: toNumber(day.avg_backtest_return_pct, executiveSummary.current.achievedPct),
      aprovadas: toNumber(coalesce(day.target_hits, day.approved_count), 0),
    });
  });

  if (rows.length > 0) return rows;

  return [
    {
      id: 1,
      data: "histórico",
      teses: executiveSummary.historical.thesisCount,
      esperado: executiveSummary.historical.expectedPct,
      alcancado: executiveSummary.historical.achievedPct,
      aprovadas: executiveSummary.historical.approvedCount,
    },
    {
      id: 2,
      data: "go-live",
      teses: executiveSummary.current.thesisCount,
      esperado: executiveSummary.current.expectedPct,
      alcancado: executiveSummary.current.achievedPct,
      aprovadas: executiveSummary.current.approvedCount,
    },
  ];
}

function buildLearningStats(scientificSummary, calibrationRows) {
  const first = calibrationRows[0];
  const last = calibrationRows[calibrationRows.length - 1] ?? first;
  const firstGap = first ? first.esperado - first.alcancado : 0;
  const lastGap = last ? last.esperado - last.alcancado : 0;
  const firstRate = first?.teses ? (first.aprovadas / first.teses) * 100 : 0;
  const lastRate = last?.teses ? (last.aprovadas / last.teses) * 100 : scientificSummary.validatedPct;

  return {
    totalLearnings: scientificSummary.appliedLearningsCount,
    gapReducedPp: Number((lastGap - firstGap).toFixed(2)),
    calibrationCount: calibrationRows.length,
    accuracyGainPp: Number((lastRate - firstRate).toFixed(2)),
    gapSeries: calibrationRows.map((row) => ({
      ciclo: cleanText(row.data),
      esperado: row.esperado,
      realizado: row.alcancado,
    })),
  };
}

function buildMarketAssets(dashboardSummary, goLiveTheses) {
  const thesisCounts = goLiveTheses.reduce((acc, thesis) => {
    acc[thesis.asset] = (acc[thesis.asset] ?? 0) + 1;
    return acc;
  }, {});

  const signalsByAsset = asArray(dashboardSummary?.latest_signals).reduce((acc, signal) => {
    const instrument = cleanText(signal.instrument);
    if (instrument) acc[instrument] = signal;
    return acc;
  }, {});

  const rows = asArray(dashboardSummary?.market_coverage?.instruments).map((instrument) => {
    const asset = cleanText(instrument.instrument);
    const signal = signalsByAsset[asset] ?? {};
    const activeThesis = goLiveTheses.find((thesis) => thesis.asset === asset);
    const confidence = toNumber(signal.confidence, null);
    const status = activeThesis ? "monitorando" : confidence && confidence >= 0.9 ? "candidato" : "atenção";

    return {
      asset,
      front: frontLabel(frontIdForInstrument(asset)),
      price: toNumber(instrument.last_price, activeThesis?.currentPrice ?? 0),
      dayPct: toNumber(activeThesis?.currentPct, 0),
      weekPct: toNumber(activeThesis?.expectedPct, 0),
      patterns: Math.max(0, Math.round((confidence ?? 0.5) * 100)),
      status,
      activeTheses: thesisCounts[asset] ?? 0,
      rationale: cleanText(signal.rationale),
    };
  });

  goLiveTheses.forEach((thesis) => {
    if (rows.some((row) => row.asset === thesis.asset)) return;
    rows.push({
      asset: thesis.asset,
      front: thesis.front,
      price: thesis.currentPrice,
      dayPct: thesis.currentPct,
      weekPct: thesis.expectedPct,
      patterns: thesis.evidence.length,
      status: thesis.status === "analysis" ? "candidato" : "monitorando",
      activeTheses: thesisCounts[thesis.asset] ?? 1,
      rationale: thesis.hypothesis,
    });
  });

  return rows;
}

function buildRisk(dashboardSummary, goLiveTheses, thesisRows) {
  const openRows = thesisRows.filter((row) => row.statusGroup === "Go-live");
  const concentration = openRows.reduce((acc, row) => {
    acc[row.asset] = (acc[row.asset] ?? 0) + 1;
    return acc;
  }, {});
  const [mainAsset = "--", mainCount = 0] = Object.entries(concentration).sort((a, b) => b[1] - a[1])[0] ?? [];
  const history = dashboardSummary?.thesis_history_overview ?? {};
  const stopRate = toNumber(history.stop_rate_pct, 0);
  const exposurePct = toNumber(dashboardSummary?.risk_summary?.exposure_pct, Math.min(100, openRows.length * 12));
  const limitPct = toNumber(dashboardSummary?.risk_summary?.limit_pct, 85);

  const alerts = [];
  if (exposurePct >= limitPct - 5) {
    alerts.push({
      title: "Exposição próxima do limite",
      description: `Exposição em ${exposurePct.toFixed(0)}% contra limite de ${limitPct.toFixed(0)}%.`,
      severity: "high",
    });
  }
  if (mainCount > 1) {
    alerts.push({
      title: `Concentração em ${mainAsset}`,
      description: `${mainCount} teses abertas usam o mesmo ativo como principal fonte de risco.`,
      severity: "medium",
    });
  }
  asArray(dashboardSummary?.data_quality_gate?.checks)
    .filter((check) => cleanText(check.status).toLowerCase() === "fail")
    .slice(0, 3)
    .forEach((check) => {
      alerts.push({
        title: cleanText(coalesce(check.label, check.check_id, "Qualidade de dados")),
        description: cleanText(coalesce(check.details, "Check de qualidade exige atenção antes de ampliar risco.")),
        severity: "medium",
      });
    });

  goLiveTheses
    .filter((thesis) => thesis.status === "stop_alert")
    .forEach((thesis) => {
      alerts.unshift({
        title: `${thesis.asset} perto do stop`,
        description: thesis.invalidation,
        severity: "high",
      });
    });

  return {
    exposurePct,
    limitPct,
    mainAsset,
    stopRespectPct: Math.max(0, 100 - stopRate),
    alerts,
  };
}

function eventTypeFrom(eventType) {
  const value = cleanText(eventType).toLowerCase();
  if (value.includes("stop")) return "stop";
  if (value.includes("valid") || value.includes("target")) return "validada";
  if (value.includes("calib") || value.includes("case_study")) return "calibração";
  if (value.includes("current_monitor") || value.includes("pattern") || value.includes("thesis")) return "padrão";
  if (value.includes("risk") || value.includes("kill")) return "concentração";
  return "calibração";
}

function buildAlertFeed(dashboardSummary, goLiveTheses, risk) {
  const feed = [];

  asArray(dashboardSummary?.alert_events).forEach((event) => {
    feed.push({
      icon: "!",
      title: cleanText(coalesce(event.title, event.event_type, "Alerta")),
      description: cleanText(coalesce(event.description, event.details, "Evento registrado pelo laboratório.")),
      time: cleanText(coalesce(event.created_at, event.time, "agora")),
      type: eventTypeFrom(coalesce(event.type, event.event_type)),
    });
  });

  asArray(dashboardSummary?.latest_audit_events).slice(0, 8).forEach((event) => {
    const details = parseJsonObject(event.details);
    const count = toNumber(coalesce(details.thesis_count, details.inserted, details.total), null);
    feed.push({
      icon: "↺",
      title: cleanText(event.event_type || "Evento de calibração"),
      description: count !== null
        ? `Evento processado com ${count} registros relevantes para o laboratório.`
        : cleanText(event.details || "Evento operacional registrado."),
      time: cleanText(event.created_at || "recente"),
      type: eventTypeFrom(event.event_type),
    });
  });

  asArray(dashboardSummary?.kill_switches)
    .filter((item) => cleanText(item.status).toLowerCase() === "active")
    .forEach((item) => {
      feed.unshift({
        icon: "!",
        title: "Kill switch ativo",
        description: cleanText(coalesce(item.reason, "Bloqueio operacional ativo.")),
        time: "agora",
        type: "concentração",
      });
    });

  goLiveTheses.forEach((thesis) => {
    if (thesis.status === "target_hit" || thesis.status === "stop_alert") {
      feed.unshift({
        icon: thesis.status === "target_hit" ? "✓" : "!",
        title: `${thesis.asset} ${statusToUi(thesis.status).label.toLowerCase()}`,
        description: thesis.janeMessage,
        time: thesis.openedAt,
        type: thesis.status === "target_hit" ? "validada" : "stop",
      });
    }
  });

  risk.alerts.slice(0, 3).forEach((alert) => {
    feed.push({
      icon: "◬",
      title: alert.title,
      description: alert.description,
      time: "monitoramento",
      type: alert.severity === "high" ? "stop" : "concentração",
    });
  });

  return feed.slice(0, 12);
}

export function statusToUi(status) {
  return STATUS_UI[status] ?? STATUS_UI.monitoring;
}

export function normalizeCockpitHalley(payloads = {}, now = new Date()) {
  const dashboardSummary = payloads?.dashboardSummary ?? {};
  const monitorTrust = normalizeMonitorTrust(payloads?.currentMonitor);
  const history = dashboardSummary.thesis_history_overview ?? dashboardSummary.thesisHistoryOverview ?? {};
  const historicalAnalysis = dashboardSummary.historical_analysis_summary ?? dashboardSummary.historicalAnalysisSummary ?? {};
  const currentSimulation = dashboardSummary.current_simulation_summary ?? dashboardSummary.currentSimulationSummary ?? {};
  const operationRows = asArray(dashboardSummary?.thesis_open_operations)
    .map((row, index) => normalizeOperationRow(row, index, now));
  const operationActiveTheses = operationRows
    .filter(isActiveOperationRow)
    .map(activeThesisFromRow);
  const operationKeys = new Set(operationActiveTheses.map(thesisKey));
  const marketTheses = asArray(payloads?.currentMonitor?.theses).map((thesis, index) => normalizeMarketThesis(thesis, index, now));
  const supplementalMarketTheses = marketTheses.filter((thesis) => !operationKeys.has(thesisKey(thesis)));
  const goLiveTheses = [...supplementalMarketTheses, ...operationActiveTheses];
  const learningLoops = learningNotesFrom(payloads).map(normalizeLearningLoop).filter((loop) => loop.pain && loop.remedy && loop.expectedImpact);
  const explicitLastUpdatedAt = coalesce(dashboardSummary.updated_at, dashboardSummary.last_updated_at);
  const lastUpdatedAt = explicitLastUpdatedAt ? toIsoDate(explicitLastUpdatedAt, now) : null;
  const appliedLearnings = coalesce(history.applied_learnings_count, history.appliedLearningsCount, dashboardSummary.applied_learnings_count);
  const scientificSummary = {
    testedTheses: toNumber(
      coalesce(
        history.total_tested,
        history.totalTested,
        history.global_total_tested,
        historicalAnalysis.thesis_count,
        historicalAnalysis.backtest_runs,
      ),
      0,
    ),
    validatedPct: toNumber(coalesce(history.success_rate_pct, history.successRatePct, historicalAnalysis.avg_win_rate_pct), 0),
    expectancyPct: toNumber(
      coalesce(
        history.expectancy_net_pct,
        history.expectancyNetPct,
        history.avg_result_pct,
        historicalAnalysis.avg_return_pct,
      ),
      0,
    ),
    goLiveCount: goLiveTheses.length || toNumber(coalesce(currentSimulation.thesis_count, currentSimulation.paper_orders), 0),
    goLiveAssetCount: uniqueAssetCount(goLiveTheses),
    appliedLearningsCount: toNumber(appliedLearnings, learningLoops.length),
    learningCountLabel: appliedLearnings === undefined ? "lições recentes" : "aprendizados aplicados",
    monitorFrozen: monitorTrust.isFrozen,
    goLiveLabel: monitorTrust.isFrozen ? "planos no último monitor" : "planos em go-live",
    goLiveKpiLabel: monitorTrust.isFrozen ? "Último monitor" : "Planos em go-live",
    lastUpdatedAt,
  };
  const executiveSummary = normalizeExecutiveSummary(dashboardSummary, scientificSummary);
  const thesisRows = buildThesisRows(dashboardSummary, supplementalMarketTheses, now, operationRows);
  const activeTheses = goLiveTheses.length > 0
    ? goLiveTheses
    : thesisRows.filter((row) => row.statusGroup === "Go-live" || row.statusGroup === "Em análise").map(activeThesisFromRow);
  const coverage = normalizeCoverage(payloads, monitorTrust, activeTheses);
  const operationalFreshness = buildOperationalFreshness(payloads, coverage, monitorTrust);
  const coveredGoLiveTheses = goLiveTheses.map((thesis) => withCoverageNotes(thesis, coverage));
  const coveredActiveTheses = activeTheses.map((thesis) => withCoverageNotes(thesis, coverage));
  const calibrationRows = buildCalibrationRows(dashboardSummary, executiveSummary);
  const risk = buildRisk(dashboardSummary, coveredActiveTheses, thesisRows);
  const hasCalibrationCycleHistory = asArray(dashboardSummary?.calibration_cycles ?? dashboardSummary?.calibrationCycles).length > 0;
  const realEstateCandidates = asArray(coalesce(payloads?.realEstateCandidates?.candidates, payloads?.realEstateCandidates?.items))
    .map((candidate, index) => normalizeRealEstateCandidate(candidate, index, now));
  const realEstateStats = buildRealEstateStats(thesisRows, realEstateCandidates, dashboardSummary);

  return {
    monitorTrust,
    coverage,
    operationalFreshness,
    scientificSummary,
    executiveSummary,
    goLiveTheses: coveredGoLiveTheses,
    activeTheses: coveredActiveTheses,
    thesisRows,
    learningLoops,
    marketAssets: buildMarketAssets(dashboardSummary, coveredActiveTheses),
    backtest: {
      accuracyCycles: buildAccuracyCycles(dashboardSummary, scientificSummary),
      accuracyCycleSource: hasCalibrationCycleHistory ? "api" : "synthetic",
      calibrations: calibrationRows,
      sampleQuality: history.sample_quality ?? history.sampleQuality ?? null,
    },
    risk,
    alertFeed: buildAlertFeed(dashboardSummary, coveredActiveTheses, risk),
    learningStats: buildLearningStats(scientificSummary, calibrationRows),
    dataQualityGate: dashboardSummary.data_quality_gate ?? null,
    realEstateCandidates,
    realEstateStats,
    realEstateStrategyTerritoryCandidates: normalizeRealEstateStrategyTerritoryCandidates(payloads?.realEstateStrategyTerritoryCandidates),
    phaseKickoffDate: cleanText(dashboardSummary.phase_kickoff_date),
    fronts: buildFronts(dashboardSummary, coveredActiveTheses, now, thesisRows, realEstateStats),
  };
}
