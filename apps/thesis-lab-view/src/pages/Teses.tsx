import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import { FrenteBadge } from "@/components/FrenteBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { CompletionRing } from "@/components/CompletionRing";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { fmtNumber, fmtPct, fmtRelative } from "@/lib/format";
import { AlertTriangle, ChevronRight, Filter, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  apiFrenteToFrente,
  isClosedThesis,
  isOpenThesis,
  type FrenteApi,
  type StatusTese,
  type TheseEnvelope,
} from "@/types/domain";

type FiltroAbertura = "abertas" | "fechadas" | "todas";
type FiltroFrente = "todas" | FrenteApi;

const STATUS_GROUPS: { key: "todos" | "ativas" | "validadas" | "refutadas"; label: string; match: (s: StatusTese) => boolean }[] = [
  { key: "todos",     label: "Todos",     match: () => true },
  { key: "ativas",    label: "Ativas",    match: (s) => s === "preparando" || s === "confirmando" || s === "monitorando" },
  { key: "validadas", label: "Validadas", match: (s) => s === "validada" },
  { key: "refutadas", label: "Refutadas", match: (s) => s === "refutada" },
];

export default function Teses() {
  const [search, setSearch] = useSearchParams();
  const initialFrente = (search.get("frente") as FiltroFrente) || "todas";
  const [frente, setFrente] = useState<FiltroFrente>(initialFrente);
  const [abertura, setAbertura] = useState<FiltroAbertura>("abertas");
  const [grupo, setGrupo] = useState<typeof STATUS_GROUPS[number]["key"]>("todos");

  const { data = [], isLoading } = useQuery({ queryKey: ["teses"], queryFn: api.teses, refetchInterval: 20_000 });
  const { data: dataHealth } = useQuery({ queryKey: ["data-health"], queryFn: api.dataHealth, refetchInterval: 30_000 });

  const baseFiltrada = useMemo(() => {
    return data.filter(t => {
      if (frente !== "todas" && t.front !== frente) return false;
      const g = STATUS_GROUPS.find(g => g.key === grupo)!;
      if (!g.match(t.status)) return false;
      return true;
    });
  }, [data, frente, grupo]);

  const contagensAbertura = useMemo(() => ({
    abertas: baseFiltrada.filter(isOpenThesis).length,
    fechadas: baseFiltrada.filter(isClosedThesis).length,
    todas: baseFiltrada.length,
  }), [baseFiltrada]);

  const teses = useMemo(() => {
    return baseFiltrada.filter((t) => {
      if (abertura === "abertas") return isOpenThesis(t);
      if (abertura === "fechadas") return isClosedThesis(t);
      return true;
    });
  }, [abertura, baseFiltrada]);

  const setFrenteAndUrl = (f: FiltroFrente) => {
    setFrente(f);
    const next = new URLSearchParams(search);
    if (f === "todas") next.delete("frente"); else next.set("frente", f);
    setSearch(next, { replace: true });
  };

  return (
    <div className="space-y-4 animate-fade-up">
      {/* Filtro por frente */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground px-1">
          <Filter className="w-3 h-3" /> Frente
        </div>
        <div className="grid grid-cols-4 gap-2">
          {(["todas", "b3", "cripto", "imoveis"] as FiltroFrente[]).map(f => (
            <button
              key={f}
              onClick={() => setFrenteAndUrl(f)}
              className={cn(
                "py-2 rounded-lg text-xs font-medium border transition-colors",
                frente === f
                  ? "bg-primary text-primary-foreground border-primary shadow-glow"
                  : "bg-surface-1 text-muted-foreground border-border/60 hover:text-foreground"
              )}
            >
              {f === "todas" ? "Todas" : f === "b3" ? "B3" : f === "cripto" ? "Cripto" : "Imóveis"}
            </button>
          ))}
        </div>
      </div>

      {/* Filtro por status (grupo) */}
      <div className="flex gap-1.5 overflow-x-auto scrollbar-hide -mx-1 px-1">
        {STATUS_GROUPS.map(g => (
          <button
            key={g.key}
            onClick={() => setGrupo(g.key)}
            className={cn(
              "shrink-0 py-1.5 px-3 rounded-full text-xs font-medium border transition-colors",
              grupo === g.key
                ? "bg-foreground/10 text-foreground border-foreground/30"
                : "bg-surface-1 text-muted-foreground border-border/60"
            )}
          >{g.label}</button>
        ))}
      </div>

      {/* Filtro abertura */}
      <div className="flex gap-2 p-1 rounded-xl bg-surface-1 border border-border/60">
        {([
          { key: "abertas", label: "Abertas" },
          { key: "fechadas", label: "Fechadas" },
          { key: "todas", label: "Todas" },
        ] as const).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setAbertura(key)}
            className={cn(
              "flex-1 py-2 rounded-lg text-sm font-medium capitalize transition-colors",
              abertura === key ? "bg-primary text-primary-foreground shadow-glow" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span>{label}</span>
            <span className="ml-1.5 text-xs opacity-80">{contagensAbertura[key]}</span>
          </button>
        ))}
      </div>

      {dataHealth?.fallbackActive && (
        <div className="rounded-xl border border-pending/25 bg-pending/10 px-3.5 py-3 text-xs leading-relaxed text-pending">
          <div className="flex items-center gap-2 font-medium text-foreground">
            <ShieldCheck className="w-3.5 h-3.5 text-pending" />
            Monitor preservado
          </div>
          <p className="mt-1 text-pending/90">
            Sem dados frescos agora. As teses abaixo sao o ultimo retrato valido ate a proxima ingestao.
          </p>
        </div>
      )}

      {isLoading && <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-44 rounded-xl bg-surface-1 animate-pulse" />)}</div>}

      <ul className="space-y-3">
        {teses.map(t => {
          const lowCompletion = t.completion.completion_pct < 70;
          const dataAlert = t.data_quality.freshness_status === "stale" || t.data_quality.freshness_status === "missing";
          const timingLabel = describeThesisTiming(t);
          const accentBorder =
            t.status === "validada" ? "border-l-validated"
            : t.status === "refutada" ? "border-l-refuted"
            : t.status === "monitorando" ? "border-l-primary"
            : t.status === "confirmando" ? "border-l-pending"
            : "border-l-border-strong";

          return (
            <li key={t.id}>
              <Link
                to={`/teses/${t.id}`}
                className={cn(
                  "block glass-card p-4 active:scale-[0.99] transition-transform border-l-4",
                  accentBorder
                )}
              >
                <div className="flex items-start justify-between mb-2 gap-2">
                  <div className="flex flex-col min-w-0 gap-1">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-display text-base font-semibold truncate">{t.asset_label}</span>
                      <FrenteBadge frente={apiFrenteToFrente(t.front)} />
                    </div>
                    {t.title && <p className="text-xs text-muted-foreground line-clamp-1">{t.title}</p>}
                  </div>
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <StatusPill status={t.status} />
                    <CompletionRing pct={t.completion.completion_pct} />
                  </div>
                </div>

                {/* Alertas inline */}
                {(lowCompletion || dataAlert) && (
                  <div className="flex flex-wrap gap-1.5 mb-2.5">
                    {lowCompletion && (
                      <span className="pill bg-pending/10 text-pending text-[10px] border border-pending/30">
                        <AlertTriangle className="w-3 h-3" /> envelope incompleto
                      </span>
                    )}
                    {dataAlert && (
                      <span className="pill bg-refuted/10 text-refuted text-[10px] border border-refuted/30">
                        <AlertTriangle className="w-3 h-3" /> dados {t.data_quality.freshness_status === "missing" ? "indisponíveis" : "atrasados"}
                      </span>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-3 gap-3 mb-3">
                  <Field label="Entrada" value={fmtNumber(t.entry_value, 2)} />
                  <Field label="Alvo" value={fmtNumber(t.target_value, 2)} accent="validated" />
                  <Field label="Atual" value={fmtNumber(t.current_value, 2)} />
                </div>

                <div className="grid grid-cols-2 gap-3 mb-3">
                  <Field label="Esperado" value={fmtPct(t.expected_result_pct)} />
                  <Field label="Real" value={fmtPct(t.current_result_pct)} accent={t.current_result_pct >= 0 ? "validated" : "refuted"} />
                </div>

                <ConfidenceBar value={t.confidence_pct / 100} className="mb-2.5" />

                <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                  <FreshnessBadge status={t.data_quality.freshness_status} lastUpdateAt={t.data_quality.last_update_at} />
                  <span>{timingLabel}</span>
                </div>

                <div className="flex items-center justify-between pt-2.5 border-t border-border/50 text-xs">
                  <span className="text-muted-foreground truncate pr-2">{t.suggested_action}</span>
                  <span className="flex items-center gap-1 text-primary font-medium shrink-0">
                    detalhes <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>

      {!isLoading && teses.length === 0 && (
        <div className="glass-card p-8 text-center">
          <div className="text-sm font-medium text-foreground">
            {abertura === "abertas"
              ? "Nao ha teses abertas neste recorte agora."
              : "Nenhuma tese corresponde aos filtros atuais."}
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {abertura === "abertas"
              ? "Isso nao indica falha. No momento, este recorte so tem teses encerradas ou depende de outro filtro."
              : "Tente ampliar a frente, o grupo de status ou a abertura para revisar mais resultados."}
          </p>
          {abertura === "abertas" && (
            <div className="flex flex-col sm:flex-row gap-2 justify-center mt-4">
              <button
                onClick={() => setAbertura("fechadas")}
                className="px-4 py-2 rounded-lg border border-border/60 bg-surface-1 text-sm font-medium text-foreground hover:bg-surface-2 transition-colors"
              >
                Ver fechadas
              </button>
              <button
                onClick={() => setAbertura("todas")}
                className="px-4 py-2 rounded-lg border border-primary/30 bg-primary/10 text-sm font-medium text-primary hover:bg-primary/15 transition-colors"
              >
                Ver todas
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, accent = "muted" }: { label: string; value: string; accent?: "validated" | "refuted" | "muted" }) {
  const c = accent === "validated" ? "text-validated" : accent === "refuted" ? "text-refuted" : "text-foreground";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("font-mono text-sm font-semibold tabular", c)}>{value}</div>
    </div>
  );
}

function describeThesisTiming(thesis: TheseEnvelope) {
  if (isClosedThesis(thesis)) {
    return `encerrada ${fmtRelative(thesis.closed_at ?? thesis.updated_at)}`;
  }
  return `aberta ${fmtRelative(thesis.opened_at)}`;
}
