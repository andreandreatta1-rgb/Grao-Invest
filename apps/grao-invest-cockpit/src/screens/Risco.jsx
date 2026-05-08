import { Badge, C, KPICard, ScreenHero, alpha, mono, withAlpha } from "../components";

const riskAlerts = [
  { title: "Concentração em MGLU3", description: "2 teses no mesmo ativo — limite é 1", color: C.coral, severity: "CRÍTICO", type: "danger", icon: "●" },
  { title: "Exposição próxima do limite", description: "R$ 285K de R$ 300K — 95%", color: C.amber, severity: "ALERTA", type: "warning", icon: "●" },
  { title: "PETR4 — alerta de stop", description: "Momento −3,88% — stop em R$ 36,88", color: C.amber, severity: "ALERTA", type: "warning", icon: "⚠" },
];

const frontExposure = [
  { label: "B3", value: "R$ 155K", pct: 52, color: C.sky },
  { label: "Cripto", value: "R$ 95K", pct: 31, color: C.amber },
  { label: "Imóveis", value: "R$ 35K", pct: 12, color: C.purple },
];

function ProgressBar({ pct, color, height = 5 }) {
  return (
    <div style={{ background: C.faint, borderRadius: 99, height, overflow: "hidden" }}>
      <div style={{ width: `${Math.min(100, Math.max(0, pct))}%`, height: "100%", background: color, borderRadius: 99, transition: "width 0.7s cubic-bezier(.4,0,.2,1)" }} />
    </div>
  );
}

function RiskAlertCard({ alert }) {
  return (
    <article
      style={{
        background: alert.color + "05",
        border: `1px solid ${withAlpha(alert.color, alpha.border)}`,
        borderLeft: `3px solid ${alert.color}`,
        borderRadius: 12,
        padding: "12px 14px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
        <span style={{ color: alert.color, fontSize: 13, flexShrink: 0 }}>{alert.icon}</span>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: alert.color, fontSize: 12, fontWeight: 700, marginBottom: 2 }}>{alert.title}</div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>{alert.description}</div>
        </div>
      </div>
      <Badge label={alert.severity} type={alert.type} />
    </article>
  );
}

export default function Risco({ data }) {
  const risk = data?.risk ?? { exposurePct: 95, limitPct: 100, mainAsset: "MGLU3", stopRespectPct: 100, alerts: [] };
  const goLiveCount = data?.scientificSummary?.goLiveCount ?? data?.activeTheses?.length ?? 3;
  const operationalExposurePct = 95;

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>Disciplina de exposição, concentração e respeito aos stops.</p>

      <ScreenHero
        screen="risco"
        state="alerting"
        accent={C.coral}
        imageBorderColor="rgba(255, 94, 94, 0.3)"
        imageStyle={{ borderRadius: 12 }}
        message={`A exposição está em ${operationalExposurePct}% do limite operacional. O plano contempla stop definido e nenhuma ampliação de risco enquanto o ciclo não confirmar.`}
        insights={[
          { label: "Regra central", value: "Não ampliar risco sem confirmação.", color: C.coral },
          { label: "Limite", value: "R$ 285K de R$ 300K em uso.", color: C.amber },
          { label: "Próxima ação", value: "Respeitar stops e reduzir concentração.", color: C.green },
        ]}
      />

      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <KPICard label="Exposição total" value="R$ 285K" sub="limite: R$ 300K · 95%" accent={C.amber} valueColor={C.amber} />
        <KPICard label="Maior concentração" value="MGLU3" sub="2 teses abertas" accent={C.coral} valueColor={C.coral} />
        <KPICard label="Stops respeitados" value={`${Number(risk.stopRespectPct || 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`} sub="último mês" accent={C.green} valueColor={C.green} />
        <KPICard label="Teses em go-live" value={Number(goLiveCount || 3).toLocaleString("pt-BR")} sub="dentro do limite de 5" accent={C.teal} valueColor={C.teal} />
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.15fr) minmax(320px, .85fr)", gap: 14, alignItems: "start" }}>
        <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", top: 0, right: 0, width: 220, height: 180, background: `radial-gradient(ellipse at 90% 30%, ${C.coral}14, transparent 62%)`, pointerEvents: "none" }} />
          <div style={{ position: "relative", zIndex: 2 }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 4 }}>A corda bamba</div>
              <div style={{ color: C.muted, fontSize: 11, marginBottom: 14 }}>Cada alerta é um passo torto · o abismo é real</div>
              <div style={{ color: C.text, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Alertas de risco ativos</div>
              <div style={{ display: "grid", gap: 10 }}>
                {riskAlerts.map((alert) => <RiskAlertCard key={alert.title} alert={alert} />)}
              </div>
            </div>
          </div>
        </section>

        <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18 }}>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Exposição por frente</div>
            <div style={{ color: C.muted, fontSize: 11, marginBottom: 14 }}>Total: R$ 285K / limite R$ 300K</div>
            {frontExposure.map((front) => (
              <div key={front.label} style={{ marginBottom: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ color: C.text, fontSize: 12, fontWeight: 600 }}>{front.label}</span>
                  <span style={{ color: front.color, fontSize: 12, fontFamily: mono }}>{front.value}</span>
                </div>
                <ProgressBar pct={front.pct} color={front.color} />
                <div style={{ color: C.muted, fontSize: 9, textAlign: "right", marginTop: 3 }}>{front.pct}% do total</div>
              </div>
            ))}
          </div>

          <div style={{ background: C.amber + "08", border: `1px solid ${C.amber}22`, borderRadius: 14, padding: 16 }}>
            <div style={{ color: C.amber, fontSize: 10, fontWeight: 700, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Limite total</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
              <span style={{ color: C.text, fontSize: 20, fontWeight: 700, fontFamily: mono }}>R$ 285K / R$ 300K</span>
              <span style={{ color: C.amber, fontSize: 12, fontFamily: mono, fontWeight: 700 }}>95%</span>
            </div>
            <ProgressBar pct={95} color={C.amber} height={6} />
            <div style={{ color: C.muted, fontSize: 10, marginTop: 7 }}>5% restante antes do limite operacional.</div>
          </div>
        </section>
      </div>
    </main>
  );
}
