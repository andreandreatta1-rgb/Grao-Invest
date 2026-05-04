import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import { FrenteBadge } from "@/components/FrenteBadge";
import { StatusPill } from "@/components/StatusPill";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { Countdown } from "@/components/Countdown";
import { PressureGauge } from "@/components/PressureGauge";
import { ProgressToTarget } from "@/components/ProgressToTarget";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { CompletionRing } from "@/components/CompletionRing";
import { fmtNumber, fmtPct, fmtRelative, fmtTime } from "@/lib/format";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FlaskConical,
  Radio,
  RefreshCw,
  Timer,
  XCircle,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  apiFrenteToFrente,
  isClosedThesis,
  type StatusTese,
  type TheseEnvelope,
  type SpecificMicrotrade,
} from "@/types/domain";
import type { MicrotradesAutopilotLatest } from "@/lib/backend-adapters";
import { buildLabSections, isLiveLabMicrotrade, type LabSections } from "@/lib/lab-groups";
import { buildLabCandidateSuggestions, type LabCandidateSuggestion } from "@/lib/lab-candidates";

export default function Lab() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["microtrades"],
    queryFn: api.microtrades,
    refetchInterval: 5_000,
  });
  const { data: cycle } = useQuery({
    queryKey: ["microtrades", "autopilot", "latest"],
    queryFn: api.microtradesAutopilotLatest,
    refetchInterval: 15_000,
  });

  const sections = buildLabSections(data);
  const candidateSuggestions = buildLabCandidateSuggestions(data);
  const liveCount = sections.activeNow.length;
  const queuedCount = sections.queued.length;
  const historicalCount = sections.recentClosed.length;
  const hasLiveTrades = liveCount > 0;
  const hasOpenTrades = liveCount + queuedCount > 0;
  const cycleRunning = Boolean(cycle?.isRunning);
  const agentActive = Boolean(cycle?.agentRunning);

  const liveModeLabel = cycleRunning
    ? "CICLO RODANDO"
    : hasLiveTrades
      ? "AO VIVO"
      : queuedCount > 0
        ? "EM OBSERVACAO"
        : agentActive
          ? "AUTO AGENDADO"
          : "SNAPSHOT";

  const liveModeClass = cycleRunning || hasLiveTrades
    ? "bg-primary/10 text-primary"
    : queuedCount > 0
      ? "bg-pending/10 text-pending"
      : agentActive
        ? "bg-accent/10 text-accent"
        : "bg-info/10 text-info";

  const liveModeDescription = cycleRunning
    ? "O autopilot esta executando um novo ciclo agora, atualizando historico, cotacao e monitoramento."
    : hasLiveTrades
      ? `Ha ${liveCount} ${pluralize(liveCount, "microtrade realmente aberto agora", "microtrades realmente abertos agora")}. Setups em observacao e historico ficam separados abaixo.`
      : queuedCount > 0
        ? `Nao ha operacao realmente aberta neste instante. Existem ${queuedCount} ${pluralize(queuedCount, "setup em observacao aguardando gatilho", "setups em observacao aguardando gatilho")} abaixo.`
        : agentActive
          ? "O autopilot segue ligado e agendado, mas sem uma janela realmente ativa neste instante. A tela abaixo mostra o ultimo snapshot persistido do laboratorio."
          : cycle
            ? "Sem ciclo automatico ativo no momento. A tela abaixo mostra o ultimo snapshot persistido do laboratorio."
            : "Aguardando o primeiro ciclo automatico de microtrades para popular o laboratorio.";

  const counts = data.reduce<Record<string, number>>((acc, microtrade) => {
    acc[microtrade.status] = (acc[microtrade.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-5 animate-fade-up">
      <section className="lab-card p-4 relative overflow-hidden">
        <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-primary/10 blur-2xl" />
        <div className="relative space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/15 grid place-items-center">
              <FlaskConical className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h2 className="font-display text-base font-semibold">Laboratorio Realtime</h2>
                <span className={cn("pill text-[10px]", liveModeClass)}>
                  <span className={cn("w-1.5 h-1.5 rounded-full bg-current", (cycleRunning || hasLiveTrades) && "animate-live")} />
                  {liveModeLabel}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{liveModeDescription}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
            <PulseChip label="Preparando" n={counts.preparando ?? 0} cls="bg-muted text-muted-foreground" />
            <PulseChip label="Confirmando" n={counts.confirmando ?? 0} cls="bg-pending/15 text-pending" live />
            <PulseChip label="Monitorando" n={counts.monitorando ?? 0} cls="bg-primary/15 text-primary" live />
            <PulseChip label="Validadas" n={counts.validada ?? 0} cls="bg-validated/15 text-validated" />
            <PulseChip label="Refutadas" n={counts.refutada ?? 0} cls="bg-refuted/15 text-refuted" />
            <PulseChip label="Por tempo" n={counts.encerrada_tempo ?? 0} cls="bg-info/15 text-info" />
          </div>

          <AutopilotOverview cycle={cycle} />
          <CollectionStrip sections={sections} />
          <CandidateRadar suggestions={candidateSuggestions} />
        </div>
      </section>

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 2 }).map((_, index) => (
            <div key={index} className="h-72 rounded-xl bg-surface-1 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && data.length > 0 && (
        <div className="space-y-6">
          {sections.activeNow.length > 0 && (
            <LabSection
              title="Em andamento agora"
              count={sections.activeNow.length}
              tone="active"
              description="Microtrades com janela viva, tick recente e possibilidade real de gain ou stop agora."
            >
              {sections.activeNow.map((microtrade) => (
                <MicrotradeBlock key={microtrade.id} m={microtrade} view="active" />
              ))}
            </LabSection>
          )}

          {sections.activeNow.length === 0 && (
            <EmptyCollectionNotice
              tone={sections.queued.length > 0 ? "queued" : "history"}
              title={
                sections.queued.length > 0
                  ? "Nenhuma operacao em andamento agora"
                  : "Somente historico encerrado neste momento"
              }
              description={
                sections.queued.length > 0
                  ? `Existem ${sections.queued.length} ${pluralize(sections.queued.length, "setup aberto em observacao", "setups abertos em observacao")} logo abaixo.`
                  : `Os ${historicalCount} cards abaixo representam resultados encerrados recentemente e servem como leitura de contexto e aprendizado.`
              }
            />
          )}

          {sections.queued.length > 0 && (
            <LabSection
              title="Observacao e preparo"
              count={sections.queued.length}
              tone="queued"
              description="Teses abertas, mas sem janela realmente ativa agora. Aqui ficam setups aguardando gatilho, tick mais fresco ou nova rodada do motor."
            >
              {sections.queued.map((microtrade) => (
                <MicrotradeBlock key={microtrade.id} m={microtrade} view="queued" />
              ))}
            </LabSection>
          )}

          {sections.recentClosed.length > 0 && (
            <LabSection
              title="Historico recente"
              count={sections.recentClosed.length}
              tone="history"
              description="Resultados ja encerrados. Eles ajudam a ler o que acabou de acontecer sem parecer que ainda existe operacao aberta."
            >
              {sections.recentClosed.map((microtrade) => (
                <MicrotradeBlock key={microtrade.id} m={microtrade} view="history" />
              ))}
            </LabSection>
          )}
        </div>
      )}

      {!isLoading && data.length === 0 && (
        <div className="glass-card p-8 text-center text-sm text-muted-foreground">
          Nenhum microtrade disponivel. O laboratorio esta em standby aguardando setup.
        </div>
      )}
    </div>
  );
}

