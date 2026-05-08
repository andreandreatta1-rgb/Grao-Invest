const TRUST_RANK = Object.freeze({
  validated: 3,
  partial: 2,
  degraded: 1,
});

const TRUST_LABELS = Object.freeze({
  validated: "Dados validados",
  partial: "Dados parciais",
  degraded: "Dados em revisão",
});

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function addIssue(issues, severity, code, message) {
  issues.push({ severity, code, message });
}

function parseDate(value) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

function referenceDateFor(data) {
  return parseDate(data?.trustReferenceAt) || new Date();
}

function isRangeLike(row) {
  const text = [
    row?.direction,
    row?.priceReferenceLabel,
    row?.structure,
    row?.operation,
    row?.thesisId,
    row?.id,
  ].join(" ").toLowerCase();
  return text.includes("neutra") || text.includes("range") || text.includes("iron condor") || text.includes("faixa") || text.includes("centro");
}

function nearlyEqual(left, right, tolerance = 0.0001) {
  const first = finiteNumber(left);
  const second = finiteNumber(right);
  if (first === null || second === null) return false;
  return Math.abs(first - second) <= tolerance;
}

function isCurrentStatus(row) {
  const status = String(row?.statusGroup ?? row?.status ?? "").toLowerCase();
  return status.includes("go-live") || status.includes("monitor") || status.includes("observ");
}

function validateThesisTemporalConsistency(issues, row, code, referenceDate) {
  const openedAt = parseDate(row?.openedAt ?? row?.opened_at ?? row?.thesis_raised_at);
  if (openedAt && openedAt.getTime() > referenceDate.getTime() + 60_000) {
    addIssue(issues, "error", `${code}.openedAt.future`, "Tese com abertura futura para o usuario.");
  }

  const latestEventAt = parseDate(row?.latestEventAt ?? row?.latest_event_time);
  if (
    row?.front === "B3"
    && isCurrentStatus(row)
    && latestEventAt
    && referenceDate.getTime() - latestEventAt.getTime() > 96 * 60 * 60 * 1000
  ) {
    addIssue(issues, "error", `${code}.b3.stale_current`, "Tese B3 antiga exibida como monitor atual.");
  }
}

function validateThesisPriceConsistency(issues, row, code) {
  const entryPrice = finiteNumber(row?.entryPrice ?? row?.entry_price ?? row?.entrada);
  const targetPrice = finiteNumber(row?.targetPrice ?? row?.target_price ?? row?.alvo);
  const stopPrice = finiteNumber(row?.stopPrice ?? row?.stop_price);
  const rangeLower = finiteNumber(row?.rangeLowerPrice ?? row?.range_lower_price);
  const rangeUpper = finiteNumber(row?.rangeUpperPrice ?? row?.range_upper_price);
  const rangeLike = isRangeLike(row);

  if (!rangeLike && entryPrice !== null && targetPrice !== null && nearlyEqual(entryPrice, targetPrice)) {
    addIssue(issues, "error", `${code}.target.same_as_entry`, "Tese direcional com entrada igual ao alvo.");
  }

  if (!rangeLike) return;

  if (rangeLower === null || rangeUpper === null) {
    addIssue(issues, "error", `${code}.range.bounds`, "Tese neutra/range sem faixa inferior e superior explicita.");
    return;
  }
  if (rangeLower >= rangeUpper) {
    addIssue(issues, "error", `${code}.range.bounds_order`, "Faixa de range com limites invertidos ou iguais.");
  }
  if (entryPrice !== null && (entryPrice < rangeLower || entryPrice > rangeUpper)) {
    addIssue(issues, "error", `${code}.range.entry_outside`, "Centro/entrada fora da faixa do range.");
  }
  if (stopPrice !== null && stopPrice > rangeLower && stopPrice < rangeUpper) {
    addIssue(issues, "warning", `${code}.range.stop_inside`, "Stop de range dentro da faixa de validade.");
  }
}

function validateFinite(issues, code, value, { min = -Infinity, max = Infinity, required = true } = {}) {
  const number = finiteNumber(value);
  if (number === null) {
    if (required) addIssue(issues, "error", `${code}.missing`, "Valor numérico ausente ou inválido.");
    return;
  }
  if (number < min || number > max) {
    addIssue(issues, "error", `${code}.range`, "Valor fora da faixa esperada.");
  }
}

function calibrationCycleOrder(label, fallback) {
  const match = String(label ?? "").match(/(?:Cal\.)?\s*0?(\d{1,3})/i);
  return match ? Number(match[1]) : fallback;
}

