import { Badge, C, KPICard, ScreenHero, alpha, mono, withAlpha } from "../components";
import { fmtDate, fmtInteger } from "../utils/formatters.js";

function statusType(status) {
  return status === "live" ? "open" : "warning";
}

function statusAccent(status) {
  return status === "live" ? C.teal : C.amber;
}

function isQualityCheckPassing(status) {
  const normalized = String(status || "").toLowerCase();
  return normalized === "pass" || normalized === "ok" || normalized === "success";
}

function CheckBadge({ status }) {
  const passed = isQualityCheckPassing(status);
  return <Badge label={passed ? "Passou" : "Aten\u00e7\u00e3o"} type={passed ? "success" : "warning"} />;
}

function qualityCheckLabel(check) {
  const key = String(check?.check_id || check?.label || "").toLowerCase();
  const labels = {
    market_fresh_coverage: "Pre\u00e7o de mercado atualizado",
    market_fresh_coverage_pct: "Pre\u00e7o de mercado atualizado",
    provider_critical_count: "Fornecedores cr\u00edticos",
    provider_no_data_count: "Fornecedores sem dados",
    fundamentals_coverage: "Fundamentos dispon\u00edveis",
    fundamentals_coverage_pct: "Fundamentos dispon\u00edveis",
    fundamentals_fresh_coverage: "Fundamentos recentes",
    fundamentals_fresh_coverage_pct: "Fundamentos recentes",
    news_recent_coverage: "Not\u00edcias recentes",
    news_recent_coverage_pct: "Not\u00edcias recentes",
    b3_daily: "Carga B3 di\u00e1ria",
    case_study: "Case study",
  };

  if (labels[key]) return labels[key];
  if (key.includes("market fresh")) return labels.market_fresh_coverage;
  if (key.includes("provider critical")) return labels.provider_critical_count;
  if (key.includes("provider no-data") || key.includes("provider no data")) return labels.provider_no_data_count;
  if (key.includes("fundamentals fresh")) return labels.fundamentals_fresh_coverage;
  if (key.includes("fundamentals coverage")) return labels.fundamentals_coverage;
  if (key.includes("news recent")) return labels.news_recent_coverage;
  return check?.label || check?.check_id || "Check de qualidade";
}

