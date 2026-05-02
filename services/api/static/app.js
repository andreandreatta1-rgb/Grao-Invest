const TOKEN_KEY = "ia_session_token";
const USER_KEY = "ia_session_user";
const SIDEBAR_COLLAPSED_KEY = "sidebar_collapsed";
const AUTH_REQUIRED = false;
const PROFILE_CONFIRMATION_REQUIRED = false;
const ANON_USER = {
  sub: 1,
  email: "anon@graoinvest.local",
  full_name: "Convidado",
};

const state = {
  accessToken: null,
  user: null,
  signalId: null,
  pendingLogin: null,
  game: null,
  selectedTicker: "PETR4",
  dashboardSnapshot: null,
};

const realtime = {
  signalsSocket: null,
  agentSocket: null,
  signalsPollingId: null,
  reconnectSignalsMs: 1000,
  reconnectAgentMs: 1500,
};

const viewMeta = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Visão consolidada da simulação, risco e trilha operacional.",
  },
  mercado: {
    title: "Mercado",
    subtitle: "Ingestão de ticks e notícias com análise técnica point-in-time.",
  },
  operacoes: {
    title: "Operações",
    subtitle: "Paper trading sem execução real em corretora.",
  },
  backtest: {
    title: "Backtest",
    subtitle: "Reexecução histórica com métricas e rationale auditável.",
  },
  risco: {
    title: "Risco",
    subtitle: "Circuit breaker e kill-switch com controle por escopo.",
  },
  game: {
    title: "Game",
    subtitle: "Simulacao interativa com 5 teses, contexto historico e carteira virtual.",
  },
  microtrades: {
    title: "Microtrades (Beta)",
    subtitle: "Modulo experimental para operacoes curtas com controle de risco e validacao de edge.",
  },
  alertas: {
    title: "Alertas",
    subtitle: "Regras de alerta e relatório consolidado por usuário.",
  },
  finvest: {
    title: "Grão Invest",
    subtitle: "Painel visual para exercícios de teses, metas e planejamento financeiro.",
  },
};

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatMoney(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(number);
}

function formatNumber(value) {
  return new Intl.NumberFormat("pt-BR").format(Number(value || 0));
}

