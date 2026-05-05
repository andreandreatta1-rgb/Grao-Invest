import { useEffect, useMemo, useState } from "react";
import { TradeCard } from "../components/TradeCard";
import { trades as fallbackTrades } from "../data/mockData";
import { fetchDashboardSummary, mapDashboardSummaryToRealEstateTrades } from "../data/realEstateTheses";
import type { Trade } from "../types";

type ThesisTab = "open" | "closed";
type DataSource = "api" | "fallback";

export function TesesScreen() {
  const [activeTab, setActiveTab] = useState<ThesisTab>("open");
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [dataSource, setDataSource] = useState<DataSource>("api");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRealEstateTheses() {
      setIsLoading(true);
      setLoadError(null);

      try {
        const summary = await fetchDashboardSummary();
        if (cancelled) return;

        setOpenTrades(mapDashboardSummaryToRealEstateTrades(summary, true));
        setClosedTrades(mapDashboardSummaryToRealEstateTrades(summary, false));
        setDataSource("api");
      } catch (error) {
        if (cancelled) return;

        setOpenTrades(fallbackTrades);
        setClosedTrades([]);
        setDataSource("fallback");
        setLoadError(error instanceof Error ? error.message : "Falha ao carregar teses de imóveis");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadRealEstateTheses();

    return () => {
      cancelled = true;
    };
  }, []);

  const visibleTrades = activeTab === "open" ? openTrades : closedTrades;
  const summaryStats = useMemo(() => buildSummaryStats(visibleTrades, dataSource), [visibleTrades, dataSource]);

  return (
    <section className="content-screen">
      <div className="relative mb-5 overflow-hidden rounded-[20px] border border-grao-blue/15 bg-[linear-gradient(135deg,#0f2a4a_0%,#0d1f3a_50%,#0a1a30_100%)] p-5 before:absolute before:-right-10 before:-top-10 before:h-[140px] before:w-[140px] before:rounded-full before:bg-[radial-gradient(circle,rgba(0,212,170,0.12)_0%,transparent_70%)]">
        <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.08em] text-grao-text2">
          Teses de Imóveis · thesis_open_operations
        </div>
        <div className="mb-4 text-[28px] font-extrabold">
          {visibleTrades.length} <span className="text-sm font-medium text-grao-text2">{activeTab === "open" ? "abertas" : "encerradas"}</span>
        </div>
        <div className="flex gap-4">
          {summaryStats.map((stat) => (
            <SummaryStat key={stat.label} label={stat.label} value={stat.value} tone={stat.tone} />
          ))}
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2 rounded-2xl bg-grao-card p-1">
        <TabButton active={activeTab === "open"} label={`Abertas · ${openTrades.length}`} onClick={() => setActiveTab("open")} />
        <TabButton active={activeTab === "closed"} label={`Encerradas · ${closedTrades.length}`} onClick={() => setActiveTab("closed")} />
      </div>

      {loadError ? (
        <div className="mb-3 rounded-2xl border border-grao-gold/20 bg-grao-gold/10 px-4 py-3 text-xs leading-relaxed text-grao-gold">
          API indisponível. Usando mockData.ts temporariamente até o endpoint voltar.
        </div>
      ) : null}

      {isLoading ? (
        <div className="rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-5 text-sm text-grao-text2">
          Buscando teses reais de imóveis no motor Halley...
        </div>
      ) : visibleTrades.length > 0 ? (
        visibleTrades.map((trade) => <TradeCard key={trade.id} trade={trade} />)
      ) : (
        <div className="rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-5 text-sm leading-relaxed text-grao-text2">
          Nenhuma tese de imóveis {activeTab === "open" ? "aberta" : "encerrada"} encontrada em thesis_open_operations.
        </div>
      )}
      <div className="h-5" />
    </section>
  );
}

type SummaryStatProps = {
  label: string;
  value: string;
  tone: "neutral" | "up" | "down" | "gold";
};

function SummaryStat({ label, value, tone }: SummaryStatProps) {
  const toneClass = {
    neutral: "text-grao-text2",
    up: "text-grao-green2",
    down: "text-grao-red",
    gold: "text-grao-gold",
  }[tone];

  return (
    <div className="min-w-0 flex-1">
      <div className="mb-1 text-[11px] text-grao-text3">{label}</div>
      <div className={`truncate text-[15px] font-bold ${toneClass}`}>{value}</div>
    </div>
  );
}

function TabButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl px-2.5 py-2.5 text-center text-[12px] font-semibold transition-all duration-200 ${
        active
          ? "bg-gradient-to-br from-[#1a3a6a] to-[#1f4580] text-white shadow-[0_4px_12px_rgba(79,142,247,0.25)]"
          : "text-grao-text2 hover:bg-white/[0.05] hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}

function buildSummaryStats(trades: Trade[], source: DataSource): SummaryStatProps[] {
  const resultPcts = trades.map((trade) => trade.resultPct);
  const avg = resultPcts.length ? resultPcts.reduce((sum, value) => sum + value, 0) / resultPcts.length : 0;
  const best = resultPcts.length ? Math.max(...resultPcts) : 0;
  const worst = resultPcts.length ? Math.min(...resultPcts) : 0;

  return [
    { label: "Média", value: formatPct(avg), tone: avg >= 0 ? "up" : "down" },
    { label: "Melhor", value: formatPct(best), tone: best >= 0 ? "up" : "down" },
    { label: "Pior", value: formatPct(worst), tone: worst >= 0 ? "up" : "down" },
    { label: "Fonte", value: source === "api" ? "API" : "Mock", tone: source === "api" ? "gold" : "neutral" },
  ];
}

function formatPct(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2).replace(".", ",")}%`;
}