function Section({ title, aside, children }) {
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

function FeedRow({ feed }) {
  const accent = statusAccent(feed.status);

  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderLeft: `3px solid ${accent}`,
        borderRadius: 14,
        display: "grid",
        gridTemplateColumns: "minmax(160px, 0.9fr) minmax(260px, 1.2fr) minmax(180px, 0.8fr)",
        gap: 14,
        padding: "14px 16px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 7, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <strong style={{ color: C.text, fontSize: 13 }}>{feed.label}</strong>
          <Badge label={feed.labelStatus} type={statusType(feed.status)} />
        </div>
        <span style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>{feed.message}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
        <span style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Endpoint oficial
        </span>
        <span style={{ color: C.sky, fontFamily: mono, fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {feed.endpoint}
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
        <span style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Array operacional
        </span>
        <span style={{ color: C.gold, fontFamily: mono, fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {feed.officialArray}
        </span>
      </div>
    </div>
  );
}

function QualityCheck({ check }) {
  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 12,
        padding: "13px 14px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
        <span style={{ color: C.text, fontSize: 12, fontWeight: 700 }}>
          {qualityCheckLabel(check)}
        </span>
        <span style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>
          {check.details || "Sem detalhe adicional registrado."}
        </span>
      </div>
      <CheckBadge status={check.status} />
    </div>
  );
}

function ValidationStep({ label, detail, status = "manual" }) {
  const type = status === "ready" ? "success" : "info";

  return (
    <div
      style={{
        background: withAlpha(C.faint, alpha.strong),
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        padding: "12px 13px",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ color: C.text, fontSize: 12, fontWeight: 700 }}>{label}</span>
        <span style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>{detail}</span>
      </div>
      <Badge label={status === "ready" ? "Pronto" : "Manual"} type={type} />
    </div>
  );
}

function coverageTone(status) {
  if (status === "fresh") return { accent: C.teal, badge: "success", label: "success" };
  if (status === "not_applicable") return { accent: C.sky, badge: "info", label: "n/a" };
  if (status === "disabled") return { accent: C.muted, badge: "neutral", label: "disabled" };
  if (status === "stale") return { accent: C.amber, badge: "warning", label: "stale" };
  return { accent: C.amber, badge: "warning", label: "missing" };
}

function CoverageRow({ name, item }) {
  const tone = coverageTone(item?.status);

  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderLeft: `3px solid ${tone.accent}`,
        borderRadius: 12,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 12,
        padding: "13px 14px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
        <span style={{ color: C.text, fontSize: 12, fontWeight: 700 }}>{name}</span>
        <span style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>
          {item?.label || "Fonte sem estado registrado"}
        </span>
      </div>
      <Badge label={tone.label} type={tone.badge} />
    </div>
  );
}

function WorkflowRow({ name, status, detail }) {
  const passed = status === "success";

  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 12,
        padding: "13px 14px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
        <span style={{ color: C.text, fontFamily: mono, fontSize: 12, fontWeight: 700 }}>{name}</span>
        <span style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>{detail}</span>
      </div>
      <Badge label={passed ? "success" : "partial"} type={passed ? "success" : "warning"} />
    </div>
  );
}

export default function Saude({ data, feedStatus = "live", feedHealth = [] }) {
  const feeds = feedHealth.length > 0 ? feedHealth : [];
  const onlineFeeds = feeds.filter((feed) => feed.status === "live").length;
  const totalFeeds = feeds.length;
  const thesisRows = data?.thesisRows ?? [];
  const activeTheses = data?.activeTheses ?? data?.goLiveTheses ?? [];
  const summaryTestedTheses = Number(data?.scientificSummary?.testedTheses);
  const uniqueTestedTheses = Number.isFinite(summaryTestedTheses)
    ? summaryTestedTheses
    : new Set(
      thesisRows
        .filter((row) => row.statusGroup === "Histórica")
        .map((row) => row.thesisId || row.id)
        .filter(Boolean),
    ).size;
  const checks = data?.dataQualityGate?.checks ?? [];
  const coverage = data?.coverage ?? {};
  const coverageRows = [
    ["Mercado", coverage.market],
    ["Historico", coverage.history],
    ["Noticias", coverage.news],
    ["Fundamentos", coverage.fundamentals],
    ["Macro", coverage.macro],
  ].filter(([, item]) => item);
  const workflowRows = [
    {
      name: "microtrades-data-refresh",
      status: coverage.market?.status === "fresh" ? "success" : "partial",
      detail: coverage.market?.label || "Atualiza preco e candles do monitor atual.",
    },
    {
      name: "data-context-refresh",
      status: coverage.news?.status === "fresh" || coverage.fundamentals?.status === "fresh" ? "success" : "partial",
      detail: `${coverage.news?.label || "Noticias sem cobertura recente"} - ${coverage.fundamentals?.label || "Fundamentos sem cobertura recente"}`,
    },
  ];
  const lastUpdatedAt = data?.scientificSummary?.lastUpdatedAt;
  const hasFallback = feedStatus !== "live" || feeds.some((feed) => feed.status !== "live");
  const qualityAttentionCount = checks.filter((check) => !isQualityCheckPassing(check.status)).length;
  const hasQualityAttention = qualityAttentionCount > 0;
  const statusColor = hasFallback ? C.amber : C.teal;
  const executiveSummary = hasFallback
    ? "Feed temporariamente indispon\u00edvel. Mantendo o \u00faltimo retrato v\u00e1lido do laborat\u00f3rio."
    : hasQualityAttention
      ? `Feeds ${onlineFeeds}/${totalFeeds || 0} online \u00b7 ${qualityAttentionCount} alertas de qualidade exigem confer\u00eancia antes de ampliar risco.`
      : "Todos os feeds principais responderam. A hip\u00f3tese operacional do dia pode ser conferida com dados reais.";

  return (
    <main
      style={{
        background: C.bg,
        color: C.text,
        display: "flex",
        flexDirection: "column",
        fontFamily: "Sora, system-ui, sans-serif",
        gap: 24,
        minHeight: 640,
        padding: "24px 28px 40px",
      }}
    >
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>
            {"Prontid\u00e3o di\u00e1ria dos feeds, valida\u00e7\u00f5es locais e qualidade dos dados do motor Halley."}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <Badge label={hasFallback ? "Fallback ativo" : "API real"} type={hasFallback ? "warning" : "open"} />
          {!hasFallback && hasQualityAttention && <Badge label={"Qualidade com aten\u00e7\u00e3o"} type="warning" />}
        </div>
      </header>

      <ScreenHero
        screen="saude"
        state="reporting"
        accent={statusColor}
        imageBorderColor={C.gold + "45"}
        message={"O laborat\u00f3rio revisou os feeds. Quando a API falha, o retrato anterior permanece vis\u00edvel e o motor registra o estado para confer\u00eancia."}
        insights={[
          { label: "Feeds", value: `${onlineFeeds}/${totalFeeds || 0} online`, color: hasFallback ? C.amber : C.teal },
          { label: "Teses", value: `${fmtInteger(uniqueTestedTheses)} testadas únicas`, color: C.sky },
          { label: "Atenção", value: hasQualityAttention ? "Há checks para conferir." : "Sem bloqueio crítico.", color: hasQualityAttention ? C.amber : C.green },
        ]}
      />

      <section
        style={{
          background: hasFallback ? withAlpha(C.amber, alpha.glow) : withAlpha(hasQualityAttention ? C.amber : C.teal, alpha.glow),
          border: `1px solid ${hasFallback || hasQualityAttention ? withAlpha(C.amber, alpha.border) : withAlpha(C.teal, alpha.border)}`,
          borderRadius: 12,
          color: hasFallback || hasQualityAttention ? C.amber : C.teal,
          fontSize: 12,
          lineHeight: 1.6,
          padding: 14,
        }}
      >
        {executiveSummary}
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
        <KPICard label="Feeds online" value={`${onlineFeeds}/${totalFeeds || 0}`} sub="endpoints oficiais" accent={hasFallback ? C.amber : C.teal} valueColor={hasFallback ? C.amber : C.teal} />
        <KPICard label={"Teses testadas \u00fanicas"} value={fmtInteger(uniqueTestedTheses)} sub="validação deduplicada" accent={C.sky} valueColor={C.text} />
        <KPICard label="Go-live" value={fmtInteger(activeTheses.length)} sub={"coletando evid\u00eancia"} accent={C.purple} valueColor={C.text} />
        <KPICard label={"\u00daltima atualiza\u00e7\u00e3o"} value={fmtDate(lastUpdatedAt)} sub="dashboard summary" accent={C.gold} valueColor={C.text} valueFontSize={18} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 0.8fr)", gap: 18 }}>
        <Section title="Cobertura por fonte" aside="preco, historico, contexto e macro">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {coverageRows.map(([name, item]) => <CoverageRow key={name} name={name} item={item} />)}
          </div>
        </Section>

        <Section title="Rotina de atualizacao" aside="GitHub Actions">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {workflowRows.map((workflow) => <WorkflowRow key={workflow.name} {...workflow} />)}
          </div>
        </Section>
      </div>

      <Section title="Feeds oficiais" aside="API, fallback e arrays de origem">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {feeds.map((feed) => <FeedRow key={feed.key} feed={feed} />)}
        </div>
      </Section>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 0.8fr)", gap: 18 }}>
        <Section title="Data quality gate" aside="bronze, silver, load e case study">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {checks.length > 0 ? checks.map((check) => (
              <QualityCheck key={check.check_id || check.label} check={check} />
            )) : (
              <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, color: C.muted, fontSize: 12, lineHeight: 1.6, padding: 14 }}>
                {"Nenhum check retornado pela API. O plano contempla isso: usar o retrato v\u00e1lido e registrar a aus\u00eancia."}
              </div>
            )}
          </div>
        </Section>

        <Section title={"Valida\u00e7\u00e3o local"} aside={"um comando para o ritual di\u00e1rio"}>
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, display: "flex", flexDirection: "column", gap: 12, padding: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {"Comando \u00fanico"}
              </span>
              <code style={{ color: C.gold, fontFamily: mono, fontSize: 13 }}>npm run validate:daily</code>
            </div>
            <ValidationStep label="Testes" detail={"Executa a su\u00edte Vitest antes de qualquer leitura visual."} status="ready" />
            <ValidationStep label="Build" detail={"Confirma que Vite fecha o pacote de produ\u00e7\u00e3o."} status="ready" />
            <ValidationStep label="Screenshots" detail={"Registra evid\u00eancia visual na pasta Valida\u00e7\u00e3o Telas."} />
          </div>
        </Section>
      </div>
    </main>
  );
}
