import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { FrenteBadge } from "@/components/FrenteBadge";
import { fmtRelative } from "@/lib/format";
import { Bell, CheckCircle2, Clock, FlaskConical, Lightbulb, MessageSquare, ShieldAlert, X, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Decisao, DecisaoStatus, DecisaoTipo } from "@/types/domain";

const tipoMeta: Record<DecisaoTipo, { icon: LucideIcon; label: string; color: string; ring: string; priority: number }> = {
  alerta_revisao: { icon: ShieldAlert, label: "Alerta de revisao", color: "text-pending", ring: "border-l-pending", priority: 0 },
  confirmacao_hipotese: { icon: FlaskConical, label: "Confirmar hipotese", color: "text-accent", ring: "border-l-accent", priority: 1 },
  sugestao_tese: { icon: Lightbulb, label: "Sugestao de tese", color: "text-primary", ring: "border-l-primary", priority: 2 },
  mensagem: { icon: MessageSquare, label: "Mensagem do sistema", color: "text-info", ring: "border-l-info", priority: 3 },
};

const statusMeta: Record<DecisaoStatus, string> = {
  pendente: "bg-pending/15 text-pending",
  aceita: "bg-validated/15 text-validated",
  rejeitada: "bg-refuted/15 text-refuted",
  em_andamento: "bg-primary/15 text-primary",
  concluida: "bg-muted text-muted-foreground",
};

type Filtro = "pendentes" | "todas" | "alertas";
type DecisionRowItem = { primary: Decisao; similarCount: number };