function formatPercent(value) {
  const numeric = Number(value || 0);
  return `${numeric.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

function formatMetric(value) {
  if (!Number.isFinite(Number(value))) {
    return "-";
  }
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatSignedMetricPercent(value) {
  if (!Number.isFinite(Number(value))) {
    return "-";
  }
  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : "";
  return `${prefix}${formatMetric(numeric)}%`;
}

function formatDayShort(value) {
  const raw = String(value || "");
  if (raw.length < 10) {
    return raw || "-";
  }
  return `${raw.slice(8, 10)}/${raw.slice(5, 7)}`;
}

function assetClassLabel(value) {
  const labels = {
    stock: "Ação BR",
    fii: "FII",
    etf: "ETF",
    bdr: "BDR",
    fx: "Câmbio",
    cash: "Caixa",
    unknown: "Outro",
  };
  return labels[String(value || "unknown").toLowerCase()] || labels.unknown;
}

function renderAssetClassBadge(value, label) {
  const normalized = String(value || "unknown").toLowerCase();
  return `<span class="asset-class-badge asset-class-${escapeHtml(normalized)}">${escapeHtml(label || assetClassLabel(normalized))}</span>`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString("pt-BR");
}

function showToast(type, message) {
  const stack = byId("toast-stack");
  if (!stack) {
    return;
  }
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  stack.prepend(toast);
  window.setTimeout(() => {
    toast.remove();
  }, 4200);
}

function setButtonLoading(button, isLoading, loadingText = "Processando...") {
  if (!button) {
    return;
  }
  if (isLoading) {
    button.dataset.originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = loadingText;
    return;
  }
  button.disabled = false;
  if (button.dataset.originalLabel) {
    button.textContent = button.dataset.originalLabel;
  }
}

function valueAsString(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "Sim" : "Não";
  }
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      return formatNumber(value);
    }
    return value.toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 6,
    });
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

function normalizeKvEntries(data) {
  if (Array.isArray(data)) {
    return data.map((item, index) => [`Item ${index + 1}`, item]);
  }
  if (data && typeof data === "object") {
    return Object.entries(data);
  }
  return [["valor", data]];
}

function renderKeyValueCard(containerId, data, labelMap = {}) {
  const container = byId(containerId);
  if (!container) {
    return;
  }
  const entries = normalizeKvEntries(data);
  container.innerHTML = entries
    .map(([key, rawValue]) => {
      const label = labelMap[key] || key;
      const value = valueAsString(rawValue);
      return `
        <div class="kv-row">
          <span class="kv-label">${escapeHtml(label)}</span>
          <span class="kv-value">${escapeHtml(value)}</span>
        </div>
      `;
    })
    .join("");
}

function setOutput(containerId, data, labelMap = {}) {
  renderKeyValueCard(containerId, data, labelMap);
}

function decodeJwtPayload(token) {
  if (!token) {
    return null;
  }
  const parts = String(token).split(".");
  if (parts.length !== 3) {
    return null;
  }
  try {
    const base64Url = parts[1];
    const base64 = base64Url.replaceAll("-", "+").replaceAll("_", "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(window.atob(padded));
  } catch {
    return null;
  }
}

function isTokenValid(token) {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") {
    return false;
  }
  return payload.exp * 1000 > Date.now();
}

function saveSession(token, userData) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(userData));
  state.accessToken = token;
  state.user = userData;
}

function clearSession() {
  stopRealtimeStreams();
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  state.accessToken = null;
  state.user = null;
  state.signalId = null;
  state.pendingLogin = null;
  state.dashboardSnapshot = null;
}

function enableAnonymousSession() {
  stopRealtimeStreams();
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.setItem(USER_KEY, JSON.stringify(ANON_USER));
  state.accessToken = null;
  state.user = { ...ANON_USER };
  state.signalId = null;
  state.pendingLogin = null;
}

function getStoredToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function getAuthUser() {
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getAuthUserId() {
  const user = state.user || getAuthUser();
  const parsed = Number(user?.sub);
  return Number.isFinite(parsed) ? parsed : null;
}

function hydrateSessionFromStorage() {
  const token = getStoredToken();
  const user = getAuthUser();
  if (token && user && isTokenValid(token)) {
    state.accessToken = token;
    state.user = user;
    return true;
  }
  clearSession();
  return false;
}

function showAuthGate() {
  const gate = byId("auth-gate");
  const shell = byId("app-shell");
  if (gate) {
    gate.style.display = "flex";
  }
  if (shell) {
    shell.style.display = "none";
  }
}

function hideAuthGate() {
  const gate = byId("auth-gate");
  const shell = byId("app-shell");
  if (gate) {
    gate.style.display = "none";
  }
  if (shell) {
    shell.style.display = "flex";
  }
}

function handleSessionExpired() {
  if (!AUTH_REQUIRED) {
    enableAnonymousSession();
    hideAuthGate();
    switchView("finvest");
    void loadDashboard();
    return;
  }
  clearSession();
  showAuthGate();
  showAuthPanel("login");
  showToast("warning", "Sessão expirada. Faça login novamente.");
}

async function apiRequest(method, url, payload = null, { auth = true, timeoutMs = 45000 } = {}) {
  const headers = {};
  if (payload !== null) {
    headers["Content-Type"] = "application/json";
  }
  const token = getStoredToken() || state.accessToken;
  if (auth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, timeoutMs);
  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: payload !== null ? JSON.stringify(payload) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Tempo de resposta excedido. Tente novamente.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }

  const raw = await response.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { raw };
    }
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      handleSessionExpired();
    }
    const message =
      data && typeof data === "object"
        ? data.detail || data.message || `${response.status} ${response.statusText}`
        : `${response.status} ${response.statusText}`;
    const error = new Error(message);
    error.data = data;
    error.status = response.status;
    throw error;
  }
  return data;
}

function toSignalTone(signalType) {
  const normalized = String(signalType || "").toLowerCase();
  if (normalized.includes("sell") || normalized.includes("short")) {
    return "tone-danger";
  }
  if (normalized.includes("buy") || normalized.includes("long")) {
    return "tone-success";
  }
  return "tone-accent";
}

function renderDashboardLoading() {
  const kpiNode = byId("dashboard-kpis");
  if (kpiNode) {
    kpiNode.innerHTML = [
      "<div class='skeleton-card'></div>",
      "<div class='skeleton-card'></div>",
      "<div class='skeleton-card'></div>",
      "<div class='skeleton-card'></div>",
    ].join("");
  }

  const emptyTargets = [
    "dashboard-positions",
    "dashboard-signals",
    "dashboard-backtests",
    "dashboard-alerts",
    "dashboard-historical-summary",
    "dashboard-current-summary",
    "dashboard-history-metrics",
    "dashboard-history-evolution",
    "dashboard-thesis-open-operations",
    "dashboard-thesis-historical-operations",
    "dashboard-thesis-current-operations",
    "dashboard-current-daily-table",
    "dashboard-coverage-summary",
    "dashboard-coverage-table",
    "dashboard-quality-summary",
    "dashboard-quality-table",
  ];
  emptyTargets.forEach((targetId) => {
    const node = byId(targetId);
    if (node) {
      node.innerHTML = "";
    }
  });
}


function renderDashboardKpis(data) {
  const kpiNode = byId("dashboard-kpis");
  if (!kpiNode) {
    return;
  }

  const historical = data.historical_analysis_summary || {};
  const current = data.current_simulation_summary || {};
  const qualityGateStatus = String(data?.data_quality_gate?.summary?.gate_status || "unknown");
  const currentReturn = Number(current.avg_backtest_return_pct || 0);

  const cards = [
    {
      label: "Backtests historicos",
      value: formatNumber(historical.backtest_runs || 0),
      tone: "tone-accent",
      mono: true,
    },
    {
      label: "Win rate medio historico",
      value: `${formatMetric(historical.avg_win_rate_pct || 0)}%`,
      tone: "tone-success",
      mono: true,
    },
    {
      label: "Ordens na fase atual",
      value: formatNumber(current.paper_orders || 0),
      tone: "tone-warning",
      mono: true,
    },
    {
      label: "Retorno medio BT atual",
      value: `${formatMetric(currentReturn)}%`,
      tone: currentReturn >= 0 ? "tone-success" : "tone-danger",
      mono: true,
    },
    {
      label: "Gate de dados",
      value: qualityGateStatus.toUpperCase(),
      tone: qualityGateStatus === "pass" ? "tone-success" : "tone-danger",
      mono: false,
    },
  ];

  kpiNode.innerHTML = cards
    .map(
      (card) => `
        <article class="kpi-card">
          <p class="kpi-label">${escapeHtml(card.label)}</p>
          <p class="kpi-value ${card.tone} ${card.mono ? "mono" : ""}">${escapeHtml(card.value)}</p>
        </article>
      `,
    )
    .join("");
}

function renderPositionsTable(data) {
  const body = byId("dashboard-positions");
  if (!body) {
    return;
  }
  const positions = data.open_positions || [];
  if (positions.length === 0) {
    body.innerHTML = "<tr><td colspan='4'>Sem posições abertas para este usuário.</td></tr>";
    return;
  }

  body.innerHTML = positions
    .map(
      (position) => `
      <tr>
        <td>${escapeHtml(position.instrument)}</td>
        <td class="mono">${escapeHtml(formatNumber(position.quantity))}</td>
        <td class="mono">${escapeHtml(formatMoney(position.average_price))}</td>
        <td>${escapeHtml(formatDate(position.updated_at))}</td>
      </tr>
    `,
    )
    .join("");
}

function renderListRows(containerId, rows, emptyMessage, rowBuilder) {
  const container = byId(containerId);
  if (!container) {
    return;
  }
  if (!rows || rows.length === 0) {
    container.innerHTML = `<div class="list-row"><p class="list-meta">${escapeHtml(emptyMessage)}</p></div>`;
    return;
  }
  container.innerHTML = rows.map((row) => rowBuilder(row)).join("");
}

function renderCoverage(coverage) {
  const summaryNode = byId("dashboard-coverage-summary");
  const tableBody = byId("dashboard-coverage-table");
  if (!summaryNode || !tableBody) {
    return;
  }
  if (!coverage || !Array.isArray(coverage.instruments)) {
    summaryNode.innerHTML =
      "<div class='list-row'><p class='list-meta'>Cobertura indisponível no momento.</p></div>";
    tableBody.innerHTML = "<tr><td colspan='6'>Sem dados de cobertura.</td></tr>";
    return;
  }
  const classCounts = coverage.asset_class_counts || {};
  const classSummary = Object.entries(classCounts)
    .filter(([, count]) => Number(count || 0) > 0)
    .map(([assetClass, count]) => `${assetClassLabel(assetClass)} ${formatNumber(count)}`)
    .join(" | ");

  summaryNode.innerHTML = `
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Ativos cobertos</p>
        <p class="list-meta mono">${escapeHtml(formatNumber(coverage.total_instruments_covered || 0))}</p>
      </div>
      <p class="list-meta">${escapeHtml(classSummary || "Classes ainda não classificadas")}</p>
    </div>
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Último evento de mercado</p>
        <p class="list-meta">${escapeHtml(formatDate(coverage.latest_market_event_time))}</p>
      </div>
      <p class="list-meta">Gerado em ${escapeHtml(formatDate(coverage.generated_at))} | Último ingest ${escapeHtml(formatDate(coverage.latest_ingest_time))}</p>
    </div>
  `;

  if (coverage.instruments.length === 0) {
    tableBody.innerHTML = "<tr><td colspan='6'>Sem ativos ingeridos.</td></tr>";
    return;
  }
  tableBody.innerHTML = coverage.instruments
    .map(
      (row) => `
      <tr>
        <td>${escapeHtml(row.instrument)}</td>
        <td>${renderAssetClassBadge(row.asset_class, row.asset_class_label)}</td>
        <td>${escapeHtml(row.provider)}</td>
        <td class="mono">${escapeHtml(formatMoney(row.last_price))}</td>
        <td class="mono">${escapeHtml(formatNumber(row.lag_seconds))}</td>
        <td>${escapeHtml(formatDate(row.last_ingest_time))}</td>
      </tr>
    `,
    )
    .join("");
}

function renderDataQualityGate(gate) {
  const summaryNode = byId("dashboard-quality-summary");
  const tableBody = byId("dashboard-quality-table");
  if (!summaryNode || !tableBody) {
    return;
  }
  if (!gate || !gate.summary || !Array.isArray(gate.checks)) {
    summaryNode.innerHTML =
      "<div class='list-row'><p class='list-meta'>Data quality gate indisponível.</p></div>";
    tableBody.innerHTML = "<tr><td colspan='5'>Sem checks disponíveis.</td></tr>";
    return;
  }

  const summary = gate.summary || {};
  const status = String(summary.gate_status || "fail");
  const statusTone = status === "pass" ? "tone-success" : "tone-danger";
  const actions = Array.isArray(gate.recommended_actions) ? gate.recommended_actions : [];
  summaryNode.innerHTML = `
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Gate status</p>
        <p class="list-meta ${statusTone}"><strong>${escapeHtml(status.toUpperCase())}</strong></p>
      </div>
      <p class="list-meta">Score ${escapeHtml(formatMetric(summary.quality_score_pct || 0))}%</p>
    </div>
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Checks</p>
        <p class="list-meta mono">${escapeHtml(formatNumber(summary.passed_checks || 0))}/${escapeHtml(formatNumber(summary.total_checks || 0))}</p>
      </div>
      <p class="list-meta">Falhas ${escapeHtml(formatNumber(summary.failed_checks || 0))}</p>
    </div>
    <div class="list-row">
      <p class="list-title">Ações recomendadas</p>
      <p class="list-meta">${escapeHtml(actions.length ? actions.join(" | ") : "Sem pendências no gate.")}</p>
    </div>
  `;

  if (gate.checks.length === 0) {
    tableBody.innerHTML = "<tr><td colspan='5'>Sem checks configurados.</td></tr>";
    return;
  }

  tableBody.innerHTML = gate.checks
    .map((check) => {
      const passed = String(check.status || "fail") === "pass";
      const tone = passed ? "tone-success" : "tone-danger";
      const comparator = String(check.comparator || ">=");
      return `
      <tr>
        <td>${escapeHtml(check.label || check.check_id || "-")}</td>
        <td class="${tone}"><strong>${passed ? "PASS" : "FAIL"}</strong></td>
        <td class="mono">${escapeHtml(formatMetric(check.actual_value))}</td>
        <td class="mono">${escapeHtml(comparator)} ${escapeHtml(formatMetric(check.target_value))}</td>
        <td>${escapeHtml(check.details || "-")}</td>
      </tr>
    `;
    })
    .join("");
}

function renderThesisHistoryOverview(data) {
  const metricsNode = byId("dashboard-history-metrics");
  const chartNode = byId("dashboard-history-evolution");
  if (!metricsNode || !chartNode) {
    return;
  }

  const overview = data.thesis_history_overview || null;
  if (!overview || typeof overview !== "object") {
    metricsNode.innerHTML = "";
    chartNode.innerHTML = "<div class='list-row'><p class='list-meta'>Historico acumulado indisponivel no momento.</p></div>";
    return;
  }

  const totalTested = Number(overview.total_tested || 0);
  const successCount = Number(overview.success_count || 0);
  const successRatePct = Number(overview.success_rate_pct || 0);
  const avgResultPct = Number(overview.avg_result_pct || 0);
  const expectancyNetPct = Number(overview.expectancy_net_pct || avgResultPct);
  const targetRatePct = Number(overview.target_rate_pct || 0);
  const stopRatePct = Number(overview.stop_rate_pct || 0);
  const timeExitRatePct = Number(overview.time_exit_rate_pct || 0);
  const openRatePct = Number(overview.open_rate_pct || 0);
  const openCount = Number(overview.open_count || 0);
  const resolutionSampleCount = Number(overview.resolution_sample_count || 0);
  const avgResolutionDays = Number(overview.avg_resolution_days);
  const hasAvgResolutionDays = Number.isFinite(avgResolutionDays) && resolutionSampleCount > 0;
  const windowStart = String(overview.window_start || "-");
  const windowEnd = String(overview.window_end || "-");

  const cards = [
    {
      label: "Teses testadas ate hoje",
      value: formatNumber(totalTested),
      tone: "tone-success",
      mono: true,
      sub: `Periodo ${windowStart} ate ${windowEnd}`,
    },
    {
      label: "Expectancia liquida",
      value: formatSignedMetricPercent(expectancyNetPct),
      tone: expectancyNetPct >= 0 ? "tone-success" : "tone-danger",
      mono: true,
      sub: "Media esperada por tese resolvida",
    },
    {
      label: "Teses com sucesso",
      value: formatNumber(successCount),
      tone: "tone-accent",
      mono: true,
      sub: `Taxa de sucesso ${formatMetric(successRatePct)}%`,
    },
    {
      label: "Alvo / Stop / Tempo",
      value: `${formatMetric(targetRatePct)}% / ${formatMetric(stopRatePct)}% / ${formatMetric(timeExitRatePct)}%`,
      tone: "tone-warning",
      mono: true,
      sub: `Em monitoramento: ${formatMetric(openRatePct)}% (${formatNumber(openCount)})`,
    },
    {
      label: "Tempo medio ate resultado",
      value: hasAvgResolutionDays ? `${formatMetric(avgResolutionDays)} dias` : "-",
      tone: "tone-accent",
      mono: true,
      sub: `Amostra: ${formatNumber(resolutionSampleCount)} teses encerradas`,
    },
  ];

  metricsNode.innerHTML = cards
    .map(
      (card) => `
        <article class="kpi-card">
          <p class="kpi-label">${escapeHtml(card.label)}</p>
          <p class="kpi-value ${card.tone} ${card.mono ? "mono" : ""}">${escapeHtml(card.value)}</p>
          ${card.sub ? `<p class="list-meta">${escapeHtml(card.sub)}</p>` : ""}
        </article>
      `,
    )
    .join("");

  const kickoffDate = String(data.phase_kickoff_date || "2026-04-27");
  const rows = Array.isArray(data.thesis_open_operations) ? data.thesis_open_operations : [];

  const classifyPhase = (row) => {
    const explicitPhase = String(row.phase || row.source_phase || "").toLowerCase();
    if (explicitPhase.includes("histor")) {
      return "historical";
    }
    if (
      explicitPhase.includes("pos")
      || explicitPhase.includes("go_live")
      || explicitPhase.includes("go-live")
      || explicitPhase.includes("current")
    ) {
      return "current";
    }
    const thesisDateRaw = String(
      row.thesis_raised_at || row.entry_time || row.reference_day || row.suggested_entry_time || "",
    );
    const thesisDay = thesisDateRaw.length >= 10 ? thesisDateRaw.slice(0, 10) : "";
    if (thesisDay && kickoffDate && thesisDay < kickoffDate) {
      return "historical";
    }
    return "current";
  };

  const isOpenStatus = (row) => {
    const status = String(row.status || "").toLowerCase();
    if (status.includes("aberta") || status.includes("aberto") || status.includes("monitor")) {
      return true;
    }
    const monitorStatus = String(row.monitor_status || "").toLowerCase();
    return monitorStatus === "monitoring";
  };

  const trimText = (value, maxLen = 190) => {
    const text = String(value || "").trim();
    if (!text) {
      return "-";
    }
    if (text.length <= maxLen) {
      return text;
    }
    return `${text.slice(0, maxLen - 1).trim()}...`;
  };

  const openRows = rows.filter((row) => row && typeof row === "object" && isOpenStatus(row));
  const openCurrentRows = openRows.filter((row) => classifyPhase(row) === "current");
  const openHistoricalRows = openRows.filter((row) => classifyPhase(row) === "historical");
  const prioritizedRows = (openCurrentRows.length ? openCurrentRows : openRows)
    .slice()
    .sort((a, b) => Number(b.thesis_number || 0) - Number(a.thesis_number || 0));

  if (!prioritizedRows.length) {
    chartNode.innerHTML = "<div class='list-row'><p class='list-meta'>Nao ha operacoes ativas no momento.</p></div>";
    return;
  }

  const cardsHtml = prioritizedRows
    .slice(0, 6)
    .map((row) => {
      const thesisNumber = Number(row.thesis_number || 0);
      const action = String(row.action || "n/d");
      const status = String(row.status || "Aberta");
      const outcome = String(row.outcome || "Em monitoramento");
      const expectedResult = Number(row.expected_result_pct || 0);
      const momentResult = Number(row.moment_result_pct || 0);
      const entryPrice = Number(row.entry_price_brl);
      const entryLabel = Number.isFinite(entryPrice) && entryPrice > 0 ? formatMoney(entryPrice) : "-";
      const operationPlan = trimText(row.operation_plan || "-");
      const structuredOperation = trimText(row.structured_operation || "-");
      const exitRule = trimText(row.exit_rule || "-");
      const reason = trimText(row.thesis_reason || "-", 220);
      const raisedAt = String(row.thesis_raised_at || row.entry_time || row.suggested_entry_time || "");
      const raisedDay = raisedAt.length >= 10 ? `${raisedAt.slice(8, 10)}/${raisedAt.slice(5, 7)}/${raisedAt.slice(0, 4)}` : "-";
      const statusTone = String(status).toLowerCase().includes("aberta") ? "tone-warning" : "tone-success";
      const momentTone = Number.isFinite(momentResult) && momentResult < 0 ? "tone-danger" : "tone-success";
      const phaseLabel = classifyPhase(row) === "historical" ? "Historico" : "Pos go-live";

      return `
        <article class="list-row active-op-card">
          <div class="list-main">
            <p class="list-title">Tese ${escapeHtml(formatNumber(thesisNumber || 0))} | ${escapeHtml(action)}</p>
            <p class="list-meta mono ${statusTone}"><strong>${escapeHtml(status)}</strong></p>
          </div>
          <p class="list-meta">${escapeHtml(phaseLabel)} | Inicio: ${escapeHtml(raisedDay)} | Desfecho atual: ${escapeHtml(outcome)}</p>
          <p class="list-meta">Esperado: <span class="mono">${escapeHtml(formatSignedMetricPercent(expectedResult))}</span> | Momento: <span class="mono ${momentTone}">${escapeHtml(formatSignedMetricPercent(momentResult))}</span></p>
          <p class="list-meta">Entra em: <span class="mono">${escapeHtml(entryLabel)}</span></p>
          <p class="list-meta">Operacao: ${escapeHtml(operationPlan)}</p>
          <p class="list-meta">Estrutura: ${escapeHtml(structuredOperation)}</p>
          <p class="list-meta">Sai se: ${escapeHtml(exitRule)}</p>
          <p class="list-meta">Motivo: ${escapeHtml(reason)}</p>
        </article>
      `;
    })
    .join("");

  chartNode.innerHTML = `
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Operacoes ativas das teses</p>
        <p class="list-meta mono">${escapeHtml(formatNumber(openRows.length))} abertas</p>
      </div>
      <p class="list-meta">Pos go-live: ${escapeHtml(formatNumber(openCurrentRows.length))} | Historico: ${escapeHtml(formatNumber(openHistoricalRows.length))}</p>
    </div>
    <div class="history-weeks-grid">
      ${cardsHtml}
    </div>
  `;
}

function renderPhaseSummaries(data) {
  const historicalNode = byId("dashboard-historical-summary");
  const currentNode = byId("dashboard-current-summary");
  if (!historicalNode || !currentNode) {
    return;
  }

  const kickoffDate = String(data.phase_kickoff_date || "2026-04-27");
  const executive = data.thesis_executive_summary || {};
  const historical = executive.historical || null;
  const current = executive.current || null;

  const buildExecutiveCard = (summary, fallbackPeriodLabel) => {
    if (!summary || typeof summary !== "object") {
      return "<div class='list-row'><p class='list-meta'>Resumo indisponivel no momento.</p></div>";
    }
    return `
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">Periodo</p>
          <p class="list-meta">${escapeHtml(summary.period_label || fallbackPeriodLabel)}</p>
        </div>
      </div>
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">Quantas teses</p>
          <p class="list-meta mono">${escapeHtml(formatNumber(summary.thesis_count || 0))}</p>
        </div>
      </div>
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">% esperado</p>
          <p class="list-meta mono">${escapeHtml(formatMetric(summary.expected_pct || 0))}%</p>
        </div>
      </div>
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">% alcancado</p>
          <p class="list-meta mono">${escapeHtml(formatMetric(summary.achieved_pct || 0))}%</p>
        </div>
      </div>
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">Teses aprovadas</p>
          <p class="list-meta mono">${escapeHtml(formatNumber(summary.approved_count || 0))}</p>
        </div>
      </div>
    `;
  };

  historicalNode.innerHTML = buildExecutiveCard(
    historical,
    `ate ${kickoffDate} (base historica)`,
  );
  currentNode.innerHTML = buildExecutiveCard(
    current,
    `desde ${kickoffDate} (simulacao atual)`,
  );
}

function renderThesisOpenOperations(data) {
  const historicalBody = byId("dashboard-thesis-historical-operations");
  const currentBody = byId("dashboard-thesis-current-operations");
  const legacyBody = byId("dashboard-thesis-open-operations");
  if (!historicalBody && !currentBody && !legacyBody) {
    return;
  }
  const rows = Array.isArray(data.thesis_open_operations) ? data.thesis_open_operations : [];

  const kickoffDate = String(data.phase_kickoff_date || "2026-04-27");

  const classifyPhase = (row) => {
    const explicitPhase = String(row.phase || row.source_phase || "").toLowerCase();
    if (explicitPhase.includes("histor")) {
      return "historical";
    }
    if (
      explicitPhase.includes("pos")
      || explicitPhase.includes("go_live")
      || explicitPhase.includes("go-live")
      || explicitPhase.includes("current")
    ) {
      return "current";
    }
    const operationPlan = String(row.operation_plan || "").toLowerCase();
    if (operationPlan.includes("case study historico")) {
      return "historical";
    }
    const thesisDateRaw = String(
      row.thesis_raised_at || row.entry_time || row.reference_day || row.suggested_entry_time || "",
    );
    const thesisDay = thesisDateRaw.length >= 10 ? thesisDateRaw.slice(0, 10) : "";
    if (thesisDay && kickoffDate && thesisDay < kickoffDate) {
      return "historical";
    }
    return "current";
  };

  const renderRows = (targetRows, emptyMessage) => {
    if (!targetRows.length) {
      return `<tr><td colspan='13'>${escapeHtml(emptyMessage)}</td></tr>`;
    }
    return targetRows
      .map((row) => {
      const status = String(row.status || "-");
      const statusLower = status.toLowerCase();
      const statusTone = statusLower.includes("invalid")
        ? "tone-danger"
        : statusLower.includes("aten")
          ? "tone-warning"
          : statusLower.includes("revisar")
            ? "tone-accent"
            : statusLower.includes("mantida")
              ? "tone-success"
              : statusLower.includes("aberta")
                ? "tone-warning"
                : "tone-success";
      const outcome = String(row.outcome || "-");
      const outcomeLower = outcome.toLowerCase();
      const outcomeTone = outcomeLower.includes("invalid")
        ? "tone-danger"
        : outcomeLower.includes("aten")
          ? "tone-warning"
          : outcomeLower.includes("revisar")
            ? "tone-accent"
            : outcomeLower.includes("mantida")
              ? "tone-success"
              : outcomeLower.includes("alvo")
                ? "tone-success"
                : outcomeLower.includes("stop")
                  ? "tone-danger"
                  : outcomeLower.includes("tempo")
                    ? "tone-warning"
                    : "tone-accent";
      const durationDays = Number(row.duration_days);
      const durationLabel = Number.isFinite(durationDays)
        ? `${formatNumber(Math.round(durationDays))} d`
        : "-";
      const momentValue = Number(row.moment_result_pct || 0);
      const momentTone = momentValue >= 0 ? "tone-success" : "tone-danger";
      const entryPrice = Number(row.entry_price_brl);
      const entryLabel = Number.isFinite(entryPrice) && entryPrice > 0 ? formatMoney(entryPrice) : "-";
      return `
      <tr>
        <td class="mono">${escapeHtml(formatNumber(row.thesis_number || 0))}</td>
        <td>${escapeHtml(row.action || "-")}</td>
        <td>${escapeHtml(row.thesis_reason || "-")}</td>
        <td class="mono">${escapeHtml(formatMetric(row.expected_result_pct || 0))}%</td>
        <td>${escapeHtml(row.operation_plan || "-")}</td>
        <td>${escapeHtml(row.structured_operation || "-")}</td>
        <td class="mono">${escapeHtml(entryLabel)}</td>
        <td>${escapeHtml(row.exit_rule || "-")}</td>
        <td class="${outcomeTone}"><strong>${escapeHtml(outcome)}</strong></td>
        <td class="mono">${escapeHtml(durationLabel)}</td>
        <td class="${statusTone}"><strong>${escapeHtml(status)}</strong></td>
        <td class="mono ${momentTone}">${escapeHtml(formatMetric(momentValue))}%</td>
        <td>${escapeHtml(row.learning_note || "-")}</td>
      </tr>
    `;
      })
      .join("");
  };

  const historicalRows = [];
  const currentRows = [];
  rows.forEach((row) => {
    if (classifyPhase(row) === "historical") {
      historicalRows.push(row);
    } else {
      currentRows.push(row);
    }
  });

  const currentOpenRows = currentRows.filter((row) =>
    String(row.status || "").toLowerCase().includes("aberta"),
  );

  if (historicalBody) {
    historicalBody.innerHTML = renderRows(
      historicalRows,
      "Sem teses históricas no momento.",
    );
  }
  if (currentBody) {
    currentBody.innerHTML = renderRows(
      currentOpenRows,
      "Sem teses pós go-live no momento.",
    );
  }
  if (legacyBody && !historicalBody && !currentBody) {
    legacyBody.innerHTML = renderRows(rows, "Sem resultados de teses no momento.");
  }
}

function renderDashboard(data) {
  renderThesisHistoryOverview(data);
  renderPhaseSummaries(data);
  renderThesisOpenOperations(data);
}

function renderDashboardFallback(message = "Dashboard temporariamente indisponível.") {
  renderDashboard({
    investor_profile: "Indisponível",
    open_positions: [],
    latest_signals: [],
    latest_backtests: [],
    alert_events: [],
    kill_switches: [],
    circuit_breaker: { status: "unknown" },
    market_coverage: null,
    data_quality_gate: null,
    phase_kickoff_date: "2026-04-27",
    historical_analysis_summary: null,
    current_simulation_summary: null,
    current_simulation_daily: [],
    thesis_history_overview: null,
    thesis_executive_summary: null,
    thesis_open_operations: [],
  });

  const summaryNode = byId("dashboard-current-summary");
  if (summaryNode) {
    summaryNode.innerHTML = `
      <div class="list-row">
        <p class="list-meta">${escapeHtml(message)}</p>
      </div>
    `;
  }
}

function updateClock() {
  const node = byId("clock-value");
  if (!node) {
    return;
  }
  node.textContent = new Date().toLocaleString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    day: "2-digit",
    month: "2-digit",
  });
}

function setFeedPill(status, label) {
  const pill = byId("feed-pill");
  const text = byId("feed-pill-label");
  if (!pill || !text) {
    return;
  }
  pill.classList.remove("feed-success", "feed-warning", "feed-danger");
  if (status === "success") {
    pill.classList.add("feed-success");
  } else if (status === "danger") {
    pill.classList.add("feed-danger");
  } else {
    pill.classList.add("feed-warning");
  }
  text.textContent = label;
}

async function refreshFeedStatus() {
  try {
    const health = await apiRequest("GET", "/api/market/feed/health", null, { auth: false });
    const providers = Array.isArray(health?.providers) ? health.providers : [];
    const summary = health?.summary || {};
    if (providers.length === 0) {
      setFeedPill("warning", "Feed sem telemetria");
      return;
    }
    if (Number(summary.critical_count || 0) > 0) {
      setFeedPill("danger", `Feed crítico (${summary.critical_count})`);
      return;
    }
    if (Number(summary.warning_count || 0) > 0) {
      setFeedPill("warning", `Feed em alerta (${summary.warning_count})`);
      return;
    }
    const maxLag = providers.reduce((acc, item) => {
      const current = Number(item.tick_lag_seconds || 0);
      return Number.isFinite(current) && current > acc ? current : acc;
    }, 0);
    setFeedPill("success", `Feed ativo · lag máx ${formatNumber(maxLag)}s`);
  } catch {
    setFeedPill("danger", "Feed indisponível");
  }
}

function switchView(viewId) {
  document.querySelectorAll("[data-view-button]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.viewButton === viewId);
  });

  document.querySelectorAll("[data-view]").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.view === viewId);
  });

  const meta = viewMeta[viewId] || viewMeta.dashboard;
  const titleNode = byId("topbar-title");
  const subtitleNode = byId("topbar-subtitle");
  if (titleNode) {
    titleNode.textContent = meta.title;
  }
  if (subtitleNode) {
    subtitleNode.textContent = meta.subtitle;
  }

  if (window.innerWidth <= 1023) {
    document.body.classList.remove("sidebar-open");
  }
}

function restoreSidebarState() {
  const sidebar = byId("sidebar");
  if (!sidebar) {
    return;
  }
  if (window.innerWidth < 1024) {
    sidebar.classList.add("is-collapsed");
    return;
  }
  if (localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1") {
    sidebar.classList.add("is-collapsed");
  }
}

function ensureLucideIcons() {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }
}

function updateUserChip() {
  const user = state.user || getAuthUser();
  if (!user) {
    return;
  }
  const full = String(user.full_name || user.email || "Usuário");
  const firstName = full.split(" ")[0];
  const initial = firstName.charAt(0).toUpperCase();
  const avatarNode = byId("user-avatar-initial");
  const nameNode = byId("user-display-name");
  if (avatarNode) {
    avatarNode.textContent = initial || "U";
  }
  if (nameNode) {
    nameNode.textContent = firstName || "Usuário";
  }
}

function bindNavigation() {
  document.querySelectorAll("[data-view-button]").forEach((button) => {
    button.addEventListener("click", () => {
      switchView(button.dataset.viewButton);
    });
  });

  const sidebarToggle = byId("sidebar-toggle");
  const sidebar = byId("sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      if (window.innerWidth <= 1023) {
        document.body.classList.toggle("sidebar-open");
        return;
      }
      const isCollapsed = sidebar.classList.toggle("is-collapsed");
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, isCollapsed ? "1" : "0");
      ensureLucideIcons();
    });
  }

  const logoutButton = byId("logout-btn");
  if (logoutButton) {
    logoutButton.addEventListener("click", () => {
      if (!AUTH_REQUIRED) {
        enableAnonymousSession();
        hideAuthGate();
        updateUserChip();
        switchView("finvest");
        void loadDashboard();
        showToast("info", "Sessao reiniciada.");
      } else {
        clearSession();
        showAuthGate();
        showAuthPanel("login");
        showToast("info", "Sessao encerrada.");
      }
    });
  }
}

function showAuthPanel(panelName) {
  const tabs = byId("auth-tabs");
  const panelIds = ["auth-panel-login", "auth-panel-signup", "auth-panel-mfa"];
  panelIds.forEach((panelId) => {
    const panel = byId(panelId);
    if (!panel) {
      return;
    }
    const isTarget = panelId === `auth-panel-${panelName}`;
    panel.classList.toggle("is-active", isTarget);
    if (panelId === "auth-panel-mfa") {
      panel.style.display = isTarget ? "block" : "none";
    }
  });

  if (tabs) {
    tabs.style.display = panelName === "mfa" ? "none" : "flex";
    tabs.querySelectorAll(".auth-tab").forEach((tab) => {
      tab.classList.toggle("is-active", tab.dataset.authTab === panelName);
    });
  }
}

function bindAuthTabs() {
  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      showAuthPanel(button.dataset.authTab || "login");
    });
  });
}

function bindPasswordToggles() {
  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = byId(button.dataset.togglePassword);
      if (!input) {
        return;
      }
      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      button.setAttribute("aria-label", isPassword ? "Ocultar senha" : "Mostrar senha");
    });
  });
}

function createMfaInputs() {
  const container = byId("mfa-inputs");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  for (let index = 0; index < 6; index += 1) {
    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 1;
    input.inputMode = "numeric";
    input.className = "mfa-digit";
    input.setAttribute("aria-label", `Dígito ${index + 1} do código MFA`);
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "");
      if (input.value && index < 5) {
        const next = container.children[index + 1];
        if (next && typeof next.focus === "function") {
          next.focus();
        }
      }
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !input.value && index > 0) {
        const previous = container.children[index - 1];
        if (previous && typeof previous.focus === "function") {
          previous.focus();
        }
      }
    });
    container.appendChild(input);
  }
  const first = container.children[0];
  if (first && typeof first.focus === "function") {
    first.focus();
  }
}

function readMfaCode() {
  const digits = Array.from(document.querySelectorAll("#mfa-inputs .mfa-digit"));
  return digits.map((node) => String(node.value || "")).join("");
}

function showMfaStep({ mode, userId = null } = { mode: "login", userId: null }) {
  const panel = byId("auth-panel-mfa");
  if (!panel) {
    return;
  }
  panel.dataset.mode = mode;
  if (userId !== null) {
    panel.dataset.userId = String(userId);
  } else {
    panel.dataset.userId = "";
  }
  createMfaInputs();
  showAuthPanel("mfa");
}

function completeLogin(loginResult, fallback = {}) {
  const token = loginResult?.access_token;
  if (!token) {
    throw new Error("Resposta de autenticação sem token.");
  }
  const payload = decodeJwtPayload(token) || {};
  const userData = {
    sub: Number(payload.sub || loginResult.user_id || fallback.sub || 0),
    email: String(payload.email || loginResult.email || fallback.email || ""),
    full_name: String(fallback.full_name || fallback.name || "Usuário"),
  };
  saveSession(token, userData);
  state.pendingLogin = null;
  hideAuthGate();
  updateUserChip();
  switchView("finvest");
  checkAndShowOnboarding();
  void loadDashboard();
  void refreshFeedStatus();
}

function updateWizardSteps(activeIndex) {
  document.querySelectorAll("#wizard-steps .wizard-dot").forEach((dot, index) => {
    dot.classList.toggle("is-active", index === activeIndex);
  });
  document.querySelectorAll(".wizard-panel").forEach((panel, index) => {
    panel.classList.toggle("is-active", index === activeIndex);
  });

  if (activeIndex === 0) {
    const welcome = byId("wizard-welcome-msg");
    const user = state.user || getAuthUser();
    if (welcome && user?.full_name) {
      welcome.textContent = `Olá, ${user.full_name}. Vamos configurar seu perfil de investidor.`;
    }
  }
}

function showOnboardingWizard() {
  const wizard = byId("onboarding-wizard");
  if (!wizard) {
    return;
  }
  wizard.style.display = "flex";
  updateWizardSteps(0);
}

function hideOnboardingWizard() {
  const wizard = byId("onboarding-wizard");
  if (!wizard) {
    return;
  }
  wizard.style.display = "none";
  const userId = getAuthUserId();
  if (userId) {
    sessionStorage.setItem(`wizard_done_${userId}`, "1");
  }
}

function checkAndShowOnboarding() {
  if (!PROFILE_CONFIRMATION_REQUIRED) {
    return;
  }
  const userId = getAuthUserId();
  if (!userId) {
    return;
  }
  const wizardDone = sessionStorage.getItem(`wizard_done_${userId}`);
  if (wizardDone) {
    return;
  }
  showOnboardingWizard();
}

function collectSuitabilityPayload() {
  const getSelectedValue = (fieldName) => {
    const selected = document.querySelector(
      `.suit-options[data-field="${fieldName}"] .suit-option.is-selected`,
    );
    return selected?.dataset.value || "";
  };

  return {
    user_id: getAuthUserId(),
    time_horizon: getSelectedValue("time_horizon"),
    risk_tolerance: getSelectedValue("risk_tolerance"),
    investment_experience: getSelectedValue("investment_experience"),
    liquidity_need: "media",
  };
}

function renderProfileSummary(payload, result) {
  const summary = byId("profile-summary");
  if (!summary) {
    return;
  }
  const labels = {
    time_horizon: {
      curto: "Curto prazo",
      medio: "Médio prazo",
      longo: "Longo prazo",
    },
    risk_tolerance: {
      baixa: "Conservador",
      media: "Moderado",
      alta: "Arrojado",
    },
    investment_experience: {
      iniciante: "Iniciante",
      intermediaria: "Intermediário",
      avancada: "Avançado",
    },
  };
  const chips = [
    ["Horizonte", labels.time_horizon[payload.time_horizon] || payload.time_horizon],
    ["Perfil", labels.risk_tolerance[payload.risk_tolerance] || payload.risk_tolerance],
    [
      "Experiência",
      labels.investment_experience[payload.investment_experience] || payload.investment_experience,
    ],
    ["Resultado", result?.investor_profile || "Perfil registrado"],
  ];
  summary.innerHTML = chips
    .map(
      ([label, value]) => `
      <div class="profile-chip">
        <span class="chip-label">${escapeHtml(label)}</span>
        <span class="chip-value">${escapeHtml(value)}</span>
      </div>
    `,
    )
    .join("");
}

function bindWizardHandlers() {
  const next0 = byId("wizard-next-0");
  if (next0) {
    next0.addEventListener("click", () => updateWizardSteps(1));
  }
  const back1 = byId("wizard-back-1");
  if (back1) {
    back1.addEventListener("click", () => updateWizardSteps(0));
  }
  const finish = byId("wizard-finish");
  if (finish) {
    finish.addEventListener("click", () => {
      hideOnboardingWizard();
      showToast("success", "Perfil concluído. Bem-vindo à plataforma.");
    });
  }

  document.querySelectorAll(".suit-options").forEach((group) => {
    group.querySelectorAll(".suit-option").forEach((button) => {
      button.addEventListener("click", () => {
        group.querySelectorAll(".suit-option").forEach((candidate) => {
          candidate.classList.remove("is-selected");
        });
        button.classList.add("is-selected");
      });
    });
  });

  const suitabilityForm = byId("suitability-form");
  if (suitabilityForm) {
    suitabilityForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = byId("wizard-next-1");
      setButtonLoading(submit, true, "Salvando...");
      try {
        const payload = collectSuitabilityPayload();
        if (!payload.user_id) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const result = await apiRequest("POST", "/api/suitability", payload);
        renderProfileSummary(payload, result);
        updateWizardSteps(2);
      } catch (error) {
        showToast("error", `Falha ao salvar suitability: ${error.message}`);
      } finally {
        setButtonLoading(submit, false);
      }
    });
  }
}

function bindAuthHandlers() {
  bindAuthTabs();
  bindPasswordToggles();

  const forgotLink = byId("forgot-password-link");
  if (forgotLink) {
    forgotLink.addEventListener("click", (event) => {
      event.preventDefault();
      showToast("info", "Fluxo de recuperação será disponibilizado em breve.");
    });
  }

  const mfaResendLink = byId("mfa-resend-link");
  if (mfaResendLink) {
    mfaResendLink.addEventListener("click", (event) => {
      event.preventDefault();
      createMfaInputs();
      showToast("info", "Digite o novo código do seu app autenticador.");
    });
  }

  const signupForm = byId("signup-form");
  if (signupForm) {
    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = byId("signup-submit-btn");
      setButtonLoading(button, true, "Criando conta...");
      try {
        const form = new FormData(event.currentTarget);
        const payload = {
          full_name: String(form.get("full_name") || "").trim(),
          tenant_name: String(form.get("tenant_name") || "").trim(),
          email: String(form.get("email") || "").trim(),
          password: String(form.get("password") || ""),
          accepted_terms: form.get("accepted_terms") === "on",
          accepted_privacy: form.get("accepted_privacy") === "on",
        };
        const signupResult = await apiRequest("POST", "/api/auth/signup", payload, {
          auth: false,
          timeoutMs: 20000,
        });
        const loginResult = await apiRequest(
          "POST",
          "/api/auth/login",
          {
            email: payload.email,
            password: payload.password,
          },
          { auth: false, timeoutMs: 20000 },
        );
        completeLogin(loginResult, {
          sub: signupResult.user_id,
          email: signupResult.email,
          full_name: payload.full_name,
        });
        showToast("success", "Conta criada e sessão autenticada.");
      } catch (error) {
        showToast("error", `Falha no cadastro: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const loginForm = byId("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = byId("login-submit-btn");
      setButtonLoading(button, true, "Entrando...");
      const form = new FormData(event.currentTarget);
      const email = String(form.get("email") || "").trim();
      const password = String(form.get("password") || "");
      try {
        const loginResult = await apiRequest(
          "POST",
          "/api/auth/login",
          { email, password },
          { auth: false, timeoutMs: 20000 },
        );
        completeLogin(loginResult, { email });
        showToast("success", "Login concluído.");
      } catch (error) {
        if (String(error.message || "").toLowerCase().includes("mfa")) {
          state.pendingLogin = { email, password };
          showMfaStep({ mode: "login" });
          showToast("warning", "MFA obrigatório. Digite o código para continuar.");
        } else {
          showToast("error", `Falha no login: ${error.message}`);
        }
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const mfaVerifyForm = byId("mfa-verify-form");
  if (mfaVerifyForm) {
    mfaVerifyForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = byId("mfa-submit-btn");
      setButtonLoading(button, true, "Validando...");
      try {
        const otpCode = readMfaCode();
        if (!/^\d{6}$/.test(otpCode)) {
          throw new Error("Informe os 6 dígitos do código MFA.");
        }
        const panel = byId("auth-panel-mfa");
        const mode = panel?.dataset.mode || "login";
        if (mode === "login") {
          if (!state.pendingLogin) {
            throw new Error("Fluxo de login MFA não encontrado. Faça login novamente.");
          }
          const result = await apiRequest(
            "POST",
            "/api/auth/login",
            {
              email: state.pendingLogin.email,
              password: state.pendingLogin.password,
              otp_code: otpCode,
            },
            { auth: false, timeoutMs: 20000 },
          );
          completeLogin(result, { email: state.pendingLogin.email });
          showToast("success", "MFA validado com sucesso.");
        } else {
          const userId = Number(panel?.dataset.userId || getAuthUserId());
          if (!Number.isFinite(userId)) {
            throw new Error("Usuário inválido para validação MFA.");
          }
          const result = await apiRequest(
            "POST",
            "/api/auth/mfa/verify",
            { user_id: userId, otp_code: otpCode },
            { auth: false, timeoutMs: 20000 },
          );
          setOutput("market-output", result);
          showAuthPanel("login");
          showToast("success", "MFA habilitado com sucesso.");
        }
      } catch (error) {
        showToast("error", `Falha na validação MFA: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }
}

function syncSignalId(signalId) {
  const parsed = Number(signalId);
  state.signalId = Number.isFinite(parsed) ? parsed : null;
  const hidden = byId("paper-signal-id");
  const display = byId("paper-signal-id-display");
  if (hidden) {
    hidden.value = state.signalId ? String(state.signalId) : "";
  }
  if (display) {
    display.value = state.signalId ? String(state.signalId) : "";
  }
}

function bindTickerSelector() {
  const pills = document.querySelectorAll("#ticker-selector .ticker-pill");
  if (!pills.length) {
    return;
  }
  const applyTicker = (ticker) => {
    state.selectedTicker = ticker;
    pills.forEach((pill) => {
      pill.classList.toggle("is-active", pill.dataset.ticker === ticker);
    });
    const marketInstrument = document.querySelector('#signal-form input[name="instrument"]');
    if (marketInstrument) {
      marketInstrument.value = ticker;
    }
    const backtestInstrument = document.querySelector('#backtest-form input[name="instrument"]');
    if (backtestInstrument) {
      backtestInstrument.value = ticker;
    }
    const breakerInstrument = document.querySelector('#circuit-breaker-form input[name="instrument"]');
    if (breakerInstrument) {
      breakerInstrument.value = ticker;
    }
    const recomputeButton = byId("recompute-indicators");
    if (recomputeButton) {
      recomputeButton.textContent = `Recalcular indicadores ${ticker}`;
    }
  };

  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      applyTicker(String(pill.dataset.ticker || "PETR4").toUpperCase());
    });
  });
  applyTicker(state.selectedTicker);
}

function bindMarketHandlers() {
  bindTickerSelector();

  const b3Form = byId("b3-universe-sync-form");
  if (b3Form) {
    b3Form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Sincronizando...");
      try {
        const form = Object.fromEntries(new FormData(event.currentTarget).entries());
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const payload = {
          user_id: userId,
          start_year: Number(form.start_year),
          end_year: Number(form.end_year),
          max_days_per_instrument_per_year: Number(form.max_days_per_instrument_per_year),
          max_instruments: Number(form.max_instruments),
          allowed_bdi_codes: ["02", "12", "14", "34"],
          allowed_market_types: ["010"],
        };
        const result = await apiRequest("POST", "/api/market/external/b3/sync-universe-range", payload);
        setOutput("market-output", result);
        showToast(
          "success",
          `Histórico B3 sincronizado: ${formatNumber(result.sync_result?.inserted || 0)} inserts.`,
        );
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha na sincronização B3: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const newsForm = byId("news-sync-form");
  if (newsForm) {
    newsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Buscando notícias...");
      try {
        const form = new FormData(event.currentTarget);
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const instruments = String(form.get("instruments") || "")
          .split(",")
          .map((item) => item.trim().toUpperCase())
          .filter(Boolean);
        if (instruments.length === 0) {
          throw new Error("Informe ao menos um ticker.");
        }
        const payload = {
          user_id: userId,
          start_date: String(form.get("start_date") || ""),
          end_date: String(form.get("end_date") || ""),
          instruments,
          max_articles_per_instrument: Number(form.get("max_articles_per_instrument") || 80),
          language: "pt-BR",
        };
        const result = await apiRequest("POST", "/api/news/external/sync-period", payload);
        setOutput("market-output", result);
        showToast(
          "success",
          `Notícias reais sincronizadas: ${formatNumber(result.inserted || 0)} inseridas.`,
        );
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha na sincronização de notícias: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const recomputeOne = byId("recompute-indicators");
  if (recomputeOne) {
    recomputeOne.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      setButtonLoading(button, true, "Recalculando...");
      try {
        const result = await apiRequest("POST", "/api/analysis/indicators/recompute", {
          instrument: state.selectedTicker,
        });
        setOutput("market-output", result);
        showToast("success", `Indicadores ${state.selectedTicker} atualizados.`);
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha no recálculo: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const recomputeBatch = byId("recompute-batch");
  if (recomputeBatch) {
    recomputeBatch.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      setButtonLoading(button, true, "Recalculando...");
      try {
        const result = await apiRequest("POST", "/api/analysis/indicators/recompute-batch", {
          instruments: ["PETR4", "VALE3"],
        });
        setOutput("market-output", { total: result.length, instrumentos: result.map((item) => item.instrument) });
        showToast("success", "Batch de indicadores atualizado.");
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha no recálculo batch: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const refreshFeedButton = byId("refresh-feed-health");
  if (refreshFeedButton) {
    refreshFeedButton.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      setButtonLoading(button, true, "Atualizando...");
      try {
        const [health, coverage, gate] = await Promise.all([
          apiRequest("GET", "/api/market/feed/health", null, { auth: false }),
          apiRequest("GET", "/api/market/universe/coverage", null, { auth: false }),
          apiRequest("GET", "/api/data-quality/gate", null, { auth: false }),
        ]);
        setOutput("market-output", {
          health: health.summary,
          coverage: coverage.total_instruments_covered,
          quality_gate: gate.summary,
        });
        renderCoverage(coverage);
        renderDataQualityGate(gate);
        showToast("success", "Saúde e cobertura do feed atualizadas.");
        await refreshFeedStatus();
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha ao atualizar feed: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const intradayForm = byId("intraday-fetch-form");
  if (intradayForm) {
    intradayForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Ingerindo...");
      try {
        const form = new FormData(event.currentTarget);
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const instruments = String(form.get("instruments") || "")
          .split(",")
          .map((item) => item.trim().toUpperCase())
          .filter(Boolean);
        if (instruments.length === 0) {
          throw new Error("Informe ao menos um ativo no formato PETR4,KNRI11,BOVA11.");
        }
        const payload = {
          user_id: userId,
          provider_name: String(form.get("provider_name") || "finnhub").trim(),
          instruments,
          auto_recompute_indicators: form.get("auto_recompute_indicators") === "on",
        };
        const result = await apiRequest("POST", "/api/market/intraday/fetch-live", payload);
        setOutput("market-output", result);
        showToast(
          "success",
          `Ingestão intraday concluída: ${formatNumber(result.processed_count || 0)} ativos.`,
        );
        await refreshFeedStatus();
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha na ingestão intraday: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const signalForm = byId("signal-form");
  if (signalForm) {
    signalForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = byId("generate-signal");
      setButtonLoading(button, true, "Gerando...");
      try {
        const form = Object.fromEntries(new FormData(event.currentTarget).entries());
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const result = await apiRequest("POST", "/api/signals/generate", {
          user_id: userId,
          instrument: String(form.instrument || state.selectedTicker).toUpperCase(),
        });
        syncSignalId(result.signal_id);
        setOutput("market-output", result);
        showToast("success", "Sinal gerado e vinculado ao formulário de ordem.");
      } catch (error) {
        setOutput("market-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha ao gerar sinal: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }
}

function bindOperationsHandlers() {
  const sideButtons = document.querySelectorAll("#order-side-selector .side-btn");
  const sideHidden = byId("order-side-hidden");
  sideButtons.forEach((button) => {
    button.addEventListener("click", () => {
      sideButtons.forEach((candidate) => candidate.classList.remove("is-active"));
      button.classList.add("is-active");
      if (sideHidden) {
        sideHidden.value = String(button.dataset.side || "BUY");
      }
    });
  });

  const orderForm = byId("paper-order-form");
  if (orderForm) {
    orderForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Simulando...");
      try {
        const form = Object.fromEntries(new FormData(event.currentTarget).entries());
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const signalId = Number(form.signal_id || state.signalId);
        if (!Number.isFinite(signalId)) {
          throw new Error("Gere um sinal na aba Mercado antes de simular ordem.");
        }
        const quantity = Number(form.quantity);
        if (!Number.isFinite(quantity) || quantity <= 0) {
          throw new Error("Informe uma quantidade válida.");
        }
        const side = String(form.side || "BUY").toUpperCase();
        const result = await apiRequest("POST", `/api/paper/orders/from-signal/${signalId}`, {
          user_id: userId,
          quantity,
        });
        setOutput("order-output", {
          ...result,
          side,
        });
        showToast("success", "Ordem simulada registrada.");
        await loadDashboard();
      } catch (error) {
        setOutput("order-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha na ordem simulada: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }
}

async function loadDashboard() {
  const userId = getAuthUserId();
  if (!userId) {
    renderDashboardFallback("Sessao expirada. Faca login novamente para carregar as teses.");
    return;
  }
  if (!state.dashboardSnapshot) {
    renderDashboardLoading();
  }
  try {
    const result = await apiRequest("GET", `/api/dashboard/summary/${userId}`, null, {
      timeoutMs: 30000,
    });
    state.dashboardSnapshot = result;
    renderDashboard(result);
  } catch (error) {
    showToast("error", `Falha ao carregar dashboard: ${error.message}`);
    if (state.dashboardSnapshot) {
      renderDashboard(state.dashboardSnapshot);
      return;
    }
    renderDashboardFallback("Não foi possível carregar os dados agora. Tente novamente.");
  }
}


function bindDashboardHandlers() {
  const refreshButton = byId("dashboard-refresh");
  if (!refreshButton) {
    return;
  }
  refreshButton.addEventListener("click", async () => {
    setButtonLoading(refreshButton, true, "Atualizando...");
    try {
      await loadDashboard();
    } finally {
      setButtonLoading(refreshButton, false);
    }
  });
}

function renderBacktestMetrics(detail) {

  const node = byId("backtest-metrics");
  if (!node) {
    return;
  }
  const performance = detail?.validation_snapshot?.performance || {};
  const riskFlags = Array.isArray(detail?.validation_snapshot?.risk_flags)
    ? detail.validation_snapshot.risk_flags
    : [];
  const cards = [
    { label: "Retorno total", value: formatPercent(detail?.total_return_pct || 0), tone: "tone-accent" },
    { label: "Win rate", value: formatPercent(detail?.win_rate || 0), tone: "tone-warning" },
    { label: "Max drawdown", value: formatPercent(detail?.max_drawdown_pct || 0), tone: "tone-danger" },
    { label: "Sharpe", value: valueAsString(performance.sharpe_ratio), tone: "tone-accent" },
    { label: "Profit factor", value: valueAsString(performance.profit_factor), tone: "tone-success" },
    { label: "Flags", value: riskFlags.length ? riskFlags.join(", ") : "Sem flags", tone: "tone-warning" },
  ];
  node.innerHTML = cards
    .map(
      (card) => `
      <article class="metric-card">
        <p class="metric-label">${escapeHtml(card.label)}</p>
        <p class="metric-value ${card.tone} mono">${escapeHtml(card.value)}</p>
      </article>
    `,
    )
    .join("");
}

function bindBacktestHandlers() {
  const backtestForm = byId("backtest-form");
  if (!backtestForm) {
    return;
  }
  backtestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('button[type="submit"]');
    setButtonLoading(button, true, "Rodando...");
    try {
      const form = Object.fromEntries(new FormData(event.currentTarget).entries());
      const userId = getAuthUserId();
      if (!userId) {
        throw new Error("Sessão inválida. Faça login novamente.");
      }
      const run = await apiRequest("POST", "/api/backtests/run", {
        user_id: userId,
        instrument: String(form.instrument || state.selectedTicker).toUpperCase(),
        quantity: Number(form.quantity),
      });
      let detail = run;
      if (run.run_id) {
        detail = await apiRequest("GET", `/api/backtests/${run.run_id}`);
      }
      renderBacktestMetrics(detail);
      setOutput("backtest-output", {
        run_id: detail.run_id,
        trade_count: detail.trade_count,
        total_return_pct: detail.total_return_pct,
        max_drawdown_pct: detail.max_drawdown_pct,
      });
      showToast("success", "Backtest concluído.");
      await loadDashboard();
    } catch (error) {
      setOutput("backtest-output", { erro: error.message, detalhe: error.data || null });
      showToast("error", `Falha no backtest: ${error.message}`);
    } finally {
      setButtonLoading(button, false);
    }
  });
}

function renderCircuitBreakerStatus(instrument, data) {
  const container = byId("circuit-breaker-result");
  if (!container) {
    return;
  }
  const status = String(data.status || "clear").toLowerCase();
  const isClear = status === "clear";
  container.innerHTML = `
    <div class="status-card ${isClear ? "status-ok" : "status-alert"}">
      <span class="status-ticker">${escapeHtml(instrument)}</span>
      <span class="status-tag">${escapeHtml(status.toUpperCase())}</span>
      <p class="status-reason">${escapeHtml(data.reason || "Sem restrições ativas para o ativo.")}</p>
    </div>
  `;
}

function bindRiskHandlers() {
  const circuitForm = byId("circuit-breaker-form");
  if (circuitForm) {
    circuitForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Consultando...");
      try {
        const instrument = String(new FormData(event.currentTarget).get("instrument") || state.selectedTicker).toUpperCase();
        const result = await apiRequest("GET", `/api/risk/circuit-breaker/${instrument}`, null, {
          auth: false,
        });
        renderCircuitBreakerStatus(instrument, result);
        showToast("success", "Status de circuito consultado.");
      } catch (error) {
        renderKeyValueCard("circuit-breaker-result", { erro: error.message });
        showToast("error", `Falha ao consultar circuito: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const scopeButtons = document.querySelectorAll("#ks-scope-selector .pill-option");
  const scopeHidden = byId("ks-scope-hidden");
  const scopeIdInput = document.querySelector('#kill-switch-form input[name="scope_id"]');
  scopeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      scopeButtons.forEach((candidate) => candidate.classList.remove("is-active"));
      button.classList.add("is-active");
      if (scopeHidden) {
        scopeHidden.value = String(button.dataset.value || "user");
      }
      if (scopeIdInput && scopeHidden?.value === "user") {
        const userId = getAuthUserId();
        if (userId) {
          scopeIdInput.value = String(userId);
        }
      }
    });
  });

  const releaseButton = byId("ks-release-btn");
  if (releaseButton) {
    releaseButton.addEventListener("click", () => {
      const statusHidden = byId("ks-status-hidden");
      if (statusHidden) {
        statusHidden.value = "released";
      }
      const form = byId("kill-switch-form");
      if (form && typeof form.requestSubmit === "function") {
        form.requestSubmit();
      }
    });
  }

  const activateButton = byId("ks-activate-btn");
  if (activateButton) {
    activateButton.addEventListener("click", () => {
      const statusHidden = byId("ks-status-hidden");
      if (statusHidden) {
        statusHidden.value = "active";
      }
    });
  }

  const killSwitchForm = byId("kill-switch-form");
  if (killSwitchForm) {
    killSwitchForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = String(byId("ks-status-hidden")?.value || "active");
      if (status === "active") {
        const confirmed = window.confirm(
          "ATENÇÃO: Ativar o kill-switch bloqueará operações no escopo selecionado.\n\nDeseja confirmar?",
        );
        if (!confirmed) {
          return;
        }
      }
      const button = status === "active" ? byId("ks-activate-btn") : byId("ks-release-btn");
      setButtonLoading(button, true);
      try {
        const form = Object.fromEntries(new FormData(event.currentTarget).entries());
        if (form.scope_type === "user" && !form.scope_id) {
          const userId = getAuthUserId();
          if (!userId) {
            throw new Error("Sessão inválida. Faça login novamente.");
          }
          form.scope_id = String(userId);
        }
        const updated = await apiRequest("POST", "/api/risk/kill-switch", form);
        const states = await apiRequest("GET", "/api/risk/kill-switch");
        setOutput("kill-switch-output", {
          atualizado: updated.status,
          escopo: `${updated.scope_type}:${updated.scope_id}`,
          total_registros: Array.isArray(states) ? states.length : 0,
        });
        showToast("success", "Kill-switch atualizado.");
        await loadDashboard();
      } catch (error) {
        setOutput("kill-switch-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha no kill-switch: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }
}

function renderActiveAlerts(events) {
  const node = byId("active-alerts-list");
  if (!node) {
    return;
  }
  if (!Array.isArray(events) || events.length === 0) {
    node.innerHTML = "<p class='empty-hint'>Nenhum alerta ativo/evento recente.</p>";
    return;
  }
  node.innerHTML = events
    .map(
      (event) => `
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">${escapeHtml(event.event_type || "alerta")}</p>
          <p class="list-meta">${escapeHtml(event.instrument || "geral")}</p>
        </div>
        <p class="list-meta">${escapeHtml(formatDate(event.created_at))}</p>
      </div>
    `,
    )
    .join("");
}

function whatsappCategoriesFromForm() {
  return {
    thesis_new: Boolean(byId("wa-cat-thesis-new")?.checked),
    thesis_update: Boolean(byId("wa-cat-thesis-update")?.checked),
    stock_alert: Boolean(byId("wa-cat-stock-alert")?.checked),
    daily_digest: Boolean(byId("wa-cat-daily-digest")?.checked),
  };
}

function whatsappThresholdsFromForm() {
  const valueFrom = (id, fallback) => {
    const parsed = Number(byId(id)?.value || fallback);
    return Number.isFinite(parsed) ? parsed : fallback;
  };
  return {
    thesis_confidence_pct: valueFrom("wa-thesis-confidence", 55),
    thesis_expected_pct: valueFrom("wa-thesis-expected", 0),
    thesis_progress_delta_pct: 20,
    stock_price_move_pct: valueFrom("wa-stock-move", 3),
    news_magnitude: valueFrom("wa-news-magnitude", 0.75),
    signal_confidence: 0.6,
  };
}

function applyWhatsAppSettings(settings) {
  if (!settings || typeof settings !== "object") {
    return;
  }
  const categories = settings.categories || {};
  const thresholds = settings.thresholds || {};
  if (byId("whatsapp-phone-number")) {
    byId("whatsapp-phone-number").value = settings.phone_number || "";
  }
  if (byId("whatsapp-display-name")) {
    byId("whatsapp-display-name").value = settings.display_name || "";
  }
  if (byId("whatsapp-opt-in")) {
    byId("whatsapp-opt-in").checked = Boolean(settings.opt_in);
  }
  const checkboxMap = {
    "wa-cat-thesis-new": categories.thesis_new,
    "wa-cat-thesis-update": categories.thesis_update,
    "wa-cat-stock-alert": categories.stock_alert,
    "wa-cat-daily-digest": categories.daily_digest,
  };
  Object.entries(checkboxMap).forEach(([id, value]) => {
    if (byId(id)) {
      byId(id).checked = value !== false;
    }
  });
  const thresholdMap = {
    "wa-thesis-confidence": thresholds.thesis_confidence_pct,
    "wa-thesis-expected": thresholds.thesis_expected_pct,
    "wa-stock-move": thresholds.stock_price_move_pct,
    "wa-news-magnitude": thresholds.news_magnitude,
  };
  Object.entries(thresholdMap).forEach(([id, value]) => {
    if (byId(id) && value !== undefined && value !== null) {
      byId(id).value = String(value);
    }
  });
  renderWhatsAppDeliveries(settings.recent_deliveries || []);
  const statusNode = byId("whatsapp-status");
  if (statusNode) {
    const statusText = settings.paused
      ? "Canal pausado por comando WhatsApp."
      : settings.opt_in
        ? "Canal WhatsApp ativo."
        : "Canal WhatsApp sem opt-in.";
    statusNode.innerHTML = `
      <div class="list-row">
        <p class="list-title">${escapeHtml(statusText)}</p>
        <p class="list-meta">${escapeHtml(settings.phone_number || "Telefone nao configurado")}</p>
      </div>
    `;
  }
}

function renderWhatsAppDeliveries(deliveries) {
  const node = byId("whatsapp-deliveries-list");
  if (!node) {
    return;
  }
  if (!Array.isArray(deliveries) || deliveries.length === 0) {
    node.innerHTML = "<p class='empty-hint'>Nenhuma entrega WhatsApp registrada.</p>";
    return;
  }
  node.innerHTML = deliveries
    .map(
      (delivery) => `
        <div class="list-row">
          <div class="list-main">
            <p class="list-title">${escapeHtml(delivery.title || delivery.category || "WhatsApp")}</p>
            <p class="list-meta mono">${escapeHtml(delivery.status || "-")}</p>
          </div>
          <p class="list-meta">${escapeHtml(delivery.instrument || "geral")} | ${escapeHtml(delivery.asset_class_label || "")} | ${escapeHtml(formatDate(delivery.created_at))}</p>
          ${
            delivery.failure_reason
              ? `<p class="list-meta tone-danger">${escapeHtml(delivery.failure_reason)}</p>`
              : ""
          }
        </div>
      `,
    )
    .join("");
}

async function loadWhatsAppSettings() {
  const userId = getAuthUserId();
  if (!userId) {
    return;
  }
  try {
    const settings = await apiRequest("GET", `/api/notifications/whatsapp?user_id=${userId}`);
    applyWhatsAppSettings(settings);
  } catch (error) {
    renderWhatsAppDeliveries([]);
  }
}

async function loadActiveAlerts() {
  const userId = getAuthUserId();
  if (!userId) {
    return;
  }
  try {
    const events = await apiRequest("GET", `/api/alerts/events/${userId}`);
    renderActiveAlerts(events);
  } catch {
    renderActiveAlerts([]);
  }
}

function bindMicrotradesHandlers() {
  const workflowForm = byId("microtrades-workflow-form");
  if (!workflowForm) {
    return;
  }

  const signalInput = byId("microtrades-signal-id");
  const monitorTable = byId("microtrades-monitor-table");
  const statusNode = byId("microtrades-status");

  const errorMessageFrom = (error) =>
    error && typeof error.message === "string" ? error.message : "Erro inesperado.";
  const isSuitabilityMissingError = (error) =>
    /suitability obrigatorio/i.test(errorMessageFrom(error));

  const renderStatus = (rows) => {
    if (!statusNode) {
      return;
    }
    if (!Array.isArray(rows) || rows.length === 0) {
      statusNode.innerHTML = `
        <div class="list-row">
          <p class="list-meta">Configure os ativos e rode o ciclo para gerar casos reais.</p>
        </div>
      `;
      return;
    }
    statusNode.innerHTML = rows
      .map(
        (row) => `
          <div class="list-row">
            <div class="list-main">
              <p class="list-title">${escapeHtml(row.title || "Status")}</p>
              <p class="list-meta ${escapeHtml(row.tone || "")}">${escapeHtml(row.meta || "-")}</p>
            </div>
          </div>
        `,
      )
      .join("");
  };

  const setSingleStatus = (title, meta, tone = "") => {
    renderStatus([{ title, meta, tone }]);
  };

  const parseInstruments = (rawValue) =>
    Array.from(
      new Set(
        String(rawValue || "")
          .split(",")
          .map((item) => item.trim().toUpperCase())
          .filter(Boolean),
      ),
    ).slice(0, 5);

  const buildSymbolOverrides = (instruments) => {
    const overrides = {};
    instruments.forEach((instrument) => {
      if (/(USDT|USDC|BUSD|FDUSD|BTC|ETH)$/.test(instrument) && !instrument.includes("-")) {
        overrides[instrument] = `BINANCE:${instrument}`;
      }
    });
    return Object.keys(overrides).length ? overrides : null;
  };

  const readConfig = () => {
    const userId = getAuthUserId();
    if (!userId) {
      throw new Error("Sessao invalida. Faca login novamente.");
    }
    const form = new FormData(workflowForm);
    const instruments = parseInstruments(form.get("instruments"));
    if (instruments.length === 0) {
      throw new Error("Informe ao menos um ativo (ex: BTCUSDT,ETHUSDT).");
    }
    const providerName = String(form.get("provider_name") || "finnhub").trim() || "finnhub";
    const horizonBars = Number(form.get("horizon_bars") || 8);
    if (!Number.isFinite(horizonBars) || horizonBars < 3 || horizonBars > 30) {
      throw new Error("Horizon bars deve ficar entre 3 e 30.");
    }
    const interval = String(form.get("interval") || "5m").trim();
    const lookbackHours = Number(form.get("lookback_hours") || 168);
    if (!Number.isFinite(lookbackHours) || lookbackHours < 1 || lookbackHours > 24 * 365) {
      throw new Error("Lookback deve ficar entre 1 e 8760 horas.");
    }
    const maxCandles = Number(form.get("max_candles_per_instrument") || 1200);
    if (!Number.isFinite(maxCandles) || maxCandles < 50 || maxCandles > 5000) {
      throw new Error("Max candles por ativo deve ficar entre 50 e 5000.");
    }
    const quantity = Number(form.get("quantity") || 1);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      throw new Error("Quantidade paper invalida.");
    }
    const signalIdRaw = String(form.get("signal_id") || "").trim();
    const parsedSignal = Number(signalIdRaw || state.signalId);
    return {
      userId,
      providerName,
      instruments,
      interval,
      lookbackHours: Math.round(lookbackHours),
      maxCandles: Math.round(maxCandles),
      horizonBars: Math.round(horizonBars),
      quantity,
      signalId: Number.isFinite(parsedSignal) && parsedSignal > 0 ? parsedSignal : null,
      symbolOverrides: buildSymbolOverrides(instruments),
    };
  };

  const syncMicrotradesSignalId = (signalId) => {
    const parsed = Number(signalId);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return;
    }
    if (signalInput) {
      signalInput.value = String(parsed);
    }
    syncSignalId(parsed);
  };

  const renderMonitorTable = (payload) => {
    if (!monitorTable) {
      return;
    }
    const theses = Array.isArray(payload?.theses) ? payload.theses : [];
    if (theses.length === 0) {
      monitorTable.innerHTML = "<tr><td colspan='7'>Sem monitoramento carregado.</td></tr>";
      return;
    }
    monitorTable.innerHTML = theses
      .map((thesis) => {
        const instrument = String(thesis.instrument || "-");
        const direction = String(thesis.direction || "-").toUpperCase();
        const confidenceNow = Number(thesis.confidence_now_pct);
        const confidence = Number.isFinite(confidenceNow)
          ? `${formatMetric(thesis.confidence_tese_pct)}% -> ${formatMetric(confidenceNow)}%`
          : `${formatMetric(thesis.confidence_tese_pct)}%`;
        const expected = formatSignedMetricPercent(thesis.expected_financial_pct);
        const status = String(thesis.executive_status_label || thesis.monitor_status || "-");
        const action = String(thesis.executive_action || thesis.suggested_action || "-");
        const trigger = String(thesis.next_trigger || "");
        const targetStop = `${formatMetric(thesis.target_price)} / ${formatMetric(thesis.stop_price)}`;
        return `
          <tr>
            <td class="mono">${escapeHtml(instrument)}</td>
            <td>${escapeHtml(direction)}</td>
            <td class="mono">${escapeHtml(confidence)}</td>
            <td class="mono">${escapeHtml(expected)}</td>
            <td>
              <strong>${escapeHtml(status)}</strong><br />
              <span class="list-meta">${escapeHtml(action)}</span>
              ${trigger ? `<br /><span class="list-meta">${escapeHtml(trigger)}</span>` : ""}
            </td>
            <td class="mono">${escapeHtml(targetStop)}</td>
            <td class="mono">${escapeHtml(formatDate(thesis.thesis_raised_at))}</td>
          </tr>
        `;
      })
      .join("");
  };

  const runBackfill = async (config, { updateOutput = true } = {}) => {
    const payload = {
      user_id: config.userId,
      provider_name: "binance",
      instruments: config.instruments,
      interval: config.interval,
      lookback_hours: config.lookbackHours,
      max_candles_per_instrument: config.maxCandles,
      auto_recompute_indicators: true,
    };
    if (config.symbolOverrides) {
      payload.symbol_overrides = config.symbolOverrides;
    }
    const result = await apiRequest("POST", "/api/market/crypto/backfill", payload);
    if (updateOutput) {
      setOutput("microtrades-output", {
        etapa: "backfill_historico",
        provider_name: result.provider_name,
        interval: result.interval,
        lookback_hours: result.lookback_hours,
        requested_candles: result.requested_candles,
        processed_count: result.processed_count,
        failed_count: result.failed_count,
      });
    }
    return result;
  };

  const runFetchLive = async (config, { updateOutput = true } = {}) => {
    const payload = {
      user_id: config.userId,
      provider_name: config.providerName,
      instruments: config.instruments,
      auto_recompute_indicators: true,
    };
    if (config.symbolOverrides) {
      payload.symbol_overrides = config.symbolOverrides;
    }
    const result = await apiRequest("POST", "/api/market/intraday/fetch-live", payload);
    if (updateOutput) {
      setOutput("microtrades-output", {
        etapa: "ingestao_intraday",
        provider_name: result.provider_name,
        requested_instruments: result.requested_instruments,
        processed_count: result.processed_count,
        failed_count: result.failed_count,
      });
    }
    return result;
  };

  const runGenerateSignal = async (config, { updateOutput = true } = {}) => {
    const result = await apiRequest("POST", "/api/signals/generate", {
      user_id: config.userId,
      instrument: config.instruments[0],
    });
    syncMicrotradesSignalId(result.signal_id);
    if (updateOutput) {
      setOutput("microtrades-output", {
        etapa: "geracao_tese",
        signal_id: result.signal_id,
        instrument: result.instrument,
        signal_type: result.signal_type,
        confidence: result.confidence,
        expected_return_pct: result.expected_return_pct,
      });
    }
    return result;
  };

  const runCaseStudy = async (config, { updateOutput = true } = {}) => {
    const result = await apiRequest("POST", "/api/theses/case-study", {
      user_id: config.userId,
      instruments: config.instruments,
      horizon_bars: config.horizonBars,
    });
    if (updateOutput) {
      const thesis = result?.selected_case?.thesis || {};
      const kpis = result?.selected_case?.kpis || {};
      setOutput("microtrades-output", {
        etapa: "comprovacao_tese",
        thesis_id: thesis.thesis_id,
        instrument: thesis.instrument,
        direction: thesis.direction,
        confidence_tese_pct: kpis.confidence_tese_pct ?? thesis.confidence_tese_pct,
        expected_financial_pct: kpis.expected_financial_pct ?? thesis.expected_financial_pct,
        realized_financial_pct:
          kpis.realized_financial_pct ?? result?.selected_case?.outcome?.realized_financial_pct,
      });
    }
    return result;
  };

  const ensureSuitabilityProfile = async (config) => {
    const payload = {
      user_id: config.userId,
      time_horizon: "medio",
      risk_tolerance: "media",
      investment_experience: "intermediaria",
      liquidity_need: "media",
    };
    const result = await apiRequest("POST", "/api/suitability", payload);
    return { payload, result };
  };

  const runCaseStudyWithAutoSuitability = async (config, { updateOutput = true } = {}) => {
    try {
      const result = await runCaseStudy(config, { updateOutput });
      return { result, suitabilityAutoCreated: false };
    } catch (error) {
      if (!isSuitabilityMissingError(error)) {
        throw error;
      }
      await ensureSuitabilityProfile(config);
      const retried = await runCaseStudy(config, { updateOutput });
      return { result: retried, suitabilityAutoCreated: true };
    }
  };

  const runMonitor = async (config, { updateOutput = true } = {}) => {
    const result = await apiRequest("POST", "/api/theses/current-monitor", {
      user_id: config.userId,
      instruments: config.instruments,
      horizon_bars: config.horizonBars,
      thesis_count: Math.min(8, Math.max(1, config.instruments.length * 2)),
      recent_bars_window: 7,
    });
    renderMonitorTable(result);
    if (updateOutput) {
      setOutput("microtrades-output", {
        etapa: "monitoramento_atual",
        generated_at: result.generated_at,
        thesis_count: result.thesis_count,
        target_hits: result.summary?.target_hits,
        stop_alerts: result.summary?.stop_alerts,
        monitoring_count: result.summary?.monitoring_count,
        avg_unrealized_financial_pct: result.summary?.avg_unrealized_financial_pct,
      });
    }
    return result;
  };

  const runMonitorWithAutoSuitability = async (config, { updateOutput = true } = {}) => {
    try {
      const result = await runMonitor(config, { updateOutput });
      return { result, suitabilityAutoCreated: false };
    } catch (error) {
      if (!isSuitabilityMissingError(error)) {
        throw error;
      }
      await ensureSuitabilityProfile(config);
      const retried = await runMonitor(config, { updateOutput });
      return { result: retried, suitabilityAutoCreated: true };
    }
  };

  const runMonitorLatest = async ({ updateOutput = true } = {}) => {
    const result = await apiRequest("GET", "/api/theses/current-monitor/latest");
    renderMonitorTable(result);
    if (updateOutput) {
      setOutput("microtrades-output", {
        etapa: "monitoramento_latest",
        generated_at: result.generated_at,
        thesis_count: result.thesis_count,
        target_hits: result.summary?.target_hits,
        stop_alerts: result.summary?.stop_alerts,
        monitoring_count: result.summary?.monitoring_count,
        avg_unrealized_financial_pct: result.summary?.avg_unrealized_financial_pct,
      });
    }
    return result;
  };

  const runPaperOrder = async (config, { updateOutput = true } = {}) => {
    const signalId = Number(config.signalId || state.signalId);
    if (!Number.isFinite(signalId) || signalId <= 0) {
      throw new Error("Informe um signal_id valido para gerar a ordem paper.");
    }
    const result = await apiRequest("POST", `/api/paper/orders/from-signal/${signalId}`, {
      user_id: config.userId,
      quantity: config.quantity,
    });
    if (updateOutput) {
      setOutput("microtrades-output", {
        etapa: "paper_order",
        signal_id: signalId,
        order_id: result.order_id,
        instrument: result.instrument,
        quantity: result.quantity,
        execution_price: result.execution_price,
        estimated_cost: result.estimated_cost,
        risk_status: result.risk_status,
      });
    }
    return result;
  };

  const bindAction = (buttonId, loadingText, handler) => {
    const button = byId(buttonId);
    if (!button) {
      return;
    }
    button.addEventListener("click", async () => {
      setButtonLoading(button, true, loadingText);
      try {
        await handler();
      } catch (error) {
        const message = errorMessageFrom(error);
        setOutput("microtrades-output", { erro: message, detalhe: error?.data || null });
        setSingleStatus("Falha", message, "tone-danger");
        showToast("error", `Falha em microtrades: ${message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  };

  workflowForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = byId("microtrades-run-cycle") || event.currentTarget.querySelector('button[type="submit"]');
    const steps = [];
    const pushStep = (title, meta, tone = "") => {
      steps.push({ title, meta, tone });
      renderStatus(steps);
    };
    setButtonLoading(button, true, "Executando ciclo...");
    try {
      const config = readConfig();
      pushStep(
        "Escopo",
        `${config.instruments.join(", ")} | ${config.interval} | provider ${config.providerName}`,
      );
      let backfill = null;
      try {
        backfill = await runBackfill(config, { updateOutput: false });
        pushStep(
          "0/5 Historico",
          `${formatNumber(backfill.processed_count || 0)} candles importados (${config.lookbackHours}h).`,
        );
      } catch (backfillError) {
        pushStep(
          "0/5 Historico",
          `Backfill automatico indisponivel agora (${errorMessageFrom(backfillError)}). Seguindo com base atual.`,
          "tone-warning",
        );
      }

      let ingest = {
        provider_name: config.providerName,
        processed_count: 0,
        failed_count: 0,
        skipped: false,
      };
      try {
        const ingestResult = await runFetchLive(config, { updateOutput: false });
        ingest = {
          provider_name: ingestResult.provider_name,
          processed_count: ingestResult.processed_count || 0,
          failed_count: ingestResult.failed_count || 0,
          skipped: false,
        };
        pushStep("1/5 Cotacao", `${formatNumber(ingest.processed_count)} ativos processados.`);
      } catch (ingestError) {
        const ingestMessage = errorMessageFrom(ingestError);
        const canSkipLive = ingestMessage.includes("FINNHUB_API_TOKEN");
        if (!canSkipLive) {
          throw ingestError;
        }
        ingest = {
          provider_name: config.providerName,
          processed_count: 0,
          failed_count: 0,
          skipped: true,
        };
        pushStep(
          "1/5 Cotacao",
          "Token Finnhub ausente. Etapa live ignorada e fluxo segue com historico local.",
          "tone-warning",
        );
      }

      const signal = await runGenerateSignal(config, { updateOutput: false });
      pushStep(
        "2/5 Tese",
        `signal_id ${signal.signal_id || "-"} em ${signal.instrument || config.instruments[0]}.`,
      );

      const caseStudyRun = await runCaseStudyWithAutoSuitability(config, { updateOutput: false });
      const caseStudy = caseStudyRun.result;
      if (caseStudyRun.suitabilityAutoCreated) {
        pushStep(
          "Perfil de risco",
          "Suitability nao encontrado. Perfil moderado criado automaticamente para continuar.",
          "tone-warning",
        );
      }
      const selectedThesisId = caseStudy?.selected_case?.thesis?.thesis_id || "-";
      pushStep("3/5 Comprovacao", `Case selecionado: ${selectedThesisId}.`);

      const monitorRun = await runMonitorWithAutoSuitability(config, { updateOutput: false });
      const monitor = monitorRun.result;
      if (monitorRun.suitabilityAutoCreated) {
        pushStep(
          "Perfil de risco",
          "Suitability criado automaticamente antes do monitoramento.",
          "tone-warning",
        );
      }
      pushStep("4/5 Monitoramento", `${formatNumber(monitor.thesis_count || 0)} teses monitoradas.`);

      setOutput("microtrades-output", {
        etapa: "ciclo_completo",
        provider_name: ingest.provider_name,
        instruments: config.instruments,
        interval: config.interval,
        lookback_hours: config.lookbackHours,
        backfill_processed_count: backfill?.processed_count || 0,
        backfill_failed_count: backfill?.failed_count || 0,
        processed_count: ingest.processed_count,
        live_ingestion_skipped: ingest.skipped,
        signal_id: signal.signal_id,
        selected_thesis_id: selectedThesisId,
        monitor_thesis_count: monitor.thesis_count,
        monitor_target_hits: monitor.summary?.target_hits,
        monitor_stop_alerts: monitor.summary?.stop_alerts,
      });
      showToast("success", "Ciclo de microtrades concluido com dados reais.");
    } catch (error) {
      const message = errorMessageFrom(error);
      pushStep("Falha no ciclo", message, "tone-danger");
      setOutput("microtrades-output", { erro: message, detalhe: error?.data || null });
      showToast("error", `Falha no ciclo de microtrades: ${message}`);
    } finally {
      setButtonLoading(button, false);
    }
  });

  bindAction("microtrades-fetch-live", "Ingerindo...", async () => {
    const config = readConfig();
    const result = await runFetchLive(config);
    setSingleStatus(
      "Cotacao carregada",
      `${formatNumber(result.processed_count || 0)} ativos processados (${formatNumber(result.failed_count || 0)} falhas).`,
    );
    showToast("success", "Cotacao intraday atualizada para microtrades.");
  });

  bindAction("microtrades-generate-signal", "Gerando...", async () => {
    const config = readConfig();
    const result = await runGenerateSignal(config);
    setSingleStatus(
      "Tese gerada",
      `Signal ${result.signal_id || "-"} para ${result.instrument || config.instruments[0]}.`,
    );
    showToast("success", "Tese de microtrade gerada.");
  });

  bindAction("microtrades-case-study", "Comprovando...", async () => {
    const config = readConfig();
    const caseStudyRun = await runCaseStudyWithAutoSuitability(config);
    const result = caseStudyRun.result;
    const thesis = result?.selected_case?.thesis || {};
    const kpis = result?.selected_case?.kpis || {};
    setSingleStatus(
      "Tese comprovada",
      `${thesis.thesis_id || "-"} | conf ${formatMetric(kpis.confidence_tese_pct || thesis.confidence_tese_pct || 0)}%`,
    );
    if (caseStudyRun.suitabilityAutoCreated) {
      showToast("info", "Perfil de suitability criado automaticamente (moderado).");
    }
    showToast("success", "Comprovacao de tese concluida.");
  });

  bindAction("microtrades-monitor", "Monitorando...", async () => {
    const config = readConfig();
    const monitorRun = await runMonitorWithAutoSuitability(config);
    const result = monitorRun.result;
    setSingleStatus(
      "Monitor atualizado",
      `${formatNumber(result.thesis_count || 0)} teses | target ${formatNumber(result.summary?.target_hits || 0)} | stop ${formatNumber(result.summary?.stop_alerts || 0)}`,
    );
    if (monitorRun.suitabilityAutoCreated) {
      showToast("info", "Perfil de suitability criado automaticamente (moderado).");
    }
    showToast("success", "Monitoramento atualizado.");
  });

  bindAction("microtrades-monitor-latest", "Carregando...", async () => {
    const result = await runMonitorLatest();
    setSingleStatus(
      "Monitor latest",
      `${formatNumber(result.thesis_count || 0)} teses carregadas de ${formatDate(result.generated_at)}.`,
    );
    showToast("success", "Monitor latest carregado.");
  });

  bindAction("microtrades-paper-order", "Criando ordem...", async () => {
    const config = readConfig();
    const result = await runPaperOrder(config);
    setSingleStatus(
      "Ordem paper criada",
      `order_id ${result.order_id || "-"} | ${result.instrument || "-"} x ${formatNumber(result.quantity || config.quantity)}`,
    );
    showToast("success", "Ordem paper registrada para microtrades.");
  });
}

function bindAlertsHandlers() {
  const whatsappForm = byId("whatsapp-settings-form");
  if (whatsappForm) {
    whatsappForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Salvando...");
      try {
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("SessÃ£o invÃ¡lida. FaÃ§a login novamente.");
        }
        const form = Object.fromEntries(new FormData(event.currentTarget).entries());
        const payload = {
          user_id: userId,
          phone_number: form.phone_number,
          display_name: form.display_name || null,
          opt_in: Boolean(byId("whatsapp-opt-in")?.checked),
          categories: whatsappCategoriesFromForm(),
          thresholds: whatsappThresholdsFromForm(),
        };
        const settings = await apiRequest("PUT", "/api/notifications/whatsapp", payload);
        applyWhatsAppSettings(settings);
        showToast("success", "WhatsApp salvo.");
      } catch (error) {
        setOutput("alerts-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha no WhatsApp: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const thresholdForm = byId("whatsapp-thresholds-form");
  if (thresholdForm) {
    thresholdForm.addEventListener("change", () => {
      const phoneInput = byId("whatsapp-phone-number");
      if (phoneInput?.value) {
        whatsappForm?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
    });
  }

  [
    "wa-cat-thesis-new",
    "wa-cat-thesis-update",
    "wa-cat-stock-alert",
    "wa-cat-daily-digest",
    "whatsapp-opt-in",
  ].forEach((id) => {
    const node = byId(id);
    if (node) {
      node.addEventListener("change", () => {
        const phoneInput = byId("whatsapp-phone-number");
        if (phoneInput?.value) {
          whatsappForm?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      });
    }
  });

  const whatsappTestButton = byId("whatsapp-test-btn");
  if (whatsappTestButton) {
    whatsappTestButton.addEventListener("click", async () => {
      setButtonLoading(whatsappTestButton, true, "Enviando...");
      try {
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("SessÃ£o invÃ¡lida. FaÃ§a login novamente.");
        }
        const result = await apiRequest("POST", "/api/notifications/whatsapp/test", {
          user_id: userId,
        });
        setOutput("alerts-output", result);
        await loadWhatsAppSettings();
        showToast("success", "Teste WhatsApp processado.");
      } catch (error) {
        setOutput("alerts-output", { erro: error.message, detalhe: error.data || null });
        await loadWhatsAppSettings();
        showToast("error", `Falha no teste WhatsApp: ${error.message}`);
      } finally {
        setButtonLoading(whatsappTestButton, false);
      }
    });
  }

  const whatsappRefreshButton = byId("whatsapp-refresh-btn");
  if (whatsappRefreshButton) {
    whatsappRefreshButton.addEventListener("click", async () => {
      setButtonLoading(whatsappRefreshButton, true, "Atualizando...");
      try {
        await loadWhatsAppSettings();
      } finally {
        setButtonLoading(whatsappRefreshButton, false);
      }
    });
  }

  const alertTypeButtons = document.querySelectorAll("#alert-type-grid .alert-type-btn");
  const ruleTypeHidden = byId("alert-rule-type-hidden");
  alertTypeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      alertTypeButtons.forEach((candidate) => candidate.classList.remove("is-active"));
      button.classList.add("is-active");
      if (ruleTypeHidden) {
        ruleTypeHidden.value = String(button.dataset.value || "signal_confidence");
      }
    });
  });

  const thresholdSlider = byId("threshold-slider");
  const thresholdDisplay = byId("threshold-display");
  if (thresholdSlider && thresholdDisplay) {
    const updateThreshold = () => {
      thresholdDisplay.textContent = Number(thresholdSlider.value).toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    };
    thresholdSlider.addEventListener("input", updateThreshold);
    updateThreshold();
  }

  const alertForm = byId("alert-rule-form");
  if (alertForm) {
    alertForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]');
      setButtonLoading(button, true, "Criando...");
      try {
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const form = Object.fromEntries(new FormData(event.currentTarget).entries());
        const payload = {
          user_id: userId,
          rule_type: form.rule_type,
          instrument: form.instrument ? String(form.instrument).toUpperCase() : null,
          threshold_value: form.threshold_value ? Number(form.threshold_value) : null,
        };
        const rule = await apiRequest("POST", "/api/alerts/rules", payload);
        const events = await apiRequest("GET", `/api/alerts/events/${userId}`);
        renderActiveAlerts(events);
        setOutput("alerts-output", rule);
        showToast("success", "Regra de alerta criada.");
        await loadDashboard();
      } catch (error) {
        setOutput("alerts-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha ao criar regra de alerta: ${error.message}`);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const reportButton = byId("load-report");
  if (reportButton) {
    reportButton.addEventListener("click", async () => {
      setButtonLoading(reportButton, true, "Carregando...");
      try {
        const userId = getAuthUserId();
        if (!userId) {
          throw new Error("Sessão inválida. Faça login novamente.");
        }
        const report = await apiRequest("GET", `/api/reports/summary/${userId}`);
        setOutput("alerts-output", report);
        showToast("success", "Relatório consolidado carregado.");
      } catch (error) {
        setOutput("alerts-output", { erro: error.message, detalhe: error.data || null });
        showToast("error", `Falha ao carregar relatório: ${error.message}`);
      } finally {
        setButtonLoading(reportButton, false);
      }
    });
  }
}

function gameSnapshot() {
  if (!state.game) {
    return null;
  }
  const finalCapital = Number(state.game.currentCapital || 0);
  const initialCapital = Number(state.game.initialCapital || 0);
  const pnl = finalCapital - initialCapital;
  const returnPct = initialCapital > 0 ? (pnl / initialCapital) * 100 : 0;
  return {
    player_name: state.game.playerName,
    initial_capital: initialCapital,
    final_capital: finalCapital,
    total_pnl: pnl,
    total_return_pct: returnPct,
    steps: state.game.steps,
  };
}

function renderGameKpis() {
  const node = byId("game-kpi-cards");
  if (!node) {
    return;
  }
  if (!state.game) {
    node.innerHTML = "";
    return;
  }
  const executed = state.game.steps.length;
  const total = state.game.theses.length;
  const remaining = Math.max(0, total - executed);
  const capital = Number(state.game.currentCapital || 0);
  const pnl = capital - Number(state.game.initialCapital || 0);
  const cards = [
    { label: "Jogador", value: state.game.playerName, tone: "tone-accent", mono: false },
    { label: "Rodada", value: `${Math.min(executed + 1, total)}/${total}`, tone: "tone-warning", mono: true },
    { label: "Capital Atual", value: formatMoney(capital), tone: pnl >= 0 ? "tone-success" : "tone-danger", mono: true },
    { label: "Teses Restantes", value: formatNumber(remaining), tone: "tone-accent", mono: true },
  ];
  node.innerHTML = cards
    .map(
      (card) => `
      <article class="kpi-card">
        <p class="kpi-label">${escapeHtml(card.label)}</p>
        <p class="kpi-value ${card.tone} ${card.mono ? "mono" : ""}">${escapeHtml(card.value)}</p>
      </article>
    `,
    )
    .join("");
}

function renderGameResult() {
  const summaryNode = byId("game-result-summary");
  const stepsNode = byId("game-result-steps");
  if (!summaryNode || !stepsNode) {
    return;
  }
  if (!state.game || state.game.steps.length === 0) {
    summaryNode.innerHTML = "<div class='list-row'><p class='list-meta'>Resultado final será exibido após a tese 5.</p></div>";
    stepsNode.innerHTML = "";
    return;
  }

  const snapshot = gameSnapshot();
  if (!snapshot) {
    return;
  }
  summaryNode.innerHTML = `
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Carteira inicial</p>
        <p class="list-meta mono">${escapeHtml(formatMoney(snapshot.initial_capital))}</p>
      </div>
      <p class="list-meta">Jogador: ${escapeHtml(snapshot.player_name)}</p>
    </div>
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">Carteira final</p>
        <p class="list-meta mono">${escapeHtml(formatMoney(snapshot.final_capital))}</p>
      </div>
      <p class="list-meta ${snapshot.total_pnl >= 0 ? "tone-success" : "tone-danger"} mono">
        PnL ${escapeHtml(formatMoney(snapshot.total_pnl))} · ${escapeHtml(formatPercent(snapshot.total_return_pct))}
      </p>
    </div>
  `;

  stepsNode.innerHTML = snapshot.steps
    .map(
      (step) => `
      <tr>
        <td>${escapeHtml(step.thesis_id)}</td>
        <td>${step.follow ? "Sim" : "Não"}</td>
        <td>${escapeHtml(step.option_id)}</td>
        <td class="mono">${escapeHtml(formatPercent(step.allocation_pct))}</td>
        <td class="mono">${escapeHtml(formatPercent(step.realized_return_pct))}</td>
        <td class="mono">${escapeHtml(formatMoney(step.pnl_amount))}</td>
        <td class="mono">${escapeHtml(formatMoney(step.capital_after))}</td>
      </tr>
    `,
    )
    .join("");
}

function renderGameRound() {
  const titleNode = byId("game-progress-title");
  const thesisNode = byId("game-thesis-card");
  const imageNode = byId("game-context-images");
  const optionsNode = byId("game-options-table");
  const decisionForm = byId("game-decision-form");
  const nextButton = byId("game-next-button");
  if (!titleNode || !thesisNode || !imageNode || !optionsNode || !decisionForm || !nextButton) {
    return;
  }

  renderGameKpis();
  renderGameResult();

  const allocationSlider = byId("allocation-slider");
  const allocationDisplay = byId("allocation-display");
  if (allocationSlider && allocationDisplay) {
    allocationDisplay.textContent = `${allocationSlider.value}%`;
  }

  if (!state.game) {
    titleNode.textContent = "Aguardando início do game";
    thesisNode.innerHTML = "<div class='list-row'><p class='list-meta'>Inicie o game para carregar a tese 1 com contexto histórico e imagens do dia.</p></div>";
    imageNode.innerHTML = "";
    optionsNode.innerHTML = "";
    nextButton.disabled = true;
    nextButton.textContent = "Próxima tese";
    return;
  }

  const index = state.game.currentIndex;
  const thesis = state.game.theses[index] || null;
  if (!thesis) {
    titleNode.textContent = "Game finalizado";
    thesisNode.innerHTML = "<div class='list-row'><p class='list-meta'>Rodadas concluídas. Confira o resumo final abaixo.</p></div>";
    imageNode.innerHTML = "";
    optionsNode.innerHTML = "";
    nextButton.disabled = true;
    nextButton.textContent = "Game finalizado";
    const snapshot = gameSnapshot();
    if (snapshot) {
      setOutput("game-output", snapshot);
    }
    return;
  }

  const totalRounds = state.game.theses.length;
  titleNode.textContent = `Tese ${index + 1} de ${totalRounds}`;
  const context = thesis.context || null;
  thesisNode.innerHTML = `
    <div class="list-row">
      <div class="list-main">
        <p class="list-title">${escapeHtml(thesis.thesis_id)} · ${escapeHtml(thesis.instrument)}</p>
        <p class="list-meta">${escapeHtml(formatDate(thesis.thesis_raised_at))}</p>
      </div>
      <p class="list-meta">Direção: ${escapeHtml(thesis.direction)}</p>
    </div>
    <div class="list-row">
      <p class="list-title">Contexto do dia</p>
      <p class="list-meta">${escapeHtml(context?.event_title || "Sem contexto externo para esta data.")}</p>
      <p class="list-meta">${escapeHtml(context?.event_summary || "-")}</p>
    </div>
    <div class="list-row">
      <p class="list-title">Tese</p>
      <p class="list-meta">${escapeHtml(thesis.thesis_statement)}</p>
      <p class="list-title">Objetivo</p>
      <p class="list-meta">${escapeHtml(thesis.objective)}</p>
      <p class="list-title">Sugestão de operação</p>
      <p class="list-meta">${escapeHtml(thesis.suggested_operation.strategy_name)} (Opção ${escapeHtml(thesis.suggested_operation.option_id)})</p>
      <p class="list-meta">Entrada: ${escapeHtml(formatDate(thesis.suggested_entry_time))} | Saída: ${escapeHtml(formatDate(thesis.suggested_exit_time))}</p>
    </div>
    <div class="list-row">
      <p class="list-title">Por que esta tese foi levantada?</p>
      <p class="list-meta">${escapeHtml((thesis.why_thesis || []).join(" | "))}</p>
    </div>
  `;

  const images = Array.isArray(context?.images) ? context.images : [];
  imageNode.innerHTML = images.length
    ? images
        .map(
          (item) => `
          <figure class="game-image-card">
            <img src="${escapeHtml(item.url)}" alt="${escapeHtml(item.caption || "Imagem do contexto histórico")}" loading="lazy" />
            <figcaption class="game-image-caption">
              ${escapeHtml(item.caption || "Fonte externa")} ·
              <a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">fonte</a>
            </figcaption>
          </figure>
        `,
        )
        .join("")
    : "<div class='list-row'><p class='list-meta'>Sem imagem disponível para o evento selecionado.</p></div>";

  optionsNode.innerHTML = (thesis.options || [])
    .map(
      (option) => `
      <tr>
        <td>${escapeHtml(option.option_id)}</td>
        <td>${escapeHtml(option.strategy_name)}</td>
        <td class="mono">${escapeHtml(formatPercent(option.expected_return_pct))}</td>
        <td class="mono">${escapeHtml(formatPercent(option.realized_return_pct))}</td>
        <td>${escapeHtml(option.risk_level)}</td>
      </tr>
    `,
    )
    .join("");

  const optionField = decisionForm.querySelector('select[name="option_id"]');
  if (optionField) {
    optionField.value = "A";
  }
  nextButton.disabled = false;
  nextButton.textContent = index === totalRounds - 1 ? "Finalizar game" : "Próxima tese";
}

function applyGameDecision(formNode) {
  if (!state.game) {
    throw new Error("Inicie o game antes de registrar decisões.");
  }
  const thesis = state.game.theses[state.game.currentIndex];
  if (!thesis) {
    throw new Error("Todas as teses já foram processadas.");
  }

  const formData = new FormData(formNode);
  const follow = String(formData.get("follow") || "sim") === "sim";
  const optionId = String(formData.get("option_id") || "A").toUpperCase();
  const rawAllocation = Number(formData.get("allocation_pct") || 0);
  const allocationPct = follow ? rawAllocation : 0;
  if (follow && (!Number.isFinite(allocationPct) || allocationPct <= 0 || allocationPct > 100)) {
    throw new Error("Informe um percentual válido de 1 a 100 para seguir a tese.");
  }

  const selectedOption = (thesis.options || []).find((option) => option.option_id === optionId);
  if (!selectedOption) {
    throw new Error("Opção de operação inválida para esta tese.");
  }

  const capitalBefore = Number(state.game.currentCapital || 0);
  const allocatedAmount = follow ? capitalBefore * (allocationPct / 100) : 0;
  const expectedReturnPct = follow ? Number(selectedOption.expected_return_pct || 0) : 0;
  const realizedReturnPct = follow ? Number(selectedOption.realized_return_pct || 0) : 0;
  const expectedPnlAmount = allocatedAmount * (expectedReturnPct / 100);
  const pnlAmount = allocatedAmount * (realizedReturnPct / 100);
  const capitalAfter = capitalBefore + pnlAmount;

  const step = {
    thesis_id: thesis.thesis_id,
    follow,
    option_id: optionId,
    allocation_pct: Number(allocationPct.toFixed(4)),
    expected_return_pct: Number(expectedReturnPct.toFixed(4)),
    realized_return_pct: Number(realizedReturnPct.toFixed(4)),
    allocated_amount: Number(allocatedAmount.toFixed(4)),
    expected_pnl_amount: Number(expectedPnlAmount.toFixed(4)),
    pnl_amount: Number(pnlAmount.toFixed(4)),
    capital_before: Number(capitalBefore.toFixed(4)),
    capital_after: Number(capitalAfter.toFixed(4)),
  };
  state.game.steps.push(step);
  state.game.currentCapital = Number(capitalAfter.toFixed(4));
  state.game.currentIndex += 1;
}

function bindGameUiControls() {
  const toggle = byId("game-follow-toggle");
  const hidden = byId("game-follow-hidden");
  const setToggle = (follow) => {
    if (!toggle || !hidden) {
      return;
    }
    toggle.setAttribute("aria-checked", follow ? "true" : "false");
    toggle.classList.toggle("is-off", !follow);
    hidden.value = follow ? "sim" : "nao";
  };

  if (toggle && hidden) {
    toggle.addEventListener("click", () => {
      const follow = toggle.getAttribute("aria-checked") !== "true";
      setToggle(follow);
    });
    toggle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        const follow = toggle.getAttribute("aria-checked") !== "true";
        setToggle(follow);
      }
    });
    setToggle(true);
  }

  const slider = byId("allocation-slider");
  const display = byId("allocation-display");
  if (slider && display) {
    const syncSlider = () => {
      display.textContent = `${slider.value}%`;
    };
    slider.addEventListener("input", syncSlider);
    syncSlider();
  }
}

function bindGameHandlers() {
  bindGameUiControls();
  const setupForm = byId("game-setup-form");
  const decisionForm = byId("game-decision-form");
  if (!setupForm || !decisionForm) {
    return;
  }

  setupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('button[type="submit"]');
    setButtonLoading(button, true, "Montando teses...");
    try {
      const formData = new FormData(event.currentTarget);
      const userId = getAuthUserId();
      if (!userId) {
        throw new Error("Sessão inválida. Faça login novamente.");
      }
      const playerName = String(formData.get("player_name") || "Jogador").trim();
      const initialCapital = Number(formData.get("initial_capital") || 100000);
      if (!Number.isFinite(initialCapital) || initialCapital <= 0) {
        throw new Error("Capital inicial inválido.");
      }
      const instruments = String(formData.get("instruments") || "")
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean);
      const payload = {
        user_id: userId,
        instruments: instruments.length > 0 ? instruments : null,
        horizon_bars: 8,
        thesis_count: 5,
        player_initial_capital: initialCapital,
      };
      const result = await apiRequest("POST", "/api/theses/game-playbook", payload);
      state.game = {
        playerName,
        initialCapital: Number(result.player_initial_capital || initialCapital),
        currentCapital: Number(result.player_initial_capital || initialCapital),
        currentIndex: 0,
        theses: Array.isArray(result.theses) ? result.theses : [],
        steps: [],
      };
      renderGameRound();
      setOutput("game-output", {
        status: "game_ready",
        player_name: playerName,
        thesis_count: state.game.theses.length,
        scan_scope: result.scan_scope,
      });
      showToast("success", "Game carregado. Registre sua decisão na tese 1.");
    } catch (error) {
      state.game = null;
      renderGameRound();
      setOutput("game-output", { erro: error.message, detalhe: error.data || null });
      showToast("error", `Falha ao iniciar game: ${error.message}`);
    } finally {
      setButtonLoading(button, false);
    }
  });

  decisionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      applyGameDecision(event.currentTarget);
      renderGameRound();
      const hasNext = Boolean(state.game && state.game.theses[state.game.currentIndex]);
      showToast(
        "success",
        hasNext ? "Decisão registrada. Avance para a próxima tese." : "Game concluído com sucesso.",
      );
    } catch (error) {
      setOutput("game-output", { erro: error.message });
      showToast("error", `Falha ao registrar decisão: ${error.message}`);
    }
  });

  renderGameRound();
}