function PulseChip({ label, n, cls, live }: { label: string; n: number; cls: string; live?: boolean }) {
  return (
    <div className={cn("rounded-lg px-2 py-1.5 flex items-start justify-between gap-2 min-w-0", cls)}>
      <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider leading-tight min-w-0">
        <span className={cn("w-1.5 h-1.5 rounded-full bg-current opacity-90", live && n > 0 && "animate-pulse-slow")} />
        <span>{label}</span>
      </span>
      <span className="font-mono text-sm font-semibold tabular shrink-0">{n}</span>
    </div>
  );
}

function AutopilotOverview({ cycle }: { cycle?: MicrotradesAutopilotLatest }) {
  if (!cycle) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 bg-surface-1/60 p-3 text-xs text-muted-foreground">
        Ainda nao existe um snapshot do autopilot neste ambiente. Assim que o primeiro ciclo automatico rodar, esta area passa a mostrar status, recencia e saude do laboratorio.
      </div>
    );
  }

  const visual = autopilotVisual(cycle);
  const scope = cycle.instruments.length
    ? cycle.instruments.map(formatMicrotradeInstrument).join(" · ")
    : "escopo nao informado";
  const lastCycleAt = cycle.lastActivityAt || cycle.runFinishedAt || cycle.lastRunAt;
  const nextValue = cycle.isRunning ? "agora" : cycle.nextRunAt ? fmtTime(cycle.nextRunAt) : cycle.agentRunning ? "aguardando" : "--";
  const nextSub = cycle.isRunning ? "ciclo em execucao" : cycle.agentRunning ? "agente ligado" : "agente inativo";
  const lastLabel = cycle.isRunning ? "Inicio atual" : "Ultima atividade";

  return (
    <div className={cn("rounded-xl border p-3 space-y-3", visual.wrap)}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground flex items-center gap-1.5">
              <RefreshCw className={cn("w-3 h-3", cycle.isRunning && "animate-spin")} />
              Autopilot
            </span>
            <span className={cn("pill text-[10px]", visual.pill)}>
              <span className={cn("w-1.5 h-1.5 rounded-full bg-current", cycle.isRunning && "animate-live")} />
              {cycle.cycleLabel}
            </span>
            <span className="pill bg-surface-2 text-foreground/80 text-[10px]">{scope}</span>
          </div>
          <div className="text-sm font-semibold text-foreground">{cycle.statusHeadline}</div>
          <p className="text-xs text-muted-foreground leading-relaxed">{cycle.statusDetail}</p>
        </div>
        {(cycle.cycleStatus === "failed" || cycle.cycleStatus === "partial") && (
          <AlertTriangle className={cn("w-4 h-4 shrink-0 mt-0.5", cycle.cycleStatus === "failed" ? "text-refuted" : "text-pending")} />
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <LabMetric
          label={lastLabel}
          value={lastCycleAt ? fmtRelative(lastCycleAt) : "--"}
          sub={lastCycleAt ? fmtTime(lastCycleAt) : "sem historico"}
        />
        <LabMetric label="Proximo" value={nextValue} sub={nextSub} />
        <LabMetric
          label="Teses"
          value={`${cycle.monitoringCount || cycle.thesisCount}`}
          sub={cycle.needsAttentionCount > 0 ? `${cycle.needsAttentionCount} em atencao` : "sem alertas de tese"}
        />
        <LabMetric label="Ciclos hoje" value={`${cycle.cyclesToday}`} sub={`intervalo ${cycle.intervalLabel}`} />
      </div>

      <div className="flex flex-wrap gap-1.5">
        <PulseChip label="Etapas OK" n={cycle.stepCounts.ok} cls="bg-validated/15 text-validated" />
        <PulseChip label="Ressalvas" n={cycle.stepCounts.warning} cls="bg-pending/15 text-pending" />
        <PulseChip label="Erros" n={cycle.stepCounts.error} cls="bg-refuted/15 text-refuted" />
        <span className={cn("pill text-[10px]", decisionStatusClass(cycle.decisionStatus))}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {decisionStatusLabel(cycle.decisionStatus)}
        </span>
      </div>
    </div>
  );
}

function LabMetric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-surface-1/80 px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono text-sm font-semibold tabular text-foreground">{value}</div>
      <div className="text-[10px] text-muted-foreground tabular mt-0.5">{sub ?? "\u00A0"}</div>
    </div>
  );
}