export default function Decisoes() {
  const [filtro, setFiltro] = useState<Filtro>("pendentes");
  const [acoes, setAcoes] = useState<Record<string, "aceita" | "rejeitada" | "adiada">>({});
  const { data = [], isLoading } = useQuery({ queryKey: ["decisoes"], queryFn: api.decisoes, refetchInterval: 15_000 });

  const agrupadas = useMemo(() => groupDecisionRows(data), [data]);

  const lista = agrupadas.filter(({ primary }) => {
    if (filtro === "pendentes") return isActionableDecision(primary);
    if (filtro === "alertas") return primary.tipo === "alerta_revisao" && isActionableDecision(primary);
    return true;
  });

  const pendentes = agrupadas.filter(({ primary }) => isActionableDecision(primary)).length;
  const alertas = agrupadas.filter(({ primary }) => primary.tipo === "alerta_revisao" && isActionableDecision(primary)).length;

  return (
    <div className="space-y-4 animate-fade-up">
      <section className="glass-card p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-pending/15 grid place-items-center">
            <Bell className="w-5 h-5 text-pending" />
          </div>
          <div className="flex-1">
            <div className="font-display text-base font-semibold">Centro de Decisoes</div>
            <p className="text-xs text-muted-foreground">Inbox executivo. Decida o que entra no metodo.</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Counter label="Pendentes" n={pendentes} tone={pendentes > 0 ? "pending" : "muted"} />
          <Counter label="Alertas" n={alertas} tone={alertas > 0 ? "refuted" : "muted"} />
        </div>
      </section>

      <div className="flex gap-2 p-1 rounded-xl bg-surface-1 border border-border/60">
        {(["pendentes", "alertas", "todas"] as Filtro[]).map((f) => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={cn(
              "flex-1 py-2 rounded-lg text-sm font-medium capitalize transition-colors",
              filtro === f ? "bg-primary text-primary-foreground shadow-glow" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading && <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-28 rounded-xl bg-surface-1 animate-pulse" />)}</div>}

      <ul className="space-y-3">
        {lista.map(({ primary, similarCount }) => (
          <DecisaoRow
            key={primary.id}
            d={primary}
            similarCount={similarCount}
            acao={acoes[primary.id]}
            onAct={(a) => setAcoes((prev) => ({ ...prev, [primary.id]: a }))}
          />
        ))}
      </ul>

      {!isLoading && lista.length === 0 && (
        <div className="glass-card p-8 text-center text-sm text-muted-foreground">
          Nenhuma decisao {filtro === "pendentes" ? "pendente" : filtro === "alertas" ? "de alerta" : ""} no momento.
        </div>
      )}
    </div>
  );
}

function Counter({ label, n, tone }: { label: string; n: number; tone: "pending" | "refuted" | "muted" }) {
  const cls =
    tone === "pending"
      ? "bg-pending/10 text-pending border-pending/30"
      : tone === "refuted"
        ? "bg-refuted/10 text-refuted border-refuted/30"
        : "bg-surface-1 text-muted-foreground border-border/60";
  return (
    <div className={cn("rounded-lg border px-3 py-2 flex items-center justify-between", cls)}>
      <span className="text-[11px] uppercase tracking-wider opacity-90">{label}</span>
      <span className="font-mono text-lg font-semibold tabular">{n}</span>
    </div>
  );
}

function DecisaoRow({
  d,
  similarCount,
  acao,
  onAct,
}: {
  d: Decisao;
  similarCount: number;
  acao?: "aceita" | "rejeitada" | "adiada";
  onAct: (a: "aceita" | "rejeitada" | "adiada") => void;
}) {
  const meta = tipoMeta[d.tipo];
  const Icon = meta.icon;
  const isAlert = d.tipo === "alerta_revisao";
  const taken = Boolean(acao) || !isActionableDecision(d);

  return (
    <li className={cn("glass-card p-4 border-l-4", meta.ring, isAlert && d.status === "pendente" && "shadow-[0_0_24px_-12px_hsl(var(--pending)/0.6)]")}>
      <div className="flex items-start gap-3">
        <div className={cn("w-9 h-9 rounded-lg bg-surface-2 grid place-items-center shrink-0", meta.color)}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className={cn("text-[10px] uppercase tracking-widest font-medium", meta.color)}>{meta.label}</span>
            <span className={cn("pill text-[10px]", statusMeta[acao ? (acao === "adiada" ? "em_andamento" : acao) : d.status])}>
              {(acao ?? d.status).replace("_", " ")}
            </span>
          </div>
          <h4 className="font-display text-sm font-semibold leading-tight mb-1">{d.titulo}</h4>
          <p className="text-xs text-muted-foreground leading-relaxed mb-2">{d.resumo}</p>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              {d.frente && <FrenteBadge frente={d.frente} className="text-[10px] py-0.5" />}
              {d.ativoRelacionado && <span className="text-[11px] font-mono tabular text-muted-foreground">{d.ativoRelacionado}</span>}
              {similarCount > 0 && (
                <span className="pill bg-surface-2 text-foreground/80 text-[10px]">
                  +{similarCount} similares
                </span>
              )}
            </div>
            <span className="text-[11px] text-muted-foreground">{fmtRelative(d.criadaEm)}</span>
          </div>

          {!taken && (
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border/50">
              <button
                onClick={() => onAct("aceita")}
                className="py-2 rounded-lg bg-validated text-validated-foreground text-xs font-semibold flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Aceitar
              </button>
              <button
                onClick={() => onAct("adiada")}
                className="py-2 rounded-lg bg-surface-2 text-foreground text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-surface-3 transition-colors"
              >
                <Clock className="w-3.5 h-3.5" /> Adiar
              </button>
              <button
                onClick={() => onAct("rejeitada")}
                className="py-2 rounded-lg bg-refuted/10 border border-refuted/30 text-refuted text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-refuted/15 transition-colors"
              >
                <X className="w-3.5 h-3.5" /> Rejeitar
              </button>
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

function groupDecisionRows(data: Decisao[]): DecisionRowItem[] {
  const actionableGroups = new Map<string, Decisao[]>();
  const passthrough: DecisionRowItem[] = [];

  for (const decision of data) {
    if (!isActionableDecision(decision)) {
      passthrough.push({ primary: decision, similarCount: 0 });
      continue;
    }

    const key = decisionGroupKey(decision);
    const group = actionableGroups.get(key) ?? [];
    group.push(decision);
    actionableGroups.set(key, group);
  }

  const grouped = Array.from(actionableGroups.values()).map((group) => {
    const ordered = [...group].sort(compareDecisionPriority);
    return {
      primary: ordered[0],
      similarCount: ordered.length - 1,
    };
  });

  return [...grouped, ...passthrough].sort((a, b) => compareDecisionPriority(a.primary, b.primary));
}

function isActionableDecision(decision: Decisao) {
  return decision.status === "pendente" || decision.status === "em_andamento";
}

function decisionGroupKey(decision: Decisao) {
  return [
    decision.tipo,
    normalizeDecisionText(decision.titulo),
    normalizeDecisionText(decision.ativoRelacionado),
    normalizeDecisionText(decision.frente),
  ].join("::");
}

function normalizeDecisionText(value?: string) {
  return (value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function compareDecisionPriority(a: Decisao, b: Decisao) {
  const pa = tipoMeta[a.tipo].priority;
  const pb = tipoMeta[b.tipo].priority;
  if (pa !== pb) return pa - pb;
  return new Date(b.criadaEm).getTime() - new Date(a.criadaEm).getTime();
}