function stopRealtimeStreams() {
  if (realtime.signalsSocket) {
    realtime.signalsSocket.onclose = null;
    realtime.signalsSocket.close();
    realtime.signalsSocket = null;
  }
  if (realtime.agentSocket) {
    realtime.agentSocket.onclose = null;
    realtime.agentSocket.close();
    realtime.agentSocket = null;
  }
  if (realtime.signalsPollingId) {
    window.clearInterval(realtime.signalsPollingId);
    realtime.signalsPollingId = null;
  }
}

function renderSignalsFromPolling(signals) {
  if (!Array.isArray(signals)) {
    return;
  }
  renderListRows(
    "dashboard-signals",
    signals,
    "Nenhum sinal gerado ainda.",
    (signal) => `
      <div class="list-row">
        <div class="list-main">
          <p class="list-title">${escapeHtml(signal.instrument)} · <span class="${toSignalTone(signal.signal_type)}">${escapeHtml(signal.signal_type)}</span></p>
          <p class="list-meta mono">Conf. ${escapeHtml(formatNumber(Number(signal.confidence || 0) * 100))}%</p>
        </div>
        <p class="list-meta">${escapeHtml(signal.rationale || "Sem rationale")}</p>
      </div>
    `,
  );
}

function startSignalsFallbackPolling() {
  if (realtime.signalsPollingId) {
    window.clearInterval(realtime.signalsPollingId);
    realtime.signalsPollingId = null;
  }
  const userId = getAuthUserId();
  if (!userId) {
    return;
  }
  realtime.signalsPollingId = window.setInterval(async () => {
    try {
      const signals = await apiRequest(
        "GET",
        `/api/signals?user_id=${userId}&status=active&limit=8`,
      );
      renderSignalsFromPolling(signals);
      if (Array.isArray(signals) && signals.length > 0) {
        syncSignalId(signals[0].signal_id);
      }
    } catch {
      return;
    }
  }, 30000);
}