function CollectionStrip({ sections }: { sections: LabSections }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      <CollectionStat label="Em andamento" n={sections.activeNow.length} cls="bg-primary/10 border-primary/25 text-primary" />
      <CollectionStat label="Observacao" n={sections.queued.length} cls="bg-pending/10 border-pending/25 text-pending" />
      <CollectionStat label="Historico" n={sections.recentClosed.length} cls="bg-surface-1 border-border/60 text-muted-foreground" />
    </div>
  );
}

function CandidateRadar({ suggestions }: { suggestions: LabCandidateSuggestion[] }) {
  const usingActiveFallback = suggestions.length > 0 && suggestions[0]?.source === "active";

  return (
    <div className="space-y-2">
      <div className="px-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-display text-base font-semibold text-foreground">Radar de candidatas</h3>
          <span className={cn("pill text-[10px]", suggestions.length > 0 ? "bg-primary/10 text-primary" : "bg-surface-2 text-foreground/70")}>
            {suggestions.length}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
          {usingActiveFallback
            ? "Nao ha candidatas puras em observacao agora. O radar esta destacando os setups vivos mais acionaveis."
            : "Teses que ainda nao viraram operacao viva, mas merecem preparacao agora."}
        </p>
      </div>

      {suggestions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/70 bg-surface-1/60 p-3 text-xs text-muted-foreground">
          Nenhuma candidata forte no momento. Quando o laboratorio abrir setups em observacao, elas aparecem aqui com prioridade, janela esperada e motivo do gatilho.
        </div>
      ) : (
        <div className="space-y-2">
          {suggestions.map((suggestion) => (
            <CandidateCard key={suggestion.thesis.id} suggestion={suggestion} />
          ))}
        </div>
      )}
    </div>
  );
}

