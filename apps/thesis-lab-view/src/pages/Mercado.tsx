import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { FrenteBadge } from "@/components/FrenteBadge";
import { HealthBadge } from "@/components/HealthBadge";
import { fmtNumber, fmtPct, fmtRelative } from "@/lib/format";
import { ArrowDownRight, ArrowUpRight, Database, ShieldCheck, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DataHealthSnapshot, Frente } from "@/types/domain";

const filtros: ("Todas" | Frente)[] = ["Todas", "B3", "Cripto", "Imoveis"];

export default function Mercado() {
  const [filtro, setFiltro] = useState<typeof filtros[number]>("Todas");
  const { data: ativos = [] } = useQuery({ queryKey: ["mercado"], queryFn: api.mercado, refetchInterval: 15_000 });
  const { data: fontes = [] } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes, refetchInterval: 30_000 });
  const { data: dataHealth } = useQuery({ queryKey: ["data-health"], queryFn: api.dataHealth, refetchInterval: 30_000 });

  const lista = filtro === "Todas" ? ativos : ativos.filter(a => a.frente === filtro);
  const destaques = lista.filter(a => a.destaque);
  const restantes = lista.filter(a => !a.destaque);

  return (
    <div className="space-y-5 animate-fade-up">
      {dataHealth && <DataHealthPanel health={dataHealth} />}

      {/* Filtros horizontais */}
      <div className="flex gap-2 overflow-x-auto scrollbar-hide -mx-1 px-1">
        {filtros.map(f => (
          <button key={f} onClick={() => setFiltro(f)}
            className={cn(
              "shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium border transition-colors",
              filtro === f ? "bg-primary text-primary-foreground border-primary shadow-glow" :
                             "bg-surface-1 text-muted-foreground border-border/60 hover:text-foreground"
            )}
          >{f === "Imoveis" ? "Imóveis" : f}</button>
        ))}
      </div>

      {/* Destaques */}
      {destaques.length > 0 && (
        <section className="space-y-2">
          <h3 className="px-1 font-display text-sm font-semibold flex items-center gap-1.5"><Star className="w-3.5 h-3.5 text-accent" /> Em destaque</h3>
          <div className="grid grid-cols-2 gap-3">
            {destaques.map(a => (
              <div key={a.ticker} className="glass-card p-3.5">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-display text-sm font-semibold">{a.ticker}</span>
                  <FrenteBadge frente={a.frente} className="text-[10px] py-0.5" />
                </div>
                <div className="font-mono tabular text-lg">{fmtNumber(a.preco, 2)}</div>
                <div className={cn("flex items-center gap-1 text-xs font-mono tabular mt-0.5", a.variacao >= 0 ? "text-validated" : "text-refuted")}>
                  {a.variacao >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {fmtPct(a.variacao)}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Lista */}
      <section className="space-y-2">
        <h3 className="px-1 font-display text-sm font-semibold">Acompanhamento</h3>
        <ul className="glass-card divide-y divide-border/50">
          {restantes.map(a => (
            <li key={a.ticker} className="flex items-center justify-between p-3.5">
              <div className="flex items-center gap-3 min-w-0">
                <FrenteBadge frente={a.frente} className="text-[10px] py-0.5" />
                <div className="min-w-0">
                  <div className="text-sm font-semibold truncate">{a.ticker}</div>
                  <div className="text-[11px] text-muted-foreground truncate">{a.nome}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono tabular text-sm">{fmtNumber(a.preco, 2)}</div>
                <div className={cn("text-xs font-mono tabular", a.variacao >= 0 ? "text-validated" : "text-refuted")}>{fmtPct(a.variacao)}</div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Saúde da ingestão */}
      <section className="space-y-2">
        <h3 className="px-1 font-display text-sm font-semibold">Saúde das fontes</h3>
        <ul className="space-y-2">
          {fontes.map(f => (
            <li key={f.nome} className="glass-card p-3.5 flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{f.nome}</div>
                <div className="text-[11px] text-muted-foreground">última atualização {fmtRelative(f.ultimaAtualizacao)}</div>
              </div>
              <HealthBadge saude={f.saude} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function DataHealthPanel({ health }: { health: DataHealthSnapshot }) {
  const modeLabel = health.fallbackActive ? "Fallback ativo" : health.status === "fresh" ? "Fluxo normal" : "Cobertura parcial";

  return (
    <section className="glass-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-muted-foreground">
            <ShieldCheck className="w-3 h-3" /> Confianca operacional
          </div>
          <h3 className="mt-1 font-display text-base font-semibold">{health.headline}</h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{health.detail}</p>
        </div>
        <HealthBadge saude={health.saude} showLabel={false} className="mt-1 shrink-0" />
      </div>

      <div className="grid grid-cols-3 gap-2 border-y border-border/50 py-3">
        <HealthMetric label="Teses" value={`${health.thesisCount}`} />
        <HealthMetric label="Atencao" value={`${health.needsAttentionCount}`} />
        <HealthMetric label="Modo" value={modeLabel} />
      </div>

      <div className="flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <Database className="w-3 h-3" /> ultimo monitor {fmtRelative(health.lastUpdateAt)}
        </span>
        <span className="font-mono tabular">
          B3 {health.frontCounts.B3} | Cripto {health.frontCounts.Cripto} | Imoveis {health.frontCounts.Imoveis}
        </span>
      </div>

      {health.notes.length > 0 && (
        <div className="rounded-lg border border-pending/20 bg-pending/10 px-3 py-2 text-[11px] leading-relaxed text-pending">
          {health.notes[0]}
        </div>
      )}
    </section>
  );
}

function HealthMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 truncate font-mono text-xs font-semibold tabular text-foreground">{value}</div>
    </div>
  );
}
