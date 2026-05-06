import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";
import { HealthBadge } from "@/components/HealthBadge";
import { FrenteBadge } from "@/components/FrenteBadge";
import { fmtNumber, fmtPctRatio, fmtRelative } from "@/lib/format";
import { CheckCircle2, Brain, Sparkles, Activity, AlertTriangle, ChevronRight, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import type { Frente, FreshnessStatus, SaudeDado, TheseEnvelope } from "@/types/domain";
import { isOpenThesis } from "@/types/domain";
import { cn } from "@/lib/utils";

export default function Cockpit() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["cockpit-resumo"], queryFn: api.cockpit, refetchInterval: 30_000,
  });
  const { data: teses = [] } = useQuery({
    queryKey: ["teses"],
    queryFn: api.teses,
    refetchInterval: 30_000,
    enabled: Boolean(data),
  });

  if (isLoading) return <SkeletonCockpit />;
  if (isError || !data) return <ErrorState />;

  // agregados de qualidade calculados a partir do envelope canônico
  const fresh   = teses.filter(t => t.data_quality.freshness_status === "fresh").length;
  const partial = teses.filter(t => t.data_quality.freshness_status === "partial" || t.data_quality.freshness_status === "stale").length;
  const missing = teses.filter(t => t.data_quality.freshness_status === "missing").length;
  const lowCompletion = teses.filter(t => t.completion.completion_pct < 70).length;

  const byFrente = (front: "b3" | "cripto" | "imoveis") => teses.filter(t => t.front === front);
  const hasDetailedTeses = teses.length > 0;
  const frontDetails = (Object.keys(data.frentes) as Frente[]).reduce((acc, f) => {
    const info = data.frentes[f];
    const apiFront = f === "B3" ? "b3" : f === "Cripto" ? "cripto" : "imoveis";
    const list = byFrente(apiFront);
    const dist = countFreshness(list);
    acc[f] = {
      apiFront,
      dist,
      total: list.length || 1,
      ativas: hasDetailedTeses ? list.filter(isOpenThesis).length : info.ativas,
      saude: hasDetailedTeses ? saudeFromFreshnessDist(dist, list.length) : info.saude,
      ultimaIngestaoEm: info.ultimaIngestaoEm,
    };
    return acc;
  }, {} as Record<Frente, {
    apiFront: "b3" | "cripto" | "imoveis";
    dist: { fresh: number; partial: number; missing: number };
    total: number;
    ativas: number;
    saude: SaudeDado;
    ultimaIngestaoEm: string;
  }>);
  const effectiveTesesAtivas = hasDetailedTeses ? teses.filter(isOpenThesis).length : data.tesesAtivas;
  const sistemaOk = Object.values(frontDetails).every(f => f.saude !== "indisponivel");

  return (
    <div className="space-y-5 animate-fade-up">
      {/* Resumo executivo */}
      <section className="rounded-xl bg-gradient-cockpit border border-border/70 p-5 shadow-elevated">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-1">Sistema</p>
            <h2 className="font-display text-xl font-semibold">
              {sistemaOk ? "Operando com método" : "Atenção em fontes de dados"}
            </h2>
          </div>
          <span className="pill bg-primary/10 text-primary border border-primary/30">
            <span className={`w-1.5 h-1.5 rounded-full bg-primary ${sistemaOk ? "animate-pulse-slow" : ""}`} />
            {effectiveTesesAtivas} ativas
          </span>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          O motor está monitorando hipóteses ativas, validando evidências e incorporando aprendizados continuamente.
        </p>

        {/* Mini-painel de saúde de dados */}
        <div className="grid grid-cols-3 gap-2">
          <HealthMini label="Saudáveis" value={fresh} tone="validated" />
          <HealthMini label="Parciais" value={partial} tone="pending" />
          <HealthMini label="Indisponíveis" value={missing} tone="refuted" />
        </div>
        {lowCompletion > 0 && (
          <div className="mt-3 flex items-center gap-2 text-[11px] text-pending">
            <AlertTriangle className="w-3.5 h-3.5" />
            {lowCompletion} {lowCompletion === 1 ? "tese com baixa completude" : "teses com baixa completude"}
          </div>
        )}
      </section>

      {/* Métricas principais */}
      <section className="grid grid-cols-2 gap-3">
        <MetricCard label="Teses testadas" value={fmtNumber(data.tesesTestadas, 0)} hint="histórico acumulado" />
        <MetricCard label="Validação histórica" value={fmtPctRatio(data.validacaoHistoricaPct, 1)} accent="validated" hint="taxa de teses validadas" />
        <MetricCard label="Expectativa líquida" value={fmtPctRatio(data.expectativaLiquidaMedia, 2)} accent="gold" hint="média por tese" />
        <MetricCard label="Aprendizados aplicados" value={fmtNumber(data.aprendizadosAplicados, 0)} accent="primary" hint="ajustes no motor" />
      </section>

      {/* Frentes — destaque visual e contagens reais */}
      <section className="space-y-2.5">
        <div className="flex items-center justify-between px-1">
          <h3 className="font-display text-sm font-semibold">Frentes de atuação</h3>
          <span className="text-[11px] text-muted-foreground">atualizado {fmtRelative(data.ultimaAtualizacao)}</span>
        </div>
        <div className="space-y-2">
          {(Object.keys(data.frentes) as Frente[]).map((f) => {
            const detail = frontDetails[f];
            return (
              <Link
                key={f}
                to={`/teses?frente=${detail.apiFront}`}
                className="block glass-card p-4 active:scale-[0.99] transition-transform"
              >
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-3">
                    <FrenteBadge frente={f} />
                    <div>
                      <div className="text-sm font-medium">{detail.ativas} {detail.ativas === 1 ? "tese ativa" : "teses ativas"}</div>
                      <div className="text-[11px] text-muted-foreground">ingestão {fmtRelative(detail.ultimaIngestaoEm)}</div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>
                {/* barra de qualidade */}
                <FreshnessBar dist={detail.dist} total={detail.total} />
                <div className="flex items-center justify-between mt-2 text-[11px] text-muted-foreground">
                  <HealthBadge saude={detail.saude} />
                  <span className="tabular">
                    {detail.dist.fresh} ok · {detail.dist.partial} parcial · {detail.dist.missing} ind.
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Indicadores rápidos */}
      <section className="grid grid-cols-2 gap-3">
        <RespostaRapida icon={Activity} label="O sistema está funcionando?" valor={sistemaOk ? "Sim" : "Parcial"} ok={sistemaOk} />
        <RespostaRapida icon={Sparkles} label="Há teses ativas agora?" valor={`${effectiveTesesAtivas}`} ok={effectiveTesesAtivas > 0} />
        <RespostaRapida icon={Brain} label="O método está aprendendo?" valor={`+${data.aprendizadosAplicados}`} ok />
        <RespostaRapida icon={CheckCircle2} label="Validação histórica" valor={fmtPctRatio(data.validacaoHistoricaPct, 0)} ok={data.validacaoHistoricaPct >= 0.5} />
      </section>
    </div>
  );
}

function countFreshness(list: TheseEnvelope[]) {
  const acc = { fresh: 0, partial: 0, missing: 0 };
  for (const t of list) {
    const f: FreshnessStatus = t.data_quality.freshness_status;
    if (f === "fresh") acc.fresh++;
    else if (f === "missing") acc.missing++;
    else acc.partial++;
  }
  return acc;
}

function saudeFromFreshnessDist(
  dist: { fresh: number; partial: number; missing: number },
  total: number,
): SaudeDado {
  if (total <= 0) return "indisponivel";
  if (dist.missing >= total) return "indisponivel";
  if (dist.partial > 0 || dist.missing > 0) return "parcial";
  return "atualizado";
}

function FreshnessBar({ dist, total }: { dist: { fresh: number; partial: number; missing: number }; total: number }) {
  const p = (n: number) => (n / total) * 100;
  return (
    <div className="flex h-1.5 w-full rounded-full overflow-hidden bg-surface-2">
      <div className="bg-validated transition-all" style={{ width: `${p(dist.fresh)}%` }} />
      <div className="bg-pending transition-all" style={{ width: `${p(dist.partial)}%` }} />
      <div className="bg-refuted transition-all" style={{ width: `${p(dist.missing)}%` }} />
    </div>
  );
}

function HealthMini({ label, value, tone }: { label: string; value: number; tone: "validated" | "pending" | "refuted" }) {
  const cls =
    tone === "validated" ? "bg-validated/10 text-validated border-validated/30"
    : tone === "pending" ? "bg-pending/10 text-pending border-pending/30"
    : "bg-refuted/10 text-refuted border-refuted/30";
  return (
    <div className={cn("rounded-lg border px-2.5 py-2", cls)}>
      <div className="text-[10px] uppercase tracking-wider opacity-80">{label}</div>
      <div className="font-mono text-base font-semibold tabular">{value}</div>
    </div>
  );
}

function RespostaRapida({
  icon: Icon,
  label,
  valor,
  ok,
}: {
  icon: LucideIcon;
  label: string;
  valor: string;
  ok: boolean;
}) {
  return (
    <div className="glass-card p-3.5">
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className={`w-4 h-4 ${ok ? "text-primary" : "text-pending"}`} />
        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</span>
      </div>
      <div className={`font-display text-lg font-semibold ${ok ? "text-foreground" : "text-pending"}`}>{valor}</div>
    </div>
  );
}

function SkeletonCockpit() {
  return (
    <div className="space-y-4">
      <div className="h-32 rounded-xl bg-surface-1 animate-pulse" />
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 rounded-xl bg-surface-1 animate-pulse" />)}
      </div>
    </div>
  );
}
function ErrorState() {
  return (
    <div className="glass-card p-6 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-pending mt-0.5" />
      <div>
        <h3 className="font-display font-semibold mb-1">Não foi possível carregar o cockpit</h3>
        <p className="text-sm text-muted-foreground">Verifique a conexão com o backend e tente novamente em instantes.</p>
      </div>
    </div>
  );
}
