import type { Trade, TradeStatus } from "../types";

export const DASHBOARD_SUMMARY_URL = "http://127.0.0.1:8000/api/dashboard/summary/1";

export type DashboardThesisOperation = {
  thesis_id?: string;
  thesis_number?: number;
  front?: string;
  action?: string;
  status?: string;
  is_open?: boolean;
  expected_result_pct?: number | null;
  moment_result_pct?: number | null;
  entry_price_brl?: number | null;
  current_price_brl?: number | null;
  operation_plan?: string;
  structured_operation?: string;
  exit_rule?: string;
  learning_note?: string;
  source_url?: string;
};

export type DashboardSummaryResponse = {
  thesis_open_operations?: DashboardThesisOperation[];
};

export async function fetchDashboardSummary(url = DASHBOARD_SUMMARY_URL): Promise<DashboardSummaryResponse> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Dashboard summary falhou: HTTP ${response.status}`);
  }
  return response.json() as Promise<DashboardSummaryResponse>;
}

export function mapDashboardSummaryToRealEstateTrades(
  summary: DashboardSummaryResponse,
  isOpen: boolean,
): Trade[] {
  return (summary.thesis_open_operations ?? [])
    .filter((thesis) => thesis.front === "imoveis")
    .filter((thesis) => thesis.is_open === isOpen)
    .map(mapThesisToTrade);
}

function mapThesisToTrade(thesis: DashboardThesisOperation): Trade {
  const expectedPct = numberOrZero(thesis.expected_result_pct);
  const hasMoment = typeof thesis.moment_result_pct === "number";
  const resultPct = hasMoment ? numberOrZero(thesis.moment_result_pct) : expectedPct;
  const progressPct = expectedPct === 0 ? 0 : clamp(Math.round((Math.abs(resultPct) / Math.abs(expectedPct)) * 100), 0, 100);

  return {
    id: thesis.thesis_number ?? thesis.thesis_id ?? "sem-id",
    ticker: thesis.action || "Tese imobiliária",
    direction: resultPct >= 0 ? "up" : "down",
    status: toTradeStatus(thesis, resultPct),
    statusLabel: thesis.status || (thesis.is_open ? "Aberta" : "Encerrada"),
    resultPct,
    resultLabel: hasMoment ? "momento atual" : "esperado",
    pills: [
      { label: "Entrada", value: formatCurrency(thesis.entry_price_brl) },
      { label: "Atual", value: formatCurrency(thesis.current_price_brl) },
      { label: "Esperado", value: formatPercent(expectedPct), tone: expectedPct >= 0 ? "green" : "red" },
    ],
    description: thesis.operation_plan || "Plano operacional registrado pelo Halley.",
    progressPct,
    progressLabel: `${progressPct}% da tese`,
    strategy: thesis.structured_operation || "Operação estruturada",
    strategyTone: toStrategyTone(thesis.structured_operation),
    maxGain: formatPercent(expectedPct),
    riskLabel: thesis.exit_rule || "Regra de saída pendente",
    link: thesis.source_url || undefined,
  };
}

function toTradeStatus(thesis: DashboardThesisOperation, resultPct: number): TradeStatus {
  if (!thesis.is_open) return "invalid";
  if (resultPct < 0) return "warn";
  return "open";
}

function toStrategyTone(strategy = ""): Trade["strategyTone"] {
  const normalized = strategy.toLowerCase();
  if (normalized.includes("renda")) return "green";
  if (normalized.includes("capital") || normalized.includes("valoriza")) return "purple";
  return "blue";
}

function numberOrZero(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatCurrency(value: number | null | undefined) {
  return numberOrZero(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  });
}

function formatPercent(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2).replace(".", ",")}%`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