function buildTrust(screen, issues) {
  const hasError = issues.some((issue) => issue.severity === "error");
  const hasWarning = issues.some((issue) => issue.severity === "warning");
  const status = hasError ? "degraded" : hasWarning ? "partial" : "validated";

  return {
    screen,
    status,
    label: TRUST_LABELS[status],
    issues,
  };
}

function addFeedIssue(issues, feedStatus) {
  if (feedStatus && feedStatus !== "live") {
    addIssue(issues, "warning", "feed.fallback", "A tela está usando fallback ou retrato parcial.");
  }
}

function validateDashboard(data, issues) {
  const summary = data?.scientificSummary ?? {};

  validateFinite(issues, "dashboard.testedTheses", summary.testedTheses, { min: 0 });
  validateFinite(issues, "dashboard.validatedPct", summary.validatedPct, { min: 0, max: 100 });
  validateFinite(issues, "dashboard.expectancyPct", summary.expectancyPct, { min: -100, max: 100 });
  validateFinite(issues, "dashboard.goLiveCount", summary.goLiveCount, { min: 0 });
  validateFinite(issues, "dashboard.appliedLearningsCount", summary.appliedLearningsCount, { min: 0 });
}

function validateTeses(data, issues) {
  const rows = [
    ...asArray(data?.thesisRows),
    ...asArray(data?.activeTheses),
    ...asArray(data?.goLiveTheses),
  ];
  if (rows.length === 0) {
    addIssue(issues, "warning", "teses.rows.empty", "Nenhuma tese normalizada disponível.");
    return;
  }

  const referenceDate = referenceDateFor(data);
  const monitorFrozen = data?.monitorTrust?.isFrozen === true;
  rows.forEach((row, index) => {
    if (!row?.id) addIssue(issues, "error", `teses.rows.${index}.id`, "Tese sem identificador.");
    if (!row?.asset) addIssue(issues, "error", `teses.rows.${index}.asset`, "Tese sem ativo.");
    if (!row?.front) addIssue(issues, "error", `teses.rows.${index}.front`, "Tese sem frente.");
    if (!row?.statusGroup) addIssue(issues, "error", `teses.rows.${index}.status`, "Tese sem status normalizado.");
    validateFinite(issues, `teses.rows.${index}.expectedPct`, row.expectedPct, { min: -1000, max: 1000, required: false });
    validateFinite(issues, `teses.rows.${index}.resultPct`, row.resultPct, { min: -1000, max: 1000, required: false });
    validateThesisPriceConsistency(issues, row, `teses.rows.${index}`);
    if (!monitorFrozen) {
      validateThesisTemporalConsistency(issues, row, `teses.rows.${index}`, referenceDate);
    }
  });
}

function validateBacktest(data, issues) {
  if (data?.backtest?.accuracyCycleSource === "synthetic") {
    addIssue(issues, "warning", "backtest.cycles.synthetic", "Série de calibração estimada a partir do acerto acumulado.");
  }

  const cycles = asArray(data?.backtest?.accuracyCycles);
  if (cycles.length < 2) {
    addIssue(issues, "warning", "backtest.cycles.short", "Histórico de calibração insuficiente.");
    return;
  }

  let previousOrder = -Infinity;
  cycles.forEach((cycle, index) => {
    const order = calibrationCycleOrder(cycle?.ciclo, index);
    validateFinite(issues, `backtest.cycles.${index}.taxa`, cycle?.taxa, { min: 0, max: 100 });
    if (order < previousOrder) {
      addIssue(issues, "warning", "backtest.cycles.order", "Ciclos de calibração fora da ordem cronológica.");
    }
    previousOrder = order;
  });
}

export function dataTrustForScreen(screen, data = {}, feedStatus = "live") {
  const issues = [];
  addFeedIssue(issues, feedStatus);

  if (screen === "dashboard") validateDashboard(data, issues);
  if (screen === "teses") validateTeses(data, issues);
  if (screen === "backtest") validateBacktest(data, issues);

  return buildTrust(screen, issues);
}

export function withCockpitDataTrust(data = {}, feedStatus = "live") {
  const dataTrust = {
    dashboard: dataTrustForScreen("dashboard", data, feedStatus),
    teses: dataTrustForScreen("teses", data, feedStatus),
    backtest: dataTrustForScreen("backtest", data, feedStatus),
  };
  const overall = Object.values(dataTrust).reduce((worst, trust) => (
    TRUST_RANK[trust.status] < TRUST_RANK[worst.status] ? trust : worst
  ), dataTrust.dashboard);

  return {
    ...data,
    dataTrust: {
      ...dataTrust,
      overall,
    },
  };
}