function handleRealtimeSignalMessage(data) {
  if (!data || typeof data !== "object") {
    return;
  }
  const eventType = String(data.type || "");
  const payload = data.payload || {};
  if (eventType === "new_signal" && payload.signal_id) {
    syncSignalId(payload.signal_id);
    showToast("info", `Novo sinal detectado em ${payload.instrument}.`);
    void loadDashboard();
    return;
  }
  if (eventType === "signal_expired") {
    const instrument = payload.instrument ? ` em ${payload.instrument}` : "";
    showToast("warning", `Sinal expirado${instrument}.`);
    void loadDashboard();
  }
}

function connectSignalsSocket() {
  const userId = getAuthUserId();
  if (!userId) {
    return;
  }
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${window.location.host}/ws/signals?user_id=${userId}`;
  const socket = new WebSocket(url);
  realtime.signalsSocket = socket;
  socket.onopen = () => {
    realtime.reconnectSignalsMs = 1000;
    if (realtime.signalsPollingId) {
      window.clearInterval(realtime.signalsPollingId);
      realtime.signalsPollingId = null;
    }
  };
  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      handleRealtimeSignalMessage(parsed);
    } catch {
      return;
    }
  };
  socket.onclose = () => {
    realtime.signalsSocket = null;
    startSignalsFallbackPolling();
    const reconnectIn = realtime.reconnectSignalsMs;
    realtime.reconnectSignalsMs = Math.min(30000, realtime.reconnectSignalsMs * 2);
    window.setTimeout(() => {
      if (getAuthUserId()) {
        connectSignalsSocket();
      }
    }, reconnectIn);
  };
}

function connectAgentSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${window.location.host}/ws/agent`;
  const socket = new WebSocket(url);
  realtime.agentSocket = socket;
  socket.onopen = () => {
    realtime.reconnectAgentMs = 1500;
  };
  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const payload = parsed.payload || {};
      if (payload.summary && Number(payload.summary.error_workers || 0) > 0) {
        setFeedPill("warning", `Workers em erro (${payload.summary.error_workers})`);
      }
    } catch {
      return;
    }
  };
  socket.onclose = () => {
    realtime.agentSocket = null;
    const reconnectIn = realtime.reconnectAgentMs;
    realtime.reconnectAgentMs = Math.min(30000, realtime.reconnectAgentMs * 2);
    window.setTimeout(() => {
      if (getAuthUserId()) {
        connectAgentSocket();
      }
    }, reconnectIn);
  };
}

