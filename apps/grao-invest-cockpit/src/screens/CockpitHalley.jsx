import {
  C,
  Badge,
  DataTrustSeal,
  FrontCard,
  KPICard,
  LearningLoopCard,
  PatrickJane,
  ThesisCard,
  withAlpha,
} from "../components";
import { dataTrustForScreen } from "../data/dataTrust.js";
import { fmtInteger, fmtPct } from "../utils/formatters.js";

function pctColor(value) {
  return value >= 0 ? C.teal : C.coral;
}

function Section({ title, children, aside }) {
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
        <h2 style={{ color: C.text, fontSize: 15, fontWeight: 700, margin: 0 }}>{title}</h2>
        {aside && <span style={{ color: C.muted, fontSize: 11 }}>{aside}</span>}
      </div>
      {children}
    </section>
  );
}

function EmptyTheses() {
  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        color: C.muted,
        fontSize: 12,
        lineHeight: 1.6,
        padding: 18,
      }}
    >
      Nenhuma hipótese em go-live neste momento. O laboratório continua testando o histórico; uma nova tese só entra em campo quando houver evidência suficiente.
    </div>
  );
}

function FrozenMonitorNotice({ trust }) {
  if (!trust?.isFrozen) return null;

  return (
    <div
      role="status"
      style={{
        alignItems: "flex-start",
        background: withAlpha(C.amber, 0.1),
        border: `1px solid ${withAlpha(C.amber, 0.32)}`,
        borderRadius: 12,
        color: C.text,
        display: "grid",
        gap: 4,
        padding: "12px 14px",
      }}
    >
      <strong style={{ color: C.amber, fontSize: 12 }}>{trust.label}</strong>
      <span style={{ color: C.muted, fontSize: 12, lineHeight: 1.55 }}>
        {trust.message}
      </span>
    </div>
  );
}

function coverageTone(status) {
  if (status === "fresh") return { color: C.teal, badge: "success", label: "Atualizado" };
  if (status === "not_applicable") return { color: C.sky, badge: "info", label: "Nao aplicavel" };
  if (status === "disabled") return { color: C.muted, badge: "neutral", label: "Fora do MVP" };
  if (status === "stale") return { color: C.amber, badge: "warning", label: "Desatualizado" };
  return { color: C.amber, badge: "warning", label: "Sem fonte" };
}