function CandidateCard({ suggestion }: { suggestion: LabCandidateSuggestion }) {
  const thesis = suggestion.thesis;
  const priorityClass =
    suggestion.priority === "alta"
      ? "bg-validated/12 text-validated border-validated/30"
      : suggestion.priority === "media"
        ? "bg-pending/12 text-pending border-pending/30"
        : "bg-surface-2 text-foreground/80 border-border/60";

  return (
    <div className="glass-card p-3 border border-border/60 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-display text-sm font-semibold text-foreground">{thesis.asset_label}</span>
            <FrenteBadge frente={apiFrenteToFrente(thesis.front)} className="text-[10px] py-0.5" />
            <span className="pill bg-surface-2 text-foreground/75 text-[10px]">
              {suggestion.source === "queued" ? "em observacao" : "ao vivo"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{suggestion.triggerReason}</p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={cn("pill text-[10px] border", priorityClass)}>{suggestion.priority}</span>
          <span className="pill bg-accent/10 text-accent text-[10px]">{suggestion.expectedTimeLabel}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <CandidateMetric label="Score" value={`${suggestion.score}`} accent="text-primary" />
        <CandidateMetric label="Pressao" value={`${suggestion.triggerPressurePct}%`} accent="text-accent" />
        <CandidateMetric label="Confianca" value={`${Math.round(thesis.confidence_pct)}%`} accent="text-foreground" />
      </div>

      <div className="flex items-center justify-between gap-3 text-[11px] border-t border-border/50 pt-2.5">
        <span className="text-muted-foreground truncate">{suggestion.nextStepLabel}</span>
        <span className="shrink-0 text-muted-foreground">{fmtRelative(thesis.updated_at)}</span>
      </div>
    </div>
  );
}

function CandidateMetric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("font-mono text-sm font-semibold tabular", accent)}>{value}</div>
    </div>
  );
}

