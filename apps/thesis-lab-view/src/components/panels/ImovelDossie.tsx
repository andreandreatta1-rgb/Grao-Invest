import {
  AlertTriangle, Building2, CheckCircle2, ClipboardList, Coins, FileText,
  HelpCircle, ListChecks, MapPin, Route, ShieldAlert, Sparkles, Target, XCircle,
} from "lucide-react";
import type { ReactNode } from "react";
import type { TheseEnvelope, SpecificImovel, DiligenceState } from "@/types/domain";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { fmtMoney, fmtPct, fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Painel de dossiê de imóvel.
 * Tolerante a campos faltantes — campos ausentes viram "—" ou badge "faltando".
 */
export function ImovelDossie({ t }: { t: TheseEnvelope }) {
  const s = (t.specific ?? {}) as Partial<SpecificImovel>;
  const score = s.score_pct ?? Math.round(t.confidence_pct);
  const completionLow = t.completion.completion_pct < 70;

  return (
    <div className="space-y-4">
      {/* RESUMO EXECUTIVO */}
      <section className="glass-card p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">
              <Building2 className="w-3 h-3" /> Dossiê de oportunidade · Imóveis
            </div>
            <div className="font-display text-lg font-semibold leading-snug mt-0.5 truncate">{t.title || t.asset_label}</div>
            {(s.city || s.neighborhood) && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                <MapPin className="w-3 h-3" />
                {[s.neighborhood, s.city].filter(Boolean).join(" · ")}
              </div>
            )}
          </div>
          <ScoreRing pct={score} />
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1">
          <Field label="Estratégia" value={prettyStrategy(s.strategy)} />
          <Field label="Tipo" value={s.property_type} />
          <Field label="Origem" value={s.origin} />
          <Field label="Status" value={prettyStatus(s.imovel_status)} />
        </div>

        <ConfidenceBar value={t.confidence_pct / 100} />

        {s.next_step && (
          <div className="rounded-lg bg-primary/8 border border-primary/30 p-3 text-sm text-primary">
            <span className="text-[10px] uppercase tracking-wider opacity-80 block mb-0.5">Próximo passo</span>
            {s.next_step}
          </div>
        )}
      </section>

      {/* VALORES */}
      <Section icon={Coins} title="Valores">
        <div className="grid grid-cols-2 gap-2">
          <Money label="Preço pedido" v={s.asking_price} />
          <Money label="Valor de avaliação" v={s.appraisal_value} />
          <Money label="Mercado estimado" v={s.market_value_estimate} />
          <Money label="Teto de compra" v={s.ceiling_price} highlight="text-validated" />
          <Money label="Caixa necessário" v={s.cash_needed} highlight="text-pending" />
          <Money label="Reforma" v={s.renovation_budget} />
          <Money label="Carrego mensal" v={s.monthly_carrying_cost} />
          <Field label="Carrego (meses)" value={s.carrying_months !== undefined ? `${s.carrying_months} m` : undefined} />
        </div>
      </Section>

      {/* CENÁRIOS */}
      <Section icon={Target} title="Cenários de venda e renda">
        <div className="space-y-2">
          <ScenarioRow label="Venda conservadora" v={s.estimated_sale_conservative} />
          <ScenarioRow label="Venda base" v={s.estimated_sale_base} highlight />
          <ScenarioRow label="Venda otimista" v={s.estimated_sale_optimistic} />
          <ScenarioRow label="Aluguel conservador" v={s.estimated_rent_conservative} suffix="/mês" />
          <div className="grid grid-cols-2 gap-2 pt-1">
            <Field label="ROI estimado" value={s.roi_estimated_pct !== undefined ? fmtPct(s.roi_estimated_pct) : undefined} highlight="text-validated" />
            <Field label="Prazo estimado" value={s.prazo_estimado_meses !== undefined ? `${s.prazo_estimado_meses} meses` : undefined} />
          </div>
          {(s.sale_comparables_count !== undefined || s.rent_comparables_count !== undefined) && (
            <div className="text-[11px] text-muted-foreground tabular pt-1">
              comparáveis: venda {s.sale_comparables_count ?? "—"} · aluguel {s.rent_comparables_count ?? "—"}
            </div>
          )}
        </div>
      </Section>

      {/* DILIGÊNCIA */}
      <Section icon={ClipboardList} title="Diligência e documentação">
        <div className="space-y-1.5">
          {(s.diligence ?? []).map((d, i) => (
            <DiligenceRow key={i} item={d} />
          ))}
          {(s.accepts_financing !== undefined || s.financing_validated !== undefined) && (
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/60">
              <Field label="Aceita financiamento" value={s.accepts_financing === undefined ? undefined : s.accepts_financing ? "Sim" : "Não"} />
              <Field label="Financiamento validado" value={s.financing_validated === undefined ? undefined : s.financing_validated ? "Sim" : "Não"} />
            </div>
          )}
        </div>
      </Section>

      {/* PLANO */}
      {(s.plan_a || s.plan_b || s.plan_c || s.exit_rule) && (
        <Section icon={Route} title="Plano operacional">
          <div className="space-y-2.5">
            {s.plan_a && <PlanRow tag="A" text={s.plan_a} />}
            {s.plan_b && <PlanRow tag="B" text={s.plan_b} />}
            {s.plan_c && <PlanRow tag="C" text={s.plan_c} />}
            {s.exit_rule && (
              <div className="rounded-lg bg-refuted/8 border border-refuted/30 p-2.5 text-xs text-foreground/90">
                <span className="text-[10px] uppercase tracking-wider text-refuted block mb-0.5 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" /> Regra de saída / descarte
                </span>
                {s.exit_rule}
              </div>
            )}
          </div>
        </Section>
      )}

      {/* HIPÓTESE / ANÁLISE */}
      <Section icon={FileText} title="Hipótese e análise">
        <p className="text-sm text-foreground/90 leading-relaxed">{t.hypothesis}</p>
        {s.analysis && <p className="text-xs text-muted-foreground leading-relaxed mt-2">{s.analysis}</p>}
        {s.notes && <p className="text-xs text-muted-foreground leading-relaxed mt-2 italic">{s.notes}</p>}
      </Section>

      {(s.evidences && s.evidences.length > 0) && (
        <Section icon={Sparkles} title="Evidências">
          <div className="flex flex-wrap gap-1.5">
            {s.evidences.map((e, i) => (
              <span key={i} className="pill bg-surface-2 text-foreground/85 text-[11px]">{e}</span>
            ))}
          </div>
        </Section>
      )}

      {t.learning_note && (
        <Section icon={Sparkles} title="Aprendizado incorporado">
          <p className="text-sm text-foreground/90 leading-relaxed">{t.learning_note}</p>
        </Section>
      )}

      {/* COMPLETUDE — destaque para imóveis */}
      <section className={cn(
        "rounded-2xl p-4 space-y-3 border",
        completionLow ? "bg-pending/8 border-pending/40" : "bg-surface-1 border-border"
      )}>
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 font-display text-sm font-semibold">
            <ListChecks className="w-4 h-4 text-pending" /> O que falta para esta tese ficar investível?
          </h3>
          <span className={cn("font-mono text-sm tabular", completionLow ? "text-pending" : "text-validated")}>
            {t.completion.completion_pct}%
          </span>
        </div>
        <div className="h-2 rounded-full bg-surface-2 overflow-hidden">
          <div
            className={cn("h-full transition-all", completionLow ? "bg-pending" : "bg-validated")}
            style={{ width: `${t.completion.completion_pct}%` }}
          />
        </div>

        {t.completion.missing_fields.length > 0 && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Campos faltantes</div>
            <div className="flex flex-wrap gap-1.5">
              {t.completion.missing_fields.map(f => (
                <span key={f} className="pill bg-pending/10 text-pending text-[10px]">{prettifyField(f)}</span>
              ))}
            </div>
          </div>
        )}

        {t.completion.pending_items.length > 0 && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Pendências</div>
            <ul className="space-y-1.5">
              {t.completion.pending_items.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-foreground/90">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-pending shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}

        {t.completion.next_required_action && (
          <button className="w-full rounded-lg bg-primary text-primary-foreground py-2.5 text-sm font-semibold hover:bg-primary/90 transition-colors">
            Complementar agora · {t.completion.next_required_action}
          </button>
        )}
      </section>

      <div className="text-[11px] text-muted-foreground text-center tabular">
        atualizado {fmtRelative(t.updated_at)}
      </div>
    </div>
  );
}

/* ---------- subcomponentes ---------- */

function ScoreRing({ pct }: { pct: number }) {
  const r = 22, c = 2 * Math.PI * r;
  const off = c - (Math.max(0, Math.min(100, pct)) / 100) * c;
  const color = pct >= 70 ? "hsl(var(--validated))" : pct >= 40 ? "hsl(var(--pending))" : "hsl(var(--refuted))";
  return (
    <div className="relative w-[58px] h-[58px] shrink-0">
      <svg viewBox="0 0 56 56" className="w-full h-full -rotate-90">
        <circle cx="28" cy="28" r={r} stroke="hsl(var(--surface-2))" strokeWidth="5" fill="none" />
        <circle cx="28" cy="28" r={r} stroke={color} strokeWidth="5" fill="none"
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 grid place-items-center leading-none">
        <div className="text-center">
          <div className="text-[8px] uppercase tracking-wider text-muted-foreground">Score</div>
          <div className="font-mono text-sm font-semibold tabular">{Math.round(pct)}</div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, highlight = "text-foreground" }: { label: string; value?: string; highlight?: string }) {
  const missing = value === undefined || value === null || value === "";
  return (
    <div className="rounded-lg bg-surface-1 border border-border/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      {missing ? (
        <span className="pill bg-pending/10 text-pending text-[10px] mt-0.5">
          <HelpCircle className="w-3 h-3" /> faltando
        </span>
      ) : (
        <div className={cn("text-sm font-mono tabular capitalize", highlight)}>{value}</div>
      )}
    </div>
  );
}