function startRealtimeStreams() {
  stopRealtimeStreams();
  connectSignalsSocket();
  connectAgentSocket();
  startSignalsFallbackPolling();
}

function showAuthenticatedExperience() {
  hideAuthGate();
  updateUserChip();
  restoreSidebarState();
  switchView("finvest");
  checkAndShowOnboarding();
  startRealtimeStreams();
  void loadDashboard();
  void loadActiveAlerts();
  void loadWhatsAppSettings();
  void refreshFeedStatus();
}

function bootstrap() {
  bindNavigation();
  bindAuthHandlers();
  bindWizardHandlers();
  bindMarketHandlers();
  bindOperationsHandlers();
  bindDashboardHandlers();
  bindBacktestHandlers();
  bindRiskHandlers();
  bindGameHandlers();
  bindMicrotradesHandlers();
  bindAlertsHandlers();

  switchView("finvest");
  updateClock();
  void refreshFeedStatus();
  ensureLucideIcons();

  window.setInterval(updateClock, 1000);
  window.setInterval(refreshFeedStatus, 15000);

  if (!AUTH_REQUIRED) {
    enableAnonymousSession();
    showAuthenticatedExperience();
    return;
  }

  if (hydrateSessionFromStorage()) {
    showAuthenticatedExperience();
    return;
  }

  showAuthGate();
  showAuthPanel("login");
  showToast("warning", "Faca login para acessar a plataforma.");
}

window.addEventListener("DOMContentLoaded", bootstrap);