function CollectionStat({ label, n, cls }: { label: string; n: number; cls: string }) {
  return (
    <div className={cn("rounded-lg border px-3 py-2", cls)}>
      <div className="text-[10px] uppercase tracking-wider">{label}</div>
      <div className="font-mono text-lg font-semibold tabular mt-1">{n}</div>
    </div>
  );
}

function EmptyCollectionNotice({
  title,
  description,
  tone,
}: {
  title: string;
  description: string;
  tone: "queued" | "history";
}) {
  const toneClass = tone === "queued"
    ? "border-pending/30 bg-pending/5"
    : "border-info/25 bg-info/5";

  return (
    <div className={cn("glass-card p-4 border", toneClass)}>
      <div className="font-display text-base font-semibold text-foreground">{title}</div>
      <p className="text-sm text-muted-foreground mt-1">{description}</p>
    </div>
  );
}

function LabSection({
  title,
  description,
  count,
  tone,
  children,
}: {
  title: string;
  description: string;
  count: number;
  tone: "active" | "queued" | "history";
  children: ReactNode;
}) {
  const pillClass = tone === "active"
    ? "bg-primary/10 text-primary"
    : tone === "queued"
      ? "bg-pending/10 text-pending"
      : "bg-surface-2 text-foreground/80";

  return (
    <section className="space-y-3">
      <div className="px-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-display text-base font-semibold text-foreground">{title}</h3>
          <span className={cn("pill text-[10px]", pillClass)}>{count}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{description}</p>
      </div>
      <div className="space-y-6">{children}</div>
    </section>
  );
}

function autopilotVisual(cycle: MicrotradesAutopilotLatest) {
  if (cycle.isRunning) {
    return { wrap: "border-primary/40 bg-primary/5", pill: "bg-primary/15 text-primary" };
  }
  if (cycle.cycleStatus === "success") {
    return { wrap: "border-validated/35 bg-validated/5", pill: "bg-validated/15 text-validated" };
  }
  if (cycle.cycleStatus === "partial") {
    return { wrap: "border-pending/35 bg-pending/5", pill: "bg-pending/15 text-pending" };
  }
  if (cycle.cycleStatus === "failed") {
    return { wrap: "border-refuted/35 bg-refuted/5", pill: "bg-refuted/15 text-refuted" };
  }
  return { wrap: "border-info/35 bg-info/5", pill: "bg-info/10 text-info" };
}

function decisionStatusLabel(status: string) {
  if (status === "created") return "Card publicado";
  if (status === "cooldown") return "Centro em cooldown";
  if (status === "skipped") return "Sem card novo";
  if (status === "error") return "Falha ao publicar";
  return `Decisao ${status || "indefinida"}`;
}

function decisionStatusClass(status: string) {
  if (status === "created") return "bg-validated/15 text-validated";
  if (status === "cooldown") return "bg-pending/15 text-pending";
  if (status === "error") return "bg-refuted/15 text-refuted";
  return "bg-surface-2 text-foreground/80";
}

function formatMicrotradeInstrument(value: string) {
  const upper = value.toUpperCase();
  for (const suffix of ["USDT", "USDC", "BUSD", "FDUSD", "BTC", "ETH"]) {
    if (upper.endsWith(suffix) && upper.length > suffix.length) {
      return `${upper.slice(0, upper.length - suffix.length)}/${suffix}`;
    }
  }
  return upper;
}

function statusVisual(status: StatusTese) {
  switch (status) {
    case "preparando":
      return { ring: "border-border-strong", glow: "" };
    case "confirmando":
      return { ring: "border-pending/50", glow: "shadow-[0_0_30px_-10px_hsl(var(--pending)/0.5)]" };
    case "monitorando":
      return { ring: "border-primary/50", glow: "shadow-glow" };
    case "validada":
      return { ring: "border-validated/60", glow: "" };
    case "refutada":
      return { ring: "border-refuted/60", glow: "" };
    case "encerrada_tempo":
      return { ring: "border-info/40", glow: "" };
    default:
      return { ring: "border-border", glow: "" };
  }
}

