import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Minus, Newspaper, BarChart3, LineChart, Sparkles, ShieldAlert, type LucideIcon } from "lucide-react";
import type { TheseEnvelope, SpecificB3 } from "@/types/domain";
import { ProgressToTarget } from "@/components/ProgressToTarget";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { fmtNumber, fmtPct, fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

export function B3Panel({ t }: { t: TheseEnvelope }) {
  const s = t.specific as Partial<SpecificB3>;
  const stop = t.stop_value ?? t.entry_value;
  const dirIcon = s.direction === "short" ? ArrowDown : s.direction === "long" ? ArrowUp : Minus;
  const DirIcon = dirIcon;
  const dirColor =
    s.direction === "long" ? "text-validated bg-validated/10 border-validated/30"
    : s.direction === "short" ? "text-refuted bg-refuted/10 border-refuted/30"
    : "text-muted-foreground bg-surface-2 border-border";

  return (
    <div className="space-y-4">
      {/* Cabeçalho de ativo listado */}
      <section className="glass-card p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Ativo listado · B3</div>
            <div className="font-display text-2xl font-semibold tabular">{s.ticker ?? t.asset_label}</div>
          </div>
          <span className={cn("pill border text-[11px] uppercase tracking-wider", dirColor)}>
            <DirIcon className="w-3 h-3" /> {s.direction ?? "neutra"}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <Mini label="Preço" value={fmtNumber(t.current_value, 2)} />
          <Mini label="Entrada" value={fmtNumber(t.entry_value, 2)} />
          <Mini label="Resultado" value={fmtPct(t.current_result_pct)} c={t.current_result_pct >= 0 ? "text-validated" : "text-refuted"} />
        </div>

        <ProgressToTarget entrada={t.entry_value} alvo={t.target_value} stop={stop} precoAtual={t.current_value} />

        <div className="grid grid-cols-3 gap-3 pt-1">
          <Mini label="Alvo" value={fmtNumber(t.target_value, 2)} c="text-validated" />
          <Mini label="Stop" value={fmtNumber(stop, 2)} c="text-refuted" />
          <Mini label="Esperado" value={fmtPct(t.expected_result_pct)} c="text-gold" />
        </div>

        <ConfidenceBar value={t.confidence_pct / 100} />
      </section>

      {/* Sinais técnicos */}
      {s.technicals && s.technicals.length > 0 && (
        <Section icon={LineChart} title="Sinais técnicos">
          <div className="grid grid-cols-2 gap-2">
            {s.technicals.map((sig, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface-1 border border-border/60 px-3 py-2">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{sig.label}</div>
                  <div className="text-sm font-mono tabular">{sig.value ?? "—"}</div>
                </div>
                <BiasDot bias={sig.bias} />
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Fundamentos */}
      {s.fundamentals && s.fundamentals.length > 0 && (
        <Section icon={BarChart3} title="Fundamentos">
          <div className="grid grid-cols-2 gap-2">
            {s.fundamentals.map((f, i) => (
              <div key={i} className="rounded-lg bg-surface-1 border border-border/60 px-3 py-2">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{f.label}</div>
                <div className="text-sm font-mono tabular">{f.value}</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Notícias */}
      {s.news && s.news.length > 0 && (
        <Section icon={Newspaper} title="Notícias relacionadas">
          <ul className="space-y-2.5">
            {s.news.map((n, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <SentimentDot s={n.sentiment} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-foreground/90 leading-snug">{n.title}</div>
                  <div className="text-[11px] text-muted-foreground tabular">{n.source} · {fmtRelative(n.published_at)}</div>
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Evidências */}
      {s.evidences && s.evidences.length > 0 && (
        <Section icon={Sparkles} title="Principais evidências">
          <div className="flex flex-wrap gap-1.5">
            {s.evidences.map((e, i) => (
              <span key={i} className="pill bg-surface-2 text-foreground/85 text-[11px]">{e}</span>
            ))}
          </div>
        </Section>
      )}

      {/* Invalidação */}
      <Section icon={ShieldAlert} title="O que invalida a tese">
        <p className="text-sm text-foreground/90 leading-relaxed">{t.stop_or_invalidation}</p>
      </Section>
    </div>
  );
}

function BiasDot({ bias }: { bias: "bull" | "bear" | "neutral" }) {
  const map = { bull: "bg-validated", bear: "bg-refuted", neutral: "bg-muted-foreground" } as const;
  return <span className={cn("w-2 h-2 rounded-full", map[bias])} />;
}
function SentimentDot({ s }: { s?: "positivo" | "negativo" | "neutro" }) {
  const map = { positivo: "bg-validated", negativo: "bg-refuted", neutro: "bg-muted-foreground" } as const;
  return <span className={cn("mt-1.5 w-1.5 h-1.5 rounded-full shrink-0", map[s ?? "neutro"])} />;
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