function Money({ label, v, highlight = "text-foreground" }: { label: string; v?: number; highlight?: string }) {
  return <Field label={label} value={v !== undefined ? fmtMoney(v) : undefined} highlight={highlight} />;
}

function ScenarioRow({ label, v, suffix, highlight }: { label: string; v?: number; suffix?: string; highlight?: boolean }) {
  return (
    <div className={cn(
      "flex items-center justify-between rounded-lg px-3 py-2 border",
      highlight ? "bg-validated/8 border-validated/30" : "bg-surface-1 border-border/60"
    )}>
      <span className="text-xs text-muted-foreground">{label}</span>
      {v === undefined ? (
        <span className="pill bg-pending/10 text-pending text-[10px]"><HelpCircle className="w-3 h-3" /> faltando</span>
      ) : (
        <span className={cn("font-mono text-sm tabular", highlight ? "text-validated font-semibold" : "")}>
          {fmtMoney(v)}{suffix ?? ""}
        </span>
      )}
    </div>
  );
}

function DiligenceRow({ item }: { item: { label: string; state: DiligenceState; detail?: string } }) {
  const map: Record<DiligenceState, { icon: LucideIcon; cls: string; label: string }> = {
    ok:           { icon: CheckCircle2,  cls: "text-validated bg-validated/10", label: "ok" },
    pendente:     { icon: HelpCircle,    cls: "text-pending bg-pending/10",     label: "pendente" },
    nao_validado: { icon: AlertTriangle, cls: "text-pending bg-pending/10",     label: "não validado" },
    faltando:     { icon: XCircle,       cls: "text-refuted bg-refuted/10",     label: "faltando" },
    alerta:       { icon: AlertTriangle, cls: "text-refuted bg-refuted/10",     label: "alerta" },
  };
  const m = map[item.state];
  const Icon = m.icon;
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg bg-surface-1 border border-border/60 px-3 py-2">
      <div className="min-w-0">
        <div className="text-sm text-foreground/90">{item.label}</div>
        {item.detail && <div className="text-[11px] text-muted-foreground">{item.detail}</div>}
      </div>
      <span className={cn("pill text-[10px] uppercase tracking-wider shrink-0", m.cls)}>
        <Icon className="w-3 h-3" /> {m.label}
      </span>
    </div>
  );
}

function PlanRow({ tag, text }: { tag: string; text: string }) {
  return (
    <div className="flex gap-2.5">
      <span className="w-6 h-6 rounded-md bg-primary/15 text-primary grid place-items-center text-xs font-semibold shrink-0">{tag}</span>
      <p className="text-sm text-foreground/90 leading-relaxed">{text}</p>
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

function prettyStrategy(s?: string) {
  if (!s) return undefined;
  const map: Record<string, string> = {
    flip: "Flip",
    buy_and_hold: "Buy & Hold",
    renda: "Renda",
    valorizacao: "Valorização",
    arbitragem: "Arbitragem",
  };
  return map[s] ?? s;
}
function prettyStatus(s?: string) {
  if (!s) return undefined;
  const map: Record<string, string> = {
    prospeccao: "Prospecção",
    diligencia: "Diligência",
    negociacao: "Negociação",
    fechado: "Fechado",
    descartada: "Descartada",
  };
  return map[s] ?? s;
}
function prettifyField(f: string) {
  return f.replace(/_/g, " ");
}