function MicrotradeBlock({
  m,
  view,
}: {
  m: TheseEnvelope;
  view: "active" | "queued" | "history";
}) {
  const spec = m.specific as Partial<SpecificMicrotrade>;
  const isMicrotrade = spec.kind === "microtrade";
  const delayed = Boolean(spec.is_data_delayed);
  const pressure = (spec.trigger_pressure_pct ?? 0) / 100;
  const evidences = spec.evidences ?? [];
  const stop = m.stop_value ?? m.entry_value;
  const distAlvo = ((m.target_value - m.current_value) / m.current_value) * 100;
  const distStop = ((stop - m.current_value) / m.current_value) * 100;
  const visual = statusVisual(m.status);
  const closed = isClosedThesis(m);
  const live = isLiveLabMicrotrade(m);

  const thesisLabel = view === "active"
    ? "Tese ativa"
    : view === "queued"
      ? "Tese em observacao"
      : "Tese encerrada";

  const trackingLabel = view === "active"
    ? "Monitoramento em tempo real"
    : view === "queued"
      ? "Acompanhamento sem janela ativa"
      : "Snapshot do ultimo ciclo";

  const footerLabel = view === "active"
    ? "auto-atualizacao ativa"
    : view === "queued"
      ? "monitorando sem gatilho ativo"
      : "snapshot sem atualizacao ativa";

  return (
    <article className="space-y-3">
      <header className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="font-display text-base font-semibold">{m.asset_label}</span>
          <FrenteBadge frente={apiFrenteToFrente(m.front)} />
        </div>
        <div className="flex items-center gap-2">
          <CompletionRing pct={m.completion.completion_pct} />
          <FreshnessBadge
            status={delayed ? "partial" : m.data_quality.freshness_status}
            lastUpdateAt={spec.last_tick_at ?? m.data_quality.last_update_at}
          />
        </div>
      </header>

      <div className={cn("glass-card p-4 space-y-3.5 border-2", visual.ring)}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground flex items-center gap-1.5">
            <FlaskConical className="w-3 h-3" /> {closed ? "Tese encerrada" : thesisLabel}
          </span>
          <StatusPill status={m.status} />
        </div>

        <p className="text-sm text-foreground/90 leading-relaxed">{m.hypothesis}</p>

        <div className="grid grid-cols-3 gap-3">
          <Mini label="Esperado" value={fmtPct(m.expected_result_pct)} c="text-gold" />
          <Mini label="Real" value={fmtPct(m.current_result_pct)} c={m.current_result_pct >= 0 ? "text-validated" : "text-refuted"} />
          <Mini label="Confianca" value={`${Math.round(m.confidence_pct)}%`} c="text-primary" />
        </div>

        <ConfidenceBar value={m.confidence_pct / 100} />

        {isMicrotrade && spec.window_min !== undefined && spec.expires_at && !closed && live && (
          <div className="rounded-xl bg-gradient-to-br from-accent/10 to-pending/5 border border-accent/40 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-accent">
                <Timer className="w-3.5 h-3.5" /> Janela ativa
              </span>
              <span className="text-[10px] text-muted-foreground tabular">
                {spec.window_min} min · {fmtTime(m.opened_at)}
              </span>
            </div>
            <div className="flex items-end justify-between">
              <Countdown iso={spec.expires_at} className="font-display text-4xl font-semibold text-accent tabular leading-none" />
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground pb-1">expira em</span>
            </div>
          </div>
        )}

        {closed && <ClosedBanner status={m.status} />}

        <div className="grid grid-cols-3 gap-3 pt-1">
          <Mini label="Entrada" value={fmtNumber(m.entry_value, 2)} />
          <Mini label="Alvo" value={fmtNumber(m.target_value, 2)} c="text-validated" />
          <Mini label="Stop" value={fmtNumber(stop, 2)} c="text-refuted" />
        </div>
      </div>

      <div className={cn("lab-card p-4 space-y-4", visual.glow)}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-primary flex items-center gap-1.5">
            <Radio className={cn("w-3 h-3", live && "animate-pulse-slow")} /> {trackingLabel}
          </span>
          {delayed && (
            <span className="pill bg-pending/15 text-pending text-[10px]">
              <AlertTriangle className="w-3 h-3" /> dado atrasado
            </span>
          )}
        </div>

        <div className="flex items-end justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Preco atual</div>
            <div className="font-display text-3xl font-semibold tabular">{fmtNumber(m.current_value, 2)}</div>
            <div className={cn("text-sm font-mono tabular", m.current_result_pct >= 0 ? "text-validated" : "text-refuted")}>
              {fmtPct(m.current_result_pct)} desde abertura
            </div>
          </div>
          <PressureGauge value={pressure} />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">
              <Zap className="w-3 h-3 text-accent" /> Pressao dos gatilhos
            </span>
            <span
              className={cn(
                "font-mono text-xs tabular font-semibold",
                pressure >= 0.75 ? "text-validated" : pressure >= 0.45 ? "text-primary" : "text-pending",
              )}
            >
              {Math.round(pressure * 100)}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-surface-2 overflow-hidden">
            <div
              className={cn(
                "h-full transition-all",
                pressure >= 0.75 ? "bg-validated" : pressure >= 0.45 ? "bg-primary" : "bg-pending",
              )}
              style={{ width: `${pressure * 100}%` }}
            />
          </div>
        </div>

        <ProgressToTarget entrada={m.entry_value} alvo={m.target_value} stop={stop} precoAtual={m.current_value} />

        <div className="grid grid-cols-3 gap-3 pt-1">
          <Mini label="Resultado real" value={fmtPct(m.current_result_pct)} c={m.current_result_pct >= 0 ? "text-validated" : "text-refuted"} />
          <Mini label="Dist. ao alvo" value={fmtPct(distAlvo)} />
          <Mini label="Dist. ao stop" value={fmtPct(distStop)} c="text-refuted" />
        </div>

        {evidences.length > 0 && (
          <div className="border-t border-border/60 pt-2.5">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Evidencias</div>
            <div className="flex flex-wrap gap-1.5">
              {evidences.map((evidence, index) => (
                <span key={index} className="pill bg-surface-2 text-foreground/85 text-[10px]">
                  {evidence}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/60 pt-2.5">
          <span className="flex items-center gap-1.5">
            <Activity className={cn("w-3 h-3", live && "text-primary")} /> {footerLabel}
          </span>
          <span>{m.suggested_action}</span>
        </div>
        {spec.last_tick_at && (
          <div className="text-[10px] text-muted-foreground tabular -mt-2">
            ultimo tick {fmtRelative(spec.last_tick_at)}
          </div>
        )}
      </div>
    </article>
  );
}

function ClosedBanner({ status }: { status: StatusTese }) {
  const map = {
    validada: { icon: CheckCircle2, cls: "bg-validated/10 border-validated/40 text-validated", label: "Hipotese validada - gain confirmado" },
    refutada: { icon: XCircle, cls: "bg-refuted/10 border-refuted/40 text-refuted", label: "Hipotese refutada - loss registrado" },
    encerrada_tempo: { icon: Timer, cls: "bg-info/10 border-info/40 text-info", label: "Encerrada por tempo - janela expirou" },
  } as Record<string, { icon: LucideIcon; cls: string; label: string }>;

  const meta = map[status];
  if (!meta) return null;
  const Icon = meta.icon;

  return (
    <div className={cn("rounded-lg border p-3 flex items-center gap-2 text-xs font-medium", meta.cls)}>
      <Icon className="w-4 h-4 shrink-0" />
      {meta.label}
    </div>
  );
}

function Mini({ label, value, c = "text-foreground" }: { label: string; value: string; c?: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("font-mono text-sm font-semibold tabular capitalize", c)}>{value}</div>
    </div>
  );
}

function pluralize(value: number, singular: string, plural: string) {
  return value === 1 ? singular : plural;
}