function CoverageStrip({ coverage }) {
  if (!coverage) return null;

  const items = [
    ["Mercado", coverage.market],
    ["Historico", coverage.history],
    ["Noticias", coverage.news],
    ["Fundamentos", coverage.fundamentals],
    ["Macro", coverage.macro],
  ].filter(([, item]) => item);

  return (
    <section
      aria-label="Cobertura de dados"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        padding: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h2 style={{ color: C.text, fontSize: 15, fontWeight: 700, margin: 0 }}>Cobertura de dados</h2>
        <span style={{ color: C.muted, fontSize: 11 }}>fonte usada pelo Metodo Grao</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
        {items.map(([name, item]) => {
          const tone = coverageTone(item.status);
          return (
            <div
              key={name}
              style={{
                background: C.panel,
                border: `1px solid ${C.line}`,
                borderLeft: `3px solid ${tone.color}`,
                borderRadius: 10,
                display: "flex",
                flexDirection: "column",
                gap: 7,
                minWidth: 0,
                padding: "10px 11px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <strong style={{ color: C.text, fontSize: 11 }}>{name}</strong>
                <Badge label={tone.label} type={tone.badge} />
              </div>
              <span style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ScientificScore({ summary, fiveCol, expectancyColor, isNarrow }) {
  const goLiveAssetCount = summary.goLiveAssetCount ?? summary.goLiveCount ?? 0;
  const learningCountLabel = summary.learningCountLabel || "aprendizados aplicados";
  const monitorFrozen = Boolean(summary.monitorFrozen);
  const goLiveLabel = summary.goLiveLabel || "planos em go-live";
  const goLiveKpiLabel = summary.goLiveKpiLabel || "Planos em go-live";
  const monitorSubLabel = monitorFrozen
    ? `${fmtInteger(goLiveAssetCount)} ativos no retrato congelado`
    : `${fmtInteger(goLiveAssetCount)} ativos cobertos`;
  const patrickMessage = monitorFrozen
    ? "O Halley marcou este retrato como estudo, não como operação viva. O feed precisa ser atualizado antes de novas decisões."
    : "O Halley revisou o laboratório. O histórico indica onde o método tem força. O plano foi seguido.";

  return (
    <section
      style={{
        backgroundColor: C.card,
        backgroundImage: `linear-gradient(135deg, ${C.card} 0%, ${C.faint} 100%)`,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        padding: 18,
        minHeight: isNarrow ? 0 : 330,
        position: "relative",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: isNarrow ? 140 : 300,
          height: isNarrow ? 120 : 180,
          background: `radial-gradient(ellipse at 90% 60%, ${C.gold}14, transparent 55%)`,
          pointerEvents: "none",
        }}
      />
      <PatrickJane
        hero={!isNarrow}
        screen="dashboard"
        state="reporting"
        imageHeight={isNarrow ? 96 : 168}
        imageWidth={isNarrow ? "auto" : "100%"}
        imageBorderColor={C.gold + "45"}
        imageStyle={isNarrow ? { height: 96, minHeight: 96, maxHeight: 96 } : { height: 168, minHeight: 168, maxHeight: 168 }}
        style={{
          gap: 16,
          position: "relative",
          zIndex: 2,
        }}
        contentStyle={{ maxWidth: 820 }}
        message={patrickMessage}
        insights={[
          { label: "Agora", value: `${fmtInteger(summary.goLiveCount)} ${goLiveLabel}`, color: C.amber },
          { label: "Cobertura", value: monitorFrozen ? `${fmtInteger(goLiveAssetCount)} ativos no retrato` : `${fmtInteger(goLiveAssetCount)} ativos cobertos`, color: C.sky },
          { label: "Método", value: `${fmtInteger(summary.appliedLearningsCount)} ${learningCountLabel}`, color: C.purple },
        ]}
      />
      <div style={{ borderTop: `1px solid ${C.line}`, position: "relative", zIndex: 2 }} />
      <div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600, position: "relative", zIndex: 2, marginTop: -4 }}>
        Placar científico · Cal. 18
      </div>
      <div style={{ display: "grid", gridTemplateColumns: fiveCol, gap: 12, position: "relative", zIndex: 2 }}>
        <KPICard label="Teses testadas" value={fmtInteger(summary.testedTheses)} sub="laboratório histórico" accent={C.sky} valueColor={C.text} />
        <KPICard label="Validação histórica" value={fmtPct(summary.validatedPct)} sub="não é garantia futura" accent={C.teal} valueColor={C.teal} />
        <KPICard label="Expectância líquida" value={fmtPct(summary.expectancyPct)} sub="ganho/perda médio por hipótese" accent={C.gold} valueColor={expectancyColor} />
        <KPICard label={goLiveKpiLabel} value={fmtInteger(summary.goLiveCount)} sub={monitorSubLabel} accent={C.amber} valueColor={C.text} />
        <KPICard label="Aprendizados" value={fmtInteger(summary.appliedLearningsCount)} sub={learningCountLabel} accent={C.purple} valueColor={C.text} />
      </div>
    </section>
  );
}

export function CockpitHalley({ data }) {
  const isNarrow = typeof window !== "undefined" && window.innerWidth < 760;
  const threeCol = isNarrow ? "1fr" : "1fr 1fr 1fr";
  const fiveCol = isNarrow ? "1fr" : "repeat(5, minmax(0, 1fr))";
  const twoCol = isNarrow ? "1fr" : "1fr 1fr";

  const summary = data?.scientificSummary ?? {};
  const fronts = data?.fronts ?? [];
  const theses = data?.activeTheses ?? data?.goLiveTheses ?? [];
  const learningLoops = data?.learningLoops ?? [];
  const expectancyColor = pctColor(summary.expectancyPct ?? 0);
  const dataTrust = data?.dataTrust?.dashboard ?? dataTrustForScreen("dashboard", data);
  const monitorTrust = data?.monitorTrust ?? {};
  const monitorFrozen = Boolean(summary.monitorFrozen || monitorTrust.isFrozen);
  const thesisSectionTitle = monitorFrozen ? "Último monitor congelado" : "Hipóteses em go-live";
  const thesisSectionAside = monitorFrozen
    ? "Dados sem frescor; retrato para estudo"
    : "Clique no card para abrir ou recolher os detalhes";
  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>Laboratório científico de teses — motor Halley</p>
        </div>
        <DataTrustSeal screen="dashboard" trust={dataTrust} />
      </header>

      <FrozenMonitorNotice trust={monitorTrust} />
      <CoverageStrip coverage={data?.coverage} />

      <ScientificScore summary={summary} fiveCol={fiveCol} expectancyColor={expectancyColor} isNarrow={isNarrow} />

      <Section title="Frentes separadas" aside="B3, Cripto e Imóveis">
        <div style={{ display: "grid", gridTemplateColumns: threeCol, gap: 14 }}>
          {fronts.map((front) => <FrontCard key={front.id} front={front} />)}
        </div>
      </Section>

      <Section title={thesisSectionTitle} aside={thesisSectionAside}>
        {theses.length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: threeCol, gap: 14 }}>
            {theses.map((thesis) => <ThesisCard key={`${thesis.front}-${thesis.id}`} thesis={thesis} />)}
          </div>
        ) : <EmptyTheses />}
      </Section>

      <Section title="Aprendizado Halley" aside="Dor, remédio e impacto esperado">
        <div style={{ display: "grid", gridTemplateColumns: twoCol, gap: 14 }}>
          {learningLoops.map((loop, index) => {
            const lastOdd = !isNarrow && learningLoops.length % 2 === 1 && index === learningLoops.length - 1;
            return (
              <div
                key={`${loop.pain}-${index}`}
                data-testid={`dashboard-learning-${index}`}
                style={{ gridColumn: lastOdd ? "1 / -1" : undefined, minWidth: 0, width: "100%" }}
              >
                <LearningLoopCard loop={loop} />
              </div>
            );
          })}
        </div>
      </Section>
    </main>
  );
}

export default CockpitHalley;
