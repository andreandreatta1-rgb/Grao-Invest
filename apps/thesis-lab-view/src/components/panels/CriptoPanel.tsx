import type { ReactNode } from "react";
import { Activity, AlertTriangle, FlaskConical, Radio, ShieldAlert, Sparkles, Timer, type LucideIcon } from "lucide-react";
import type { TheseEnvelope, SpecificMicrotrade } from "@/types/domain";
import { ProgressToTarget } from "@/components/ProgressToTarget";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { PressureGauge } from "@/components/PressureGauge";
import { Countdown } from "@/components/Countdown";
import { fmtNumber, fmtPct, fmtRelative, fmtTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CriptoPanel({ t }: { t: TheseEnvelope }) {
  const s = t.specific as Partial<SpecificMicrotrade>;
  const stop = t.stop_value ?? t.entry_value;
  const pressure = (s.trigger_pressure_pct ?? 0) / 100;
  const delayed = !!s.is_data_delayed;
  const live = isLiveMicrotrade(t);

  return (
    <div className="space-y-4">
      <section className="lab-card p-4 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-primary flex items-center gap-1.5">
            <Radio className={cn("w-3 h-3", live && "animate-live")} /> {live ? "Monitoramento realtime" : "Snapshot monitorado"}
          </span>
          <span className={cn("pill text-[10px]", live ? "bg-primary/10 text-primary" : "bg-info/10 text-info")}>
            <span className={cn("w-1.5 h-1.5 rounded-full bg-current", live && "animate-live")} />
            {live ? "AO VIVO" : "SNAPSHOT"}
          </span>
        </div>

        <div className="flex items-end justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Moeda | {t.asset_label}</div>
            <div className="font-display text-3xl font-semibold tabular">{fmtNumber(t.current_value, 2)}</div>
            <div className={cn("text-sm font-mono tabular", t.current_result_pct >= 0 ? "text-validated" : "text-refuted")}>
              {fmtPct(t.current_result_pct)} desde abertura
            </div>
          </div>
          <PressureGauge value={pressure} />
        </div>

        {s.window_min !== undefined && s.expires_at && live && (
          <div className="flex items-center justify-between rounded-lg bg-surface-1 border border-border/60 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <Timer className="w-4 h-4 text-accent" />
              <div className="leading-tight">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Janela esperada</div>
                <div className="text-xs text-muted-foreground tabular">{s.window_min} min | abertura {fmtTime(t.opened_at)}</div>
              </div>
            </div>
            <div className="text-right leading-tight">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Expira em</div>
              <Countdown iso={s.expires_at} className="text-base font-semibold text-accent" />
            </div>
          </div>
        )}

        <ProgressToTarget entrada={t.entry_value} alvo={t.target_value} stop={stop} precoAtual={t.current_value} />

        <div className="grid grid-cols-3 gap-3">
          <Mini label="Entrada" value={fmtNumber(t.entry_value, 2)} />
          <Mini label="Alvo" value={fmtNumber(t.target_value, 2)} c="text-validated" />
          <Mini label="Stop" value={fmtNumber(stop, 2)} c="text-refuted" />
        </div>

        <ConfidenceBar value={t.confidence_pct / 100} />

        {delayed && (
          <div className="pill bg-pending/15 text-pending text-[10px]">
            <AlertTriangle className="w-3 h-3" /> dado atrasado
          </div>
        )}

        <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/60 pt-2.5">
          <span className="flex items-center gap-1.5"><Activity className={cn("w-3 h-3", live && "text-primary")} /> {live ? "auto-atualizacao ativa" : "snapshot sem atualizacao ativa"}</span>
          {s.last_tick_at && <span className="tabular">ultimo tick {fmtRelative(s.last_tick_at)}</span>}
        </div>
      </section>

      {s.evidences && s.evidences.length > 0 && (
        <Section icon={Sparkles} title="Gatilhos de confirmacao">
          <div className="flex flex-wrap gap-1.5">
            {s.evidences.map((e, i) => (
              <span key={i} className="pill bg-surface-2 text-foreground/85 text-[11px]">{e}</span>
            ))}
          </div>
        </Section>
      )}

      <Section icon={FlaskConical} title="Hipotese">
        <p className="text-sm text-foreground/90 leading-relaxed">{t.hypothesis}</p>
      </Section>

      <Section icon={ShieldAlert} title="O que invalida a tese">
        <p className="text-sm text-foreground/90 leading-relaxed">{t.stop_or_invalidation}</p>
      </Section>
    </div>
  );
}

function Mini({ label, value, c = "text-foreground" }: { label: string; value: string; c?: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("font-mono text-sm font-semibold tabular", c)}>{value}</div>
    </div>
  );
}

function Section({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="flex items-center gap-2 px-1 font-display text-sm font-semibold">
        <Icon className="w-4 h-4 text-primary" /> {title}
      </h3>
      <div className="glass-card p-4">{children}</div>
    </section>
  );
}

function isLiveMicrotrade(t: TheseEnvelope) {
  const s = t.specific as Partial<SpecificMicrotrade>;
  if (s.kind !== "microtrade") return false;
  if (t.closed_at) return false;
  if (!s.last_tick_at || !s.expires_at) return false;
  const lastTickAgeMs = Date.now() - new Date(s.last_tick_at).getTime();
  const expiresAtMs = new Date(s.expires_at).getTime();
  return Number.isFinite(lastTickAgeMs) && lastTickAgeMs <= 10 * 60_000 && expiresAtMs > Date.now();
}
