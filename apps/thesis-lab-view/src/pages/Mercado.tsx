import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { FrenteBadge } from "@/components/FrenteBadge";
import { HealthBadge } from "@/components/HealthBadge";
import { fmtNumber, fmtPct, fmtRelative } from "@/lib/format";
import { ArrowDownRight, ArrowUpRight, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Frente } from "@/types/domain";

const filtros: ("Todas" | Frente)[] = ["Todas", "B3", "Cripto", "Imoveis"];

export default function Mercado() {
  const [filtro, setFiltro] = useState<typeof filtros[number]>("Todas");
  const { data: ativos = [] } = useQuery({ queryKey: ["mercado"], queryFn: api.mercado, refetchInterval: 15_000 });
  const { data: fontes = [] } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes, refetchInterval: 30_000 });

  const lista = filtro === "Todas" ? ativos : ativos.filter(a => a.frente === filtro);
  const destaques = lista.filter(a => a.destaque);
  const restantes = lista.filter(a => !a.destaque);

  return (
    <div className="space-y-5 animate-fade-up">
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
