(() => {
  if (!window.React || !window.ReactDOM) {
    return;
  }

  const { useState, useEffect, useMemo } = window.React;

const C = {
  bg: "#070b14", panel: "#0c1120", card: "#101828",
  border: "#1a2540", hover: "#141f35", line: "#1e2d4a",
  gold: "#c8a444", goldLight: "#e8c870", goldDim: "#8a6e2c",
  teal: "#00c896", tealDim: "#006b50",
  sky: "#3b9eff", skyDim: "#1a4d8c",
  coral: "#ff5e5e", coralDim: "#7a2020",
  amber: "#f5a623", amberDim: "#7a4e05",
  green: "#22c55e", greenDim: "#14532d",
  purple: "#a78bfa",
  text: "#e2eaf8", muted: "#5a7090", dim: "#2e4060",
};

const mono = "'JetBrains Mono', 'Fira Code', monospace";

const fmt = (v, decimals = 2) => {
  const n = parseFloat(v);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(decimals)}%`;
};

const teseCountLabel = (n) => `${n} ${n === 1 ? "tese" : "teses"}`;

const avg = (arr) => {
  if (!arr.length) return null;
  const total = arr.reduce((acc, n) => acc + n, 0);
  return total / arr.length;
};

const pct = (part, whole) => {
  if (!whole) return 0;
  return Math.round((part / whole) * 100);
};

const semaforoPorPercentual = (valor, verde = 70, amarelo = 45) => {
  if (valor >= verde) return { label: "Verde", type: "success", color: C.green };
  if (valor >= amarelo) return { label: "Amarelo", type: "warning", color: C.amber };
  return { label: "Vermelho", type: "danger", color: C.coral };
};

const semaforoAmostra = (fechadas) => {
  if (fechadas >= 5) return { label: "Verde", type: "success", color: C.green };
  if (fechadas >= 2) return { label: "Amarelo", type: "warning", color: C.amber };
  return { label: "Vermelho", type: "danger", color: C.coral };
};

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatPctLabel = (value) => {
  const n = toNumber(value, 0);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2).replace(".", ",")}%`;
};

const formatMoneyLabel = (value) => {
  const n = toNumber(value, NaN);
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(2).replace(".", ",");
};

const formatCurrencyLabel = (value) => {
  const n = toNumber(value, NaN);
  if (!Number.isFinite(n)) return "-";
  return `R$ ${n.toFixed(2).replace(".", ",")}`;
};

const formatDateLabel = (value) => {
  const raw = String(value || "");
  if (raw.length < 10) return "-";
  return `${raw.slice(8, 10)}/${raw.slice(5, 7)}/${raw.slice(0, 4)}`;
};

const compactText = (text, max = 150) => {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  if (!clean) return "-";
  return clean.length > max ? `${clean.slice(0, max - 3)}...` : clean;
};

function useCompactLayout() {
  const [compact, setCompact] = useState(() => (typeof window !== "undefined" ? window.innerWidth < 760 : false));
  useEffect(() => {
    const onResize = () => setCompact(window.innerWidth < 760);
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return compact;
}

const isOpenStatus = (status) => {
  const normalized = String(status || "").toLowerCase();
  return normalized.includes("aberta") || normalized.includes("aberto") || normalized.includes("monitor");
};

const classifyPhase = (row, kickoffDate) => {
  const explicitPhase = String(row?.phase || row?.source_phase || "").toLowerCase();
  if (explicitPhase.includes("histor")) return "historical";
  if (explicitPhase.includes("pos") || explicitPhase.includes("go_live") || explicitPhase.includes("go-live") || explicitPhase.includes("current")) {
    return "current";
  }
  const thesisDateRaw = String(
    row?.thesis_raised_at || row?.entry_time || row?.reference_day || row?.suggested_entry_time || "",
  );
  const thesisDay = thesisDateRaw.length >= 10 ? thesisDateRaw.slice(0, 10) : "";
  if (thesisDay && kickoffDate && thesisDay < kickoffDate) return "historical";
  return "current";
};

const inferMelhoriasAplicadas = (row) => {
  const outcome = String(row?.outcome || "").toLowerCase();
  const reason = String(row?.thesis_reason || "").toLowerCase();
  const learning = String(row?.learning_note || "").toLowerCase();
  const tags = [];
  if (outcome.includes("tempo")) tags.push("tempo_da_tese");
  if (learning.includes("parcial")) tags.push("saida_parcial");
  if (outcome.includes("stop") || learning.includes("stop")) tags.push("stop_antecipado");
  if (reason.includes("faixa") || learning.includes("faixa")) tags.push("range_break_rapido");
  if (reason.includes("volume") || learning.includes("volume")) tags.push("confirmacao_volume");
  if (learning.includes("protecao curta") || learning.includes("prote\u00e7\u00e3o curta")) tags.push("protecao_curta");
  if (learning.includes("tempo maximo") || learning.includes("tempo m\u00e1ximo")) tags.push("tempo_maximo");
  if (learning.includes("alvo")) tags.push("calibragem_alvo");
  return [...new Set(tags)];
};

const operationDirection = (row) => {
  const plan = String(row?.operation_plan || "").toLowerCase();
  if (plan.startsWith("compra")) return "Alta";
  if (plan.startsWith("venda")) return "Baixa";
  return "Neutra";
};

const extractExitLevels = (exitRule) => {
  const text = String(exitRule || "");
  const matches = [...text.matchAll(/R\\$\\s*([0-9]+(?:[\\.,][0-9]+)?)/g)];
  const values = matches
    .map((m) => (m[1] || "").replace(",", "."))
    .map((v) => Number(v))
    .filter((n) => Number.isFinite(n));
  return {
    gain: values.length > 0 ? values[0].toFixed(2).replace(".", ",") : "-",
    stop: values.length > 1 ? values[1].toFixed(2).replace(".", ",") : "-",
  };
};

const mapOperationRowToTable = (row, index) => {
  const expected = toNumber(row?.expected_result_pct, 0);
  const result = toNumber(row?.moment_result_pct, 0);
  const entry = formatMoneyLabel(row?.entry_price_brl);
  const duration = Number.isFinite(toNumber(row?.duration_days, NaN)) ? Math.round(toNumber(row?.duration_days, 0)) : 0;
  const direction = operationDirection(row);
  const melhoriasAplicadas = inferMelhoriasAplicadas(row);
  const lowerSignals = `${String(row?.outcome || "")} ${String(row?.thesis_reason || "")} ${String(row?.learning_note || "")}`.toLowerCase();
  const sintomaDetectado = melhoriasAplicadas.length > 0 || /stop|tempo|romp|alerta|quebra/.test(lowerSignals);
  const sintomaConfirmado = String(row?.status || "").toLowerCase().includes("fechad") && result >= 0;
  return {
    id: toNumber(row?.thesis_number, index + 1),
    ativo: String(row?.action || "n/d"),
    direcao: direction,
    esperado: formatPctLabel(expected),
    estrutura: String(row?.structured_operation || "-"),
    entrada: entry,
    saida: String(row?.exit_rule || "-"),
    desfecho: String(row?.outcome || "-"),
    dias: duration,
    status: String(row?.status || "Fechada"),
    resultado: result,
    porQue: String(row?.thesis_reason || "Sem detalhamento disponivel para esta tese."),
    aprendizado: String(row?.learning_note || "Sem aprendizado registrado ainda."),
    melhoriasAplicadas,
    sintomaDetectado,
    sintomaConfirmado,
    origem: row,
  };
};

function Badge({ label, type = "neutral" }) {
  const styles = {
    open:    { bg: C.teal + "20",  color: C.teal,  border: C.teal + "40" },
    closed:  { bg: C.muted + "20", color: C.muted, border: C.muted + "40" },
    warning: { bg: C.amber + "20", color: C.amber, border: C.amber + "40" },
    success: { bg: C.green + "20", color: C.green, border: C.green + "40" },
    danger:  { bg: C.coral + "20", color: C.coral, border: C.coral + "40" },
    neutral: { bg: C.dim + "60",   color: C.muted, border: C.dim },
    high:    { bg: C.gold + "20",  color: C.gold,  border: C.gold + "40" },
    bull:    { bg: C.teal + "20",  color: C.teal,  border: C.teal + "40" },
    bear:    { bg: C.coral + "20", color: C.coral, border: C.coral + "40" },
    info:    { bg: C.sky + "20",   color: C.sky,   border: C.sky + "40" },
  };
  const s = styles[type] || styles.neutral;
  return (
    <span style={{
      background: s.bg, color: s.color,
      border: `1px solid ${s.border}`,
      fontSize: 10, fontWeight: 700,
      padding: "2px 8px", borderRadius: 6,
      letterSpacing: "0.04em", textTransform: "uppercase",
      fontFamily: mono, whiteSpace: "nowrap",
    }}>{label}</span>
  );
}

function KPICard({ label, value, sub, valueColor, accent, icon }) {
  return (
    <div style={{
      background: C.card,
      border: `1px solid ${C.border}`,
      borderTop: `2px solid ${accent || C.border}`,
      borderRadius: 14,
      padding: "18px 20px",
      display: "flex", flexDirection: "column", gap: 6,
      position: "relative", overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", top: 0, right: 0,
        width: 80, height: 80,
        background: `radial-gradient(circle at top right, ${(accent || C.gold) + "18"}, transparent 70%)`,
        borderRadius: "0 14px 0 0",
        pointerEvents: "none",
      }} />
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
        {icon && <span style={{ fontSize: 13 }}>{icon}</span>}
        <span style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</span>
      </div>
      <span style={{ color: valueColor || C.text, fontSize: 26, fontWeight: 700, fontFamily: mono, letterSpacing: "-0.02em", lineHeight: 1 }}>{value}</span>
      {sub && <span style={{ color: C.muted, fontSize: 11, marginTop: 2 }}>{sub}</span>}
    </div>
  );
}

function ThesisCard({ thesis }) {
  const isWarning = thesis.desfecho?.toLowerCase().includes("stop");
  const statusType = thesis.status === "Aberta" ? (isWarning ? "warning" : "open") : "closed";
  const momentumColor = thesis.momentum >= 0 ? C.teal : C.coral;
  const expectedColor = thesis.expected >= 0 ? C.teal : C.coral;
  const dirType = thesis.direcao === "Alta" ? "bull" : thesis.direcao === "Baixa" ? "bear" : "neutral";

  return (
    <div style={{
      background: C.card,
      border: `1px solid ${isWarning ? C.amber + "55" : C.border}`,
      borderLeft: `3px solid ${isWarning ? C.amber : C.teal}`,
      borderRadius: 12,
      padding: 16,
      display: "flex", flexDirection: "column", gap: 10,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: C.muted, fontSize: 10, fontFamily: mono }}>#{thesis.id}</span>
          <span style={{ color: C.text, fontSize: 15, fontWeight: 700 }}>{thesis.ativo}</span>
          <Badge label={thesis.direcao} type={dirType} />
        </div>
        <Badge label={thesis.desfecho || thesis.status} type={statusType} />
      </div>

      {/* Metrics row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "Entrada", value: `R$ ${thesis.entrada}`, color: C.text },
          { label: "Esperado", value: fmt(thesis.expected), color: expectedColor },
          { label: "Momento", value: fmt(thesis.momentum), color: momentumColor },
        ].map((m) => (
          <div key={m.label} style={{ background: C.panel, borderRadius: 8, padding: "8px 10px" }}>
            <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>{m.label}</div>
            <div style={{ color: m.color, fontSize: 13, fontWeight: 700, fontFamily: mono }}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Structure */}
      <div style={{ background: C.panel, borderRadius: 8, padding: "8px 12px" }}>
        <span style={{ color: C.muted, fontSize: 10, marginRight: 8 }}>Estrutura</span>
        <span style={{ color: C.sky, fontSize: 12, fontWeight: 500 }}>{thesis.estrutura}</span>
      </div>

      {/* Levels */}
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <span style={{ color: C.muted, fontSize: 10 }}>Saida</span>
        <span style={{ color: C.green, fontSize: 11, fontFamily: mono, fontWeight: 600 }}>^ R$ {thesis.saiGanho}</span>
        <div style={{ width: 1, height: 12, background: C.border }} />
        <span style={{ color: C.coral, fontSize: 11, fontFamily: mono, fontWeight: 600 }}>v R$ {thesis.saiStop}</span>
        {thesis.inicio && <span style={{ color: C.muted, fontSize: 10, marginLeft: "auto" }}>go-live {thesis.inicio}</span>}
      </div>
    </div>
  );
}

function ExecutiveMethodStrip({ executiveData, resumoKpis, compact }) {
  const last7 = executiveData?.evolution?.last_7_days || {};
  const lastDay = executiveData?.evolution?.last_day || {};
  const kpis = executiveData?.kpis || {};
  const last7Count = toNumber(last7.sample_count, 0);
  const lastDayCount = toNumber(lastDay.sample_count, 0);
  const cards = [
    {
      step: "01",
      label: "Objetivo",
      value: "Aprender antes de alocar",
      sub: executiveData?.objective || "Descobrir teses, testar operacoes e melhorar as proximas decisoes.",
      tone: C.sky,
    },
    {
      step: "02",
      label: "Como fazemos",
      value: "Mercado + fundamento + contexto",
      sub: "Leitura tecnica, suporte historico, dados fundamentais e noticias viram uma tese testavel.",
      tone: C.gold,
    },
    {
      step: "03",
      label: "Ultimos 7 dias",
      value: last7Count ? `${last7Count} exercicios` : `${resumoKpis.totalTested} avaliadas`,
      sub: last7Count
        ? `${toNumber(last7.success_rate_pct, 0).toFixed(1).replace(".", ",")}% sucesso e ${toNumber(last7.discovery_rate_pct, 0).toFixed(1).replace(".", ",")}% descoberta.`
        : `${resumoKpis.successRatePct.toFixed(1).replace(".", ",")}% sucesso acumulado.`,
      tone: C.teal,
    },
    {
      step: "04",
      label: "Ciclo atual",
      value: toNumber(kpis.total_iterations, 0) ? `${toNumber(kpis.total_iterations, 0)} iteracoes` : "Pos-morte ativo",
      sub: lastDayCount
        ? `Ultimo dia: ${lastDayCount} casos, ${toNumber(lastDay.success_rate_pct, 0).toFixed(1).replace(".", ",")}% sucesso.`
        : "Sem nova amostra fechada no ultimo dia; aprendizado segue em shadow antes de virar regra ativa.",
      tone: C.purple,
    },
  ];

  return (
    <section style={{
      display: "grid",
      gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(220px, 1fr))",
      gap: 12,
    }}>
      {cards.map((card) => (
        <div key={card.step} style={{
          background: `linear-gradient(145deg, ${C.card}, #090f1c)`,
          border: `1px solid ${C.border}`,
          borderRadius: 14,
          padding: "14px 15px",
          minHeight: 122,
          position: "relative",
          overflow: "hidden",
        }}>
          <div style={{
            position: "absolute",
            right: 12,
            top: 8,
            color: card.tone + "28",
            fontSize: 36,
            fontWeight: 900,
            fontFamily: mono,
            lineHeight: 1,
          }}>{card.step}</div>
          <div style={{ color: card.tone, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 800 }}>
            {card.label}
          </div>
          <div style={{ color: C.text, fontSize: 16, fontWeight: 850, lineHeight: 1.2, marginTop: 9, maxWidth: 250 }}>
            {card.value}
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.35, marginTop: 8, maxWidth: 300 }}>
            {card.sub}
          </div>
        </div>
      ))}
    </section>
  );
}

function LearningJourney({ evolution, compact }) {
  const cases = Array.isArray(evolution?.cases) ? evolution.cases.slice(0, 3) : [];
  const fallbackCases = [
    {
      label: "Tese A",
      instrument: "BPAC11",
      strategy: "Operacao de alta",
      entry_date: "2019-09-30",
      entry_price: 58.55,
      target_price: 62.65,
      stop_price: 56.09,
      exit_date: "2019-10-10",
      exit_price: 53.70,
      realized_financial_pct: -2.2,
      expected_financial_pct: 3.79,
      why_entered: "Sinal tecnico parecia forte, mas havia pouco suporte historico e confirmacoes externas fracas.",
      narrative: "Tecnico forte elevou a confianca, mas faltou confirmacao.",
      learning: "Reduzir confianca quando o tecnico vier sozinho.",
      success: false,
    },
    {
      label: "Tese B",
      instrument: "PETR4",
      strategy: "Operacao de alta",
      entry_date: "2024-04-19",
      entry_price: 40.53,
      target_price: 43.37,
      stop_price: 38.83,
      exit_date: "2024-05-02",
      exit_price: 42.18,
      realized_financial_pct: 3.14,
      expected_financial_pct: 4.82,
      why_entered: "Sinal tecnico veio acompanhado de fundamentos e noticias favoraveis.",
      narrative: "Tecnico veio com fundamento e noticias.",
      learning: "Manter a tese, mas recalibrar alvo agressivo.",
      success: true,
    },
    {
      label: "Proxima regra",
      instrument: "Shadow",
      strategy: "Regra candidata",
      realized_financial_pct: null,
      expected_financial_pct: null,
      why_entered: "O aprendizado vira criterio a ser testado antes de mudar a politica ativa.",
      narrative: "O aprendizado entra como regra candidata.",
      learning: "Testar em shadow antes de promover a politica.",
      success: null,
    },
  ];
  const visibleCases = cases.length ? cases : fallbackCases;

  return (
    <section style={{
      background: `linear-gradient(135deg, ${C.card}, #0a1422 58%, #081a20)`,
      border: `1px solid ${C.border}`,
      borderRadius: 16,
      padding: 18,
      boxShadow: "0 18px 46px rgba(0,0,0,0.22)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <div style={{ color: C.text, fontSize: 16, fontWeight: 800 }}>Evolucao do aprendizado</div>
          <div style={{ color: C.muted, fontSize: 12, marginTop: 4, maxWidth: 760 }}>
            {evolution?.headline || "Cada operacao vira diagnostico, regra candidata e novo criterio de decisao."}
          </div>
        </div>
        <Badge label="pos-morte na pratica" type="info" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(290px, 1fr))", alignItems: "stretch", gap: 12 }}>
        {visibleCases.map((item, index) => {
          const result = Number(item.realized_financial_pct);
          const hasResult = Number.isFinite(result);
          const tone = item.success === false ? C.coral : item.success === true ? C.teal : C.sky;
          const title = String(item.label || `Etapa ${index + 1}`);
          const instrument = String(item.instrument || "-");
          const expected = Number(item.expected_financial_pct);
          const statusLabel = item.success === false ? "ajustar regra" : item.success === true ? "manter criterio" : "validar em shadow";
          const detailRows = [
            { label: "Entrou", value: `${formatDateLabel(item.entry_date)} | ${formatCurrencyLabel(item.entry_price)}` },
            { label: "Alvo", value: formatCurrencyLabel(item.target_price) },
            { label: "Protecao", value: formatCurrencyLabel(item.stop_price) },
            { label: "Saiu", value: `${formatDateLabel(item.exit_date)} | ${formatCurrencyLabel(item.exit_price)}` },
          ].filter((row) => row.value && row.value !== "-" && row.value !== "- | -");
          return (
            <div key={`${instrument}-${index}`} style={{
              minHeight: 268,
              background: C.panel,
              border: `1px solid ${tone}55`,
              borderTop: `3px solid ${tone}`,
              borderRadius: 13,
              padding: "14px 14px 13px",
              display: "flex",
              flexDirection: "column",
              gap: 10,
              position: "relative",
              overflow: "hidden",
            }}>
              <div style={{
                position: "absolute",
                right: 14,
                top: 12,
                color: tone + "18",
                fontSize: 46,
                fontWeight: 900,
                fontFamily: mono,
                lineHeight: 1,
              }}>{index + 1}</div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", position: "relative" }}>
                <div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", maxWidth: 230 }}>{title}</div>
                <Badge label={instrument} type={item.success === false ? "danger" : item.success === true ? "success" : "info"} />
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, position: "relative" }}>
                <div style={{ color: tone, fontSize: 29, fontWeight: 850, fontFamily: mono }}>
                  {hasResult ? formatPctLabel(result) : "regra"}
                </div>
                {Number.isFinite(expected) && (
                  <div style={{ color: C.muted, fontSize: 11 }}>esperado {formatPctLabel(expected)}</div>
                )}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                <div style={{ color: C.sky, fontSize: 11, lineHeight: 1.3 }}>{item.strategy || "Operacao simulada"}</div>
                <Badge label={statusLabel} type={item.success === false ? "warning" : item.success === true ? "success" : "info"} />
              </div>
              {detailRows.length > 0 && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 }}>
                  {detailRows.map((row) => (
                    <div key={row.label} style={{ background: "#070d18", border: `1px solid ${C.border}`, borderRadius: 8, padding: "7px 8px" }}>
                      <div style={{ color: C.muted, fontSize: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>{row.label}</div>
                      <div style={{ color: C.text, fontSize: 11, marginTop: 3, fontFamily: mono }}>{row.value}</div>
                    </div>
                  ))}
                </div>
              )}
              <div style={{ background: "rgba(59, 158, 255, 0.06)", border: `1px solid ${C.sky}25`, borderRadius: 9, padding: "9px 10px" }}>
                <div style={{ color: C.sky, fontSize: 9, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4 }}>Por que entrou</div>
                <div style={{ color: C.text, fontSize: 11, lineHeight: 1.35 }}>{compactText(item.why_entered || item.narrative, 142)}</div>
              </div>
              <div style={{
                marginTop: "auto",
                background: "#070d18",
                border: `1px solid ${C.border}`,
                borderRadius: 9,
                padding: "9px 10px",
              }}>
                <div style={{ color: C.gold, fontSize: 9, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4 }}>O que mudou</div>
                <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.35 }}>{compactText(item.learning, 150)}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 14, color: C.sky, fontSize: 12, lineHeight: 1.45 }}>
        <strong>Conclusao:</strong> {evolution?.conclusion || "O tecnico continua relevante, mas precisa de confirmacao para sustentar confianca alta."}
      </div>
    </section>
  );
}

function LearningEvidencePanel({ prova, compact }) {
  const evidenceCards = [
    {
      label: "Padroes detectados",
      value: String(prova.comSintomaDetectado),
      sub: `${prova.comSintomaConfirmado} confirmados`,
      tone: C.sky,
    },
    {
      label: "Diagnostico",
      value: `${prova.acertoDiagnosticoPct}%`,
      sub: "acerto dos sinais",
      tone: prova.semaforoDiagnostico.color,
    },
    {
      label: "Ajustes em uso",
      value: `${prova.adocaoRemedioPct}%`,
      sub: `${prova.posComRemedio}/${prova.totalPosGoLive} teses pos go-live`,
      tone: prova.semaforoAdocao.color,
    },
    {
      label: "Efeito observado",
      value: prova.deltaMediaPos === null ? "em formacao" : `${prova.deltaMediaPos >= 0 ? "+" : ""}${prova.deltaMediaPos.toFixed(2)}pp`,
      sub: prova.deltaMediaPos === null ? prova.semaforoEfeito.observacao : `pos ${fmt(prova.mediaPos)} vs hist ${fmt(prova.mediaHistorica)}`,
      tone: prova.semaforoEfeito.color,
    },
  ];

  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 16, padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>Prova objetiva do aprendizado</div>
          <div style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>Erro identificado, ajuste aplicado e efeito observado.</div>
        </div>
        <Badge label="evidencia" type="info" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        {evidenceCards.map((item) => (
          <div key={item.label} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: "12px 13px" }}>
            <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>{item.label}</div>
            <div style={{ color: item.tone, fontSize: 22, fontWeight: 800, fontFamily: mono, marginTop: 8 }}>{item.value}</div>
            <div style={{ color: C.muted, fontSize: 11, marginTop: 5 }}>{item.sub}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(220px, 1fr))", gap: 10, marginTop: 12 }}>
        {prova.licoes.slice(0, 3).map((item) => (
          <div key={item.chave} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 12, background: "#090f1c" }}>
            <div style={{ color: C.coral, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Erro</div>
            <div style={{ color: C.text, fontSize: 12, marginTop: 5 }}>{item.dor}</div>
            <div style={{ height: 1, background: C.border, margin: "10px 0" }} />
            <div style={{ color: C.teal, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Mudanca</div>
            <div style={{ color: C.muted, fontSize: 12, marginTop: 5 }}>{item.remedio}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function OpenOperationsBoard({ rows, compact }) {
  const grouped = Object.values(rows.reduce((acc, thesis) => {
    const key = thesis.ativo;
    if (!acc[key]) {
      acc[key] = {
        ativo: thesis.ativo,
        direcao: thesis.direcao,
        count: 0,
        warnings: 0,
        expectedTotal: 0,
        momentumTotal: 0,
        latest: thesis,
        ids: [],
      };
    }
    acc[key].count += 1;
    acc[key].expectedTotal += toNumber(thesis.expected, 0);
    acc[key].momentumTotal += toNumber(thesis.momentum, 0);
    acc[key].warnings += String(thesis.desfecho || "").toLowerCase().includes("stop") ? 1 : 0;
    acc[key].ids.push(thesis.id);
    if (toNumber(thesis.id, 0) > toNumber(acc[key].latest.id, 0)) acc[key].latest = thesis;
    return acc;
  }, {})).sort((a, b) => b.warnings - a.warnings || b.count - a.count);

  return (
    <section>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>Teses abertas em monitoramento</div>
          <div style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>Consolidado por ativo para reduzir repeticao e destacar risco.</div>
        </div>
        <Badge label={`${teseCountLabel(rows.length)} abertas`} type="open" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(270px, 1fr))", gap: 14 }}>
        {grouped.map((group) => {
          const avgExpected = group.expectedTotal / Math.max(group.count, 1);
          const avgMomentum = group.momentumTotal / Math.max(group.count, 1);
          const warning = group.warnings > 0;
          const statusType = warning ? "warning" : "open";
          const tone = warning ? C.amber : C.teal;
          return (
            <div key={group.ativo} style={{
              background: C.card,
              border: `1px solid ${warning ? C.amber + "66" : C.border}`,
              borderLeft: `4px solid ${tone}`,
              borderRadius: 13,
              padding: 15,
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ color: C.text, fontSize: 18, fontWeight: 800 }}>{group.ativo}</span>
                    <Badge label={`${group.count}x`} type="info" />
                  </div>
                  <div style={{ color: C.muted, fontSize: 11, marginTop: 4 }}>Ids #{group.ids.slice(0, 4).join(", #")}</div>
                </div>
                <Badge label={warning ? "atenÃ§Ã£o" : "em monitoramento"} type={statusType} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div style={{ background: C.panel, borderRadius: 9, padding: "9px 10px" }}>
                  <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>Esperado medio</div>
                  <div style={{ color: avgExpected >= 0 ? C.teal : C.coral, fontSize: 16, fontWeight: 800, fontFamily: mono, marginTop: 5 }}>{formatPctLabel(avgExpected)}</div>
                </div>
                <div style={{ background: C.panel, borderRadius: 9, padding: "9px 10px" }}>
                  <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>Momento medio</div>
                  <div style={{ color: avgMomentum >= 0 ? C.teal : C.coral, fontSize: 16, fontWeight: 800, fontFamily: mono, marginTop: 5 }}>{formatPctLabel(avgMomentum)}</div>
                </div>
              </div>
              <div style={{ background: "#080e1a", border: `1px solid ${C.border}`, borderRadius: 9, padding: "9px 10px" }}>
                <div style={{ color: C.muted, fontSize: 10, marginBottom: 5 }}>Ultima estrutura</div>
                <div style={{ color: C.sky, fontSize: 12, lineHeight: 1.35 }}>{group.latest.estrutura}</div>
              </div>
              <div style={{ display: "flex", gap: 10, color: C.muted, fontSize: 11, marginTop: "auto" }}>
                <span>Entrada R$ {group.latest.entrada}</span>
                <span style={{ color: C.green }}>Alvo R$ {group.latest.saiGanho}</span>
                <span style={{ color: C.coral }}>Stop R$ {group.latest.saiStop}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function CompletedOperationsPreview({ rows, examples, compact }) {
  const visibleExamples = Array.isArray(examples) && examples.length ? examples.slice(0, 4) : [];
  const visibleRows = rows.slice(-4).reverse();
  if (visibleExamples.length) {
    return (
      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 16, padding: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>Operacoes avaliadas</div>
            <div style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>Exemplos fechados com entrada, saida, resultado e aprendizado pratico.</div>
          </div>
          <Badge label={`${teseCountLabel(visibleExamples.length)} exemplos`} type="closed" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(245px, 1fr))", gap: 10 }}>
          {visibleExamples.map((row, index) => {
            const result = toNumber(row.realized_financial_pct, 0);
            const expected = toNumber(row.expected_financial_pct, 0);
            const resultColor = result >= 0 ? C.teal : C.coral;
            return (
              <div key={`${row.instrument}-${row.thesis_id || index}`} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
                  <div>
                    <div style={{ color: C.text, fontSize: 16, fontWeight: 850 }}>{row.instrument || "-"}</div>
                    <div style={{ color: C.sky, fontSize: 11, marginTop: 3 }}>{row.strategy || "Operacao simulada"}</div>
                  </div>
                  <div style={{ color: resultColor, fontSize: 17, fontWeight: 850, fontFamily: mono }}>{formatPctLabel(result)}</div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 }}>
                  {[
                    { label: "Entrada", value: `${formatDateLabel(row.entry_date)} | ${formatCurrencyLabel(row.entry_price)}` },
                    { label: "Alvo", value: formatCurrencyLabel(row.target_price) },
                    { label: "Trava alta", value: formatCurrencyLabel(row.high_guard) },
                    { label: "Trava baixa", value: formatCurrencyLabel(row.low_guard) },
                    { label: "Saida", value: `${formatDateLabel(row.exit_date)} | ${formatCurrencyLabel(row.exit_price)}` },
                  ].map((item) => (
                    <div key={item.label} style={{ background: "#070d18", border: `1px solid ${C.border}`, borderRadius: 8, padding: "7px 8px" }}>
                      <div style={{ color: C.muted, fontSize: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>{item.label}</div>
                      <div style={{ color: C.text, fontSize: 10, marginTop: 3, fontFamily: mono }}>{item.value}</div>
                    </div>
                  ))}
                </div>
                <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 9 }}>
                  <div style={{ color: C.gold, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>Por que entrou</div>
                  <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.35, marginTop: 5 }}>{compactText(row.reason, 112)}</div>
                </div>
                <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.35, marginTop: "auto" }}>
                  Esperado {formatPctLabel(expected)} | realizado {formatPctLabel(result)}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 16, padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>Operacoes realizadas</div>
          <div style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>Resumo curto das teses ja fechadas e do aprendizado gerado.</div>
        </div>
        <Badge label={`${teseCountLabel(rows.length)} encerradas`} type="closed" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
        {visibleRows.map((row) => {
          const resultColor = row.resultado >= 0 ? C.teal : C.coral;
          return (
            <div key={`${row.id}-${row.ativo}`} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>{row.ativo}</div>
                <div style={{ color: resultColor, fontSize: 15, fontWeight: 800, fontFamily: mono }}>{formatPctLabel(row.resultado)}</div>
              </div>
              <div style={{ color: C.muted, fontSize: 11, marginTop: 7 }}>{row.estrutura}</div>
              <div style={{ height: 1, background: C.border, margin: "10px 0" }} />
              <div style={{ color: C.gold, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>Aprendizado</div>
              <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.35, marginTop: 5 }}>
                {row.aprendizado.length > 118 ? `${row.aprendizado.slice(0, 118)}...` : row.aprendizado}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Sidebar({ active, setActive }) {
  const items = [
    { id: "dashboard", label: "Dashboard", icon: "â—‰" },
    { id: "mercado",   label: "Mercado",   icon: "ã€œ" },
    { id: "operacoes", label: "OperaÃ§Ãµes",  icon: "â‡„" },
    { id: "backtest",  label: "Backtest",   icon: "â†º" },
    { id: "risco",     label: "Risco",      icon: "â—¬" },
    { id: "game",      label: "Game",       icon: "â—ˆ" },
    { id: "alertas",   label: "Alertas",    icon: "â—Ž" },
  ];

  return (
    <aside style={{
      width: 220, background: C.panel,
      borderRight: `1px solid ${C.border}`,
      display: "flex", flexDirection: "column",
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: "22px 20px 18px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <div style={{
            width: 32, height: 32, background: C.gold + "22",
            border: `1px solid ${C.gold}55`,
            borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, fontWeight: 700, color: C.gold, fontFamily: mono,
          }}>G</div>
          <div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 700, letterSpacing: "0.04em" }}>GRÃƒO</div>
            <div style={{ color: C.muted, fontSize: 9, letterSpacing: "0.08em", textTransform: "uppercase" }}>Invest</div>
          </div>
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 5, background: C.amber + "18", border: `1px solid ${C.amber}40`, borderRadius: 6, padding: "3px 8px" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: C.amber, display: "inline-block" }} />
          <span style={{ color: C.amber, fontSize: 9, fontWeight: 600, letterSpacing: "0.06em" }}>FASE 1 Â· SIMULAÃ‡ÃƒO</span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "12px 10px", flex: 1 }}>
        {items.map((item) => {
          const isActive = active === item.id;
          return (
            <button key={item.id} onClick={() => setActive(item.id)} style={{
              display: "flex", alignItems: "center", gap: 10,
              width: "100%", background: isActive ? C.gold + "18" : "transparent",
              color: isActive ? C.gold : C.muted,
              border: isActive ? `1px solid ${C.gold}35` : "1px solid transparent",
              borderRadius: 10, padding: "10px 12px",
              fontSize: 13, fontWeight: isActive ? 600 : 400,
              cursor: "pointer", textAlign: "left", marginBottom: 2,
              transition: "all 0.15s", fontFamily: "inherit",
            }}>
              <span style={{ fontSize: 12, width: 16, textAlign: "center", opacity: isActive ? 1 : 0.6 }}>{item.icon}</span>
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div style={{ padding: "14px 16px", borderTop: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 30, height: 30, background: C.sky + "30", border: `1px solid ${C.sky}44`, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: C.sky }}>AI</div>
          <div>
            <div style={{ color: C.text, fontSize: 12, fontWeight: 500 }}>Convidado</div>
            <div style={{ color: C.muted, fontSize: 10 }}>ConfiguraÃ§Ãµes</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function TabelaExercicio({ titulo, periodo, teses, esperado, alcancado, aprovadas }) {
  const gapColor = parseFloat(alcancado) >= parseFloat(esperado) ? C.green : C.coral;
  const gap = (parseFloat(alcancado) - parseFloat(esperado)).toFixed(2);

  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>{titulo}</div>
          <div style={{ color: C.muted, fontSize: 11, marginTop: 2 }}>{periodo}</div>
        </div>
        <Badge label={`${teses} teses`} type="info" />
      </div>
      <div style={{ padding: "14px 20px", display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12 }}>
        {[
          { label: "Teses", value: teses, color: C.text },
          { label: "Esperado", value: `${esperado}%`, color: C.sky },
          { label: "AlcanÃ§ado", value: `${alcancado}%`, color: parseFloat(alcancado) >= 0 ? C.teal : C.coral },
          { label: "Gap", value: `${gap > 0 ? "+" : ""}${gap}pp`, color: gapColor },
        ].map((s) => (
          <div key={s.label} style={{ background: C.panel, borderRadius: 10, padding: "10px 12px" }}>
            <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>{s.label}</div>
            <div style={{ color: s.color, fontSize: 18, fontWeight: 700, fontFamily: mono }}>{s.value}</div>
          </div>
        ))}
      </div>
      <div style={{ padding: "0 20px 14px", display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ color: C.muted, fontSize: 11 }}>Aprovadas:</span>
        <span style={{ color: C.green, fontWeight: 700, fontFamily: mono, fontSize: 13 }}>{aprovadas}</span>
        <div style={{ flex: 1, height: 4, background: C.line, borderRadius: 99, overflow: "hidden" }}>
          <div style={{ width: `${(aprovadas / teses) * 100}%`, height: "100%", background: C.teal, borderRadius: 99 }} />
        </div>
        <span style={{ color: C.muted, fontSize: 10 }}>{Math.round((aprovadas / teses) * 100)}%</span>
      </div>
    </div>
  );
}

function TabelaTeses({ rows, titulo }) {
  const [expandedId, setExpandedId] = useState(null);

  const toggleDetail = (id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>{titulo}</div>
        <div style={{ color: C.muted, fontSize: 11, marginTop: 6 }}>
          Clique na linha para abrir ou fechar os detalhes da tese.
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr style={{ background: C.panel }}>
              {["#", "A??o", "Dire??o", "Esperado", "Estrutura", "Entrada", "Sa?da se", "Desfecho", "Dias", "Status", "Resultado"].map((h) => (
                <th key={h} style={{ padding: "9px 12px", color: C.muted, fontWeight: 600, textAlign: "left", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: `1px solid ${C.border}`, whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.flatMap((r, i) => {
              const resColor = r.resultado > 0 ? C.teal : r.resultado < 0 ? C.coral : C.muted;
              const isExpanded = expandedId === r.id;
              const dirType = r.direcao === "Alta" ? "bull" : r.direcao === "Baixa" ? "bear" : "neutral";

              const mainRow = (
                <tr
                  key={`row-${r.id}-${i}`}
                  style={{ borderBottom: `1px solid ${C.line}`, transition: "background 0.1s", cursor: "pointer" }}
                  onClick={() => toggleDetail(r.id)}
                  onMouseEnter={(e) => e.currentTarget.style.background = C.hover}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <td style={{ padding: "10px 12px", color: C.dim, fontFamily: mono }}>{r.id}</td>
                  <td style={{ padding: "10px 12px", color: C.text, fontWeight: 700 }}>{r.ativo}</td>
                  <td style={{ padding: "10px 12px" }}><Badge label={r.direcao} type={dirType} /></td>
                  <td style={{ padding: "10px 12px", color: C.sky, fontFamily: mono }}>{r.esperado}</td>
                  <td style={{ padding: "10px 12px", color: C.muted, maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.estrutura}</td>
                  <td style={{ padding: "10px 12px", color: C.text, fontFamily: mono }}>
                    {r.entrada === "-" ? "-" : `R$ ${r.entrada}`}
                  </td>
                  <td style={{ padding: "10px 12px", color: C.muted, fontFamily: mono, fontSize: 10 }}>{r.saida}</td>
                  <td style={{ padding: "10px 12px" }}><Badge label={r.desfecho} type={r.desfecho?.includes("stop") ? "warning" : r.desfecho === "Tempo" ? "neutral" : "open"} /></td>
                  <td style={{ padding: "10px 12px", color: C.muted, fontFamily: mono }}>{r.dias}d</td>
                  <td style={{ padding: "10px 12px" }}><Badge label={r.status} type={r.status === "Aberta" ? "open" : "closed"} /></td>
                  <td style={{ padding: "10px 12px", color: resColor, fontFamily: mono, fontWeight: 700 }}>{r.resultado > 0 ? "+" : ""}{r.resultado?.toFixed(2)}%</td>
                </tr>
              );

              const detailRow = isExpanded ? (
                <tr key={`detail-${r.id}-${i}`}>
                  <td colSpan={11} style={{ padding: "12px 14px", background: C.panel, borderBottom: `1px solid ${C.line}` }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px" }}>
                        <p style={{ margin: "0 0 6px", color: C.gold, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                          Por que entramos
                        </p>
                        <p style={{ margin: 0, color: C.text, fontSize: 12, lineHeight: 1.45 }}>
                          {r.porQue || "Sem detalhamento dispon?vel para esta tese."}
                        </p>
                      </div>
                      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px" }}>
                        <p style={{ margin: "0 0 6px", color: C.teal, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                          O que aprendemos
                        </p>
                        <p style={{ margin: 0, color: C.text, fontSize: 12, lineHeight: 1.45 }}>
                          {r.aprendizado || "Sem aprendizado registrado ainda."}
                        </p>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : null;

              return detailRow ? [mainRow, detailRow] : [mainRow];
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const tesisAbertas = [
  {
    id: 162, ativo: "KNRI11", direcao: "Alta", entrada: "154,25",
    expected: 3.01, momentum: 0.83, estrutura: "Bull Call Spread Â· ganho 5,40% Â· perda 2,20%",
    saiGanho: "9,90", saiStop: "8,86", status: "Aberta", desfecho: "Em monitoramento",
    inicio: "14/04",
  },
  {
    id: 161, ativo: "AAPL34", direcao: "Alta", entrada: "46,39",
    expected: 2.76, momentum: -0.36, estrutura: "Bull Call Spread Â· ganho 5,40% Â· perda 2,20%",
    saiGanho: "9,99", saiStop: "9,03", status: "Aberta", desfecho: "Em monitoramento",
    inicio: "15/04",
  },
  {
    id: 160, ativo: "PETR4", direcao: "Neutro", entrada: "41,03",
    expected: 0.82, momentum: -3.88, estrutura: "Iron Condor Â· ganho 2,40% Â· perda 3,80%",
    saiGanho: "41,03", saiStop: "40,41", status: "Aberta", desfecho: "Alerta de stop",
    inicio: "21/04",
  },
];

const tesesHistoricas = [
  {
    id: 159,
    ativo: "PETR4",
    direcao: "Alta",
    esperado: "+4,82%",
    estrutura: "Bull Call Spread | ganho 5,40% | perda 2,20%",
    entrada: "40,53",
    saida: ">=43,37 / <=38,83",
    desfecho: "Tempo",
    dias: 13,
    status: "Fechada",
    resultado: 3.14,
    porQue: "A tese foi aberta porque o preco reagiu em suporte tecnico, com contexto favoravel em fundamentos e fluxo mais comprador no periodo.",
    aprendizado: "Quando o alvo nao vem no tempo esperado, a estrutura protegeu o capital. Proxima melhoria: reduzir janela e usar saida parcial no meio do caminho.",
    melhoriasAplicadas: ["tempo_da_tese", "saida_parcial"],
    sintomaDetectado: true,
    sintomaConfirmado: true,
  },
];

const tesesPosGoLive = [
  {
    id: 160,
    ativo: "PETR4",
    direcao: "Neutro",
    esperado: "+0,82%",
    estrutura: "Iron Condor | ganho 2,40% | perda 3,80%",
    entrada: "41,03",
    saida: ">=41,03 / <=40,41",
    desfecho: "Alerta de stop",
    dias: 0,
    status: "Aberta",
    resultado: -3.88,
    porQue: "Entramos com cenario de lateralizacao, pois o ativo vinha oscilando em faixa estreita com volatilidade controlada e sem tendencia forte definida.",
    aprendizado: "Com rompimento rapido da faixa, reforcamos que cenarios neutros precisam gatilho de saida mais cedo quando o mercado acelera para um lado.",
    melhoriasAplicadas: ["stop_antecipado", "range_break_rapido"],
    sintomaDetectado: true,
    sintomaConfirmado: true,
  },
  {
    id: 161,
    ativo: "AAPL34",
    direcao: "Alta",
    esperado: "+2,76%",
    estrutura: "Bull Call Spread | ganho 5,40% | perda 2,20%",
    entrada: "9,39",
    saida: ">=9,99 / <=9,03",
    desfecho: "Em monitoramento",
    dias: 0,
    status: "Aberta",
    resultado: -0.36,
    porQue: "A tese surgiu por retomada de momentum de alta com confirmacao de preco acima de zona de suporte e assimetria favoravel entre risco e retorno.",
    aprendizado: "Em mercado mais ruidoso, manter protecao curta continua importante. Vamos priorizar confirmacao de volume antes de repetir entradas parecidas.",
    melhoriasAplicadas: ["confirmacao_volume", "protecao_curta"],
    sintomaDetectado: true,
    sintomaConfirmado: false,
  },
  {
    id: 162,
    ativo: "KNRI11",
    direcao: "Alta",
    esperado: "+3,01%",
    estrutura: "Bull Call Spread | ganho 5,40% | perda 2,20%",
    entrada: "9,25",
    saida: ">=9,90 / <=8,86",
    desfecho: "Em monitoramento",
    dias: 0,
    status: "Aberta",
    resultado: 0.83,
    porQue: "Entramos apos sinal tecnico de continuidade da alta, com leitura de contexto menos adverso e relacao risco-retorno dentro do limite definido.",
    aprendizado: "A leitura inicial esta funcionando, mas ainda em fase aberta. Proximo ajuste sera calibrar tempo maximo da tese para capturar ganho sem prolongar exposicao.",
    melhoriasAplicadas: ["tempo_maximo", "calibragem_alvo"],
    sintomaDetectado: false,
    sintomaConfirmado: false,
  },
];

// â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function GraoDashboard() {
  const isCompact = useCompactLayout();

  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap";
    document.head.appendChild(link);
    return () => { link.remove(); };
  }, []);

  const [apiData, setApiData] = useState(null);
  const [executiveData, setExecutiveData] = useState(null);
  const [apiError, setApiError] = useState("");
  const [lastSync, setLastSync] = useState("");

  useEffect(() => {
    let canceled = false;
    const loadSummary = async () => {
      try {
        const response = await fetch("/api/dashboard/summary/1", {
          method: "GET",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = await response.json();
        let executivePayload = null;
        try {
          const executiveResponse = await fetch("/api/reports/executive", {
            method: "GET",
            headers: { Accept: "application/json" },
          });
          if (executiveResponse.ok) {
            executivePayload = await executiveResponse.json();
          }
        } catch (_) {
          executivePayload = null;
        }
        if (!canceled) {
          setApiData(payload);
          setExecutiveData(executivePayload);
          setApiError("");
          setLastSync(new Date().toISOString());
        }
      } catch (error) {
        if (!canceled) {
          setApiError(String(error?.message || "Falha ao atualizar"));
        }
      }
    };

    loadSummary();
    const timer = window.setInterval(loadSummary, 60000);
    return () => {
      canceled = true;
      window.clearInterval(timer);
    };
  }, []);

  const runtime = useMemo(() => {
    if (!apiData || typeof apiData !== "object") return null;
    const kickoffDate = String(apiData.phase_kickoff_date || "2026-04-27");
    const overview = apiData.thesis_history_overview && typeof apiData.thesis_history_overview === "object"
      ? apiData.thesis_history_overview
      : {};
    const operationsRaw = Array.isArray(apiData.thesis_open_operations) ? apiData.thesis_open_operations : [];
    const mapped = operationsRaw
      .filter((row) => row && typeof row === "object")
      .map((row, index) => mapOperationRowToTable(row, index))
      .sort((a, b) => toNumber(a.id, 0) - toNumber(b.id, 0));
    const historical = mapped.filter((row) => classifyPhase(row.origem, kickoffDate) === "historical");
    const current = mapped.filter((row) => classifyPhase(row.origem, kickoffDate) === "current");
    const currentOpen = current.filter((row) => isOpenStatus(row.status));
    const cards = currentOpen
      .slice()
      .sort((a, b) => toNumber(b.id, 0) - toNumber(a.id, 0))
      .slice(0, 6)
      .map((row) => {
        const levels = extractExitLevels(row.saida);
        const raisedAt = String(row.origem?.thesis_raised_at || "");
        const startLabel = raisedAt.length >= 10 ? `${raisedAt.slice(8, 10)}/${raisedAt.slice(5, 7)}` : "";
        return {
          id: row.id,
          ativo: row.ativo,
          direcao: row.direcao,
          entrada: row.entrada,
          expected: toNumber(row.origem?.expected_result_pct, 0),
          momentum: toNumber(row.resultado, 0),
          estrutura: row.estrutura,
          saiGanho: levels.gain,
          saiStop: levels.stop,
          status: row.status,
          desfecho: row.desfecho,
          inicio: startLabel,
        };
      });

    const totalTested = toNumber(overview.total_tested, historical.length + current.length);
    const successCount = toNumber(overview.success_count, mapped.filter((row) => row.resultado >= 0).length);
    const successRatePct = toNumber(overview.success_rate_pct, pct(successCount, totalTested));
    const expectancyNetPct = toNumber(overview.expectancy_net_pct, 0);
    const targetRatePct = toNumber(overview.target_rate_pct, 0);
    const stopRatePct = toNumber(overview.stop_rate_pct, 0);
    const timeExitRatePct = toNumber(overview.time_exit_rate_pct, 0);
    const openRatePct = toNumber(overview.open_rate_pct, 0);
    const openCount = toNumber(overview.open_count, 0);
    const avgResolutionDays = toNumber(overview.avg_resolution_days, 0);
    const resolutionSampleCount = toNumber(overview.resolution_sample_count, 0);

    return {
      kickoffDate,
      historical,
      current,
      currentOpen,
      cards,
      summary: {
        totalTested,
        successCount,
        successRatePct,
        expectancyNetPct,
        targetRatePct,
        stopRatePct,
        timeExitRatePct,
        openRatePct,
        openCount,
        avgResolutionDays,
        resolutionSampleCount,
        windowStart: String(overview.window_start || "-"),
        windowEnd: String(overview.window_end || "-"),
      },
    };
  }, [apiData]);

  const tesesHistoricasView = runtime?.historical?.length ? runtime.historical : tesesHistoricas;
  const tesesPosGoLiveViewAll = runtime?.current?.length ? runtime.current : tesesPosGoLive;
  const tesesPosGoLiveViewOpen = runtime?.currentOpen?.length ? runtime.currentOpen : tesesPosGoLive;
  const tesisAbertasView = runtime?.cards?.length ? runtime.cards : tesisAbertas;
  const tesesHistoricasDrilldown = tesesHistoricasView.slice(-12).reverse();
  const tesesPosGoLiveDrilldown = tesesPosGoLiveViewOpen.slice(0, 12);
  const resumoKpis = runtime?.summary || {
    totalTested: 162,
    successCount: 152,
    successRatePct: 93.83,
    expectancyNetPct: 3.07,
    targetRatePct: 93.83,
    stopRatePct: 3.09,
    timeExitRatePct: 3.09,
    openRatePct: 0,
    openCount: 0,
    avgResolutionDays: 13,
    resolutionSampleCount: 1,
    windowStart: "2026-04-20",
    windowEnd: "2026-05-01",
  };
  const learningEvolution = executiveData?.learning_evolution || null;

  const provaAprendizado = useMemo(() => {
    const mapaLicoes = {
      tempo_da_tese: {
        ordem: 1,
        dor: "Tese fica aberta sem andar",
        sintoma: "3 a 5 pregoes sem tracao",
        remedio: "Definir janela maxima e encerrar por tempo",
      },
      saida_parcial: {
        ordem: 2,
        dor: "Lucro devolvido no fim",
        sintoma: "Ativo bate parte do alvo e perde forca",
        remedio: "Realizar parcial e proteger o restante",
      },
      stop_antecipado: {
        ordem: 3,
        dor: "Perda acelera rapido",
        sintoma: "Perda de suporte com aumento de volatilidade",
        remedio: "Antecipar stop antes do limite final",
      },
      range_break_rapido: {
        ordem: 4,
        dor: "Cenario neutro quebra cedo",
        sintoma: "Rompimento forte da faixa",
        remedio: "Sair sem esperar retorno para a faixa",
      },
      confirmacao_volume: {
        ordem: 5,
        dor: "Entrada em rompimento falso",
        sintoma: "Movimento sem volume de confirmacao",
        remedio: "Entrar so com volume acima da media",
      },
      protecao_curta: {
        ordem: 6,
        dor: "Ruido tira resultado",
        sintoma: "Oscilacao curta contra a tese",
        remedio: "Manter protecao curta e revisar rapido",
      },
      tempo_maximo: {
        ordem: 7,
        dor: "Exposicao longa sem premio",
        sintoma: "Ganho nao acelera dentro da janela",
        remedio: "Calibrar tempo maximo por padrao",
      },
      calibragem_alvo: {
        ordem: 8,
        dor: "Alvo distante demais",
        sintoma: "Preco evolui, mas nao completa o alvo",
        remedio: "Reduzir alvo para capturar ganho mais cedo",
      },
    };

    const todas = [...tesesHistoricasView, ...tesesPosGoLiveViewAll];
    const posGoLive = [...tesesPosGoLiveViewAll];

    const posComRemedio = posGoLive.filter((tese) => Array.isArray(tese.melhoriasAplicadas) && tese.melhoriasAplicadas.length > 0).length;
    const adocaoRemedioPct = pct(posComRemedio, posGoLive.length);
    const semaforoAdocao = semaforoPorPercentual(adocaoRemedioPct, 80, 50);

    const comSintomaDetectado = todas.filter((tese) => tese.sintomaDetectado).length;
    const comSintomaConfirmado = todas.filter((tese) => tese.sintomaDetectado && tese.sintomaConfirmado).length;
    const acertoDiagnosticoPct = pct(comSintomaConfirmado, comSintomaDetectado);
    const semaforoDiagnostico = semaforoPorPercentual(acertoDiagnosticoPct, 70, 45);

    const historicasFechadas = tesesHistoricasView.filter((tese) => tese.status === "Fechada");
    const posFechadas = tesesPosGoLiveViewAll.filter((tese) => tese.status === "Fechada");
    const mediaHistorica = avg(historicasFechadas.map((tese) => tese.resultado));
    const mediaPos = avg(posFechadas.map((tese) => tese.resultado));
    const deltaMediaPos = mediaPos !== null && mediaHistorica !== null ? mediaPos - mediaHistorica : null;

    const semaforoEfeito = deltaMediaPos === null
      ? { label: "Amarelo", type: "warning", color: C.amber, observacao: "Ainda sem teses fechadas no pos go-live" }
      : deltaMediaPos >= 0
        ? { label: "Verde", type: "success", color: C.green, observacao: "Media pos go-live acima do historico" }
        : { label: "Vermelho", type: "danger", color: C.coral, observacao: "Media pos go-live abaixo do historico" };

    const semaforoMaturidade = semaforoAmostra(posFechadas.length);

    const porLicao = {};
    todas.forEach((tese) => {
      const aplicacoes = Array.isArray(tese.melhoriasAplicadas) ? tese.melhoriasAplicadas : [];
      aplicacoes.forEach((item) => {
        porLicao[item] = (porLicao[item] || 0) + 1;
      });
    });

    const licoes = Object.entries(porLicao)
      .map(([chave, qtd]) => ({
        chave,
        qtd,
        ...mapaLicoes[chave],
      }))
      .filter((item) => item.dor && item.sintoma && item.remedio)
      .sort((a, b) => {
        if (b.qtd !== a.qtd) return b.qtd - a.qtd;
        return (a.ordem || 99) - (b.ordem || 99);
      })
      .slice(0, 6);

    return {
      adocaoRemedioPct,
      posComRemedio,
      totalPosGoLive: posGoLive.length,
      semaforoAdocao,
      acertoDiagnosticoPct,
      comSintomaConfirmado,
      comSintomaDetectado,
      semaforoDiagnostico,
      deltaMediaPos,
      mediaPos,
      mediaHistorica,
      semaforoEfeito,
      posFechadas: posFechadas.length,
      semaforoMaturidade,
      licoes,
    };
  }, [tesesHistoricasView, tesesPosGoLiveViewAll]);


  return (
    <div style={{
      display: "flex", background: C.bg, minHeight: 640,
      fontFamily: "Sora, system-ui, sans-serif", color: C.text,
      borderRadius: 18, overflow: "hidden", border: `1px solid ${C.border}`,
      width: "100%", maxWidth: "100%", minWidth: 0,
    }}>
      {/* Main */}
      <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Topbar interna removida: usamos a topbar do shell principal */}

        {/* Content */}
        <div style={{ padding: isCompact ? "14px 12px 34px" : "24px 28px 40px", display: "flex", flexDirection: "column", gap: isCompact ? 18 : 24, minWidth: 0 }}>

          <div style={{
            display: "grid",
            gridTemplateColumns: isCompact ? "1fr" : "repeat(auto-fit, minmax(360px, 1fr))",
            gap: 18,
            alignItems: "stretch",
            minWidth: 0,
          }}>
            <div style={{
              background: `linear-gradient(140deg, #111827, #0b1725 62%, #061c1f)`,
              border: `1px solid ${C.border}`,
              borderRadius: 18,
              padding: 22,
              minHeight: 190,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              minWidth: 0,
            }}>
              <div>
                <div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 10 }}>
                  Reporte executivo
                </div>
                <div style={{ color: C.text, fontSize: 28, fontWeight: 850, lineHeight: 1.08, maxWidth: 760 }}>
                  Dos exercicios para aprendizado operacional.
                </div>
                <div style={{ color: C.muted, fontSize: 13, lineHeight: 1.45, marginTop: 12, maxWidth: 760 }}>
                  Exploramos movimentos diarios da bolsa, combinamos sinais tecnicos, fundamentos e contexto externo; cada tese vira operacao simulada, pos-morte e ajuste para a proxima decisao.
                </div>
                {apiError && <div style={{ color: C.coral, fontSize: 11, marginTop: 10 }}>{`Atualizacao em contingencia: ${apiError}`}</div>}
                {!apiError && lastSync && <div style={{ color: C.muted, fontSize: 10, marginTop: 10 }}>{`Atualizado em: ${lastSync.slice(0, 19).replace("T", " ")}`}</div>}
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
                <Badge label={`${teseCountLabel(resumoKpis.totalTested)} avaliadas`} type="info" />
                <Badge label={`${resumoKpis.successRatePct.toFixed(1).replace(".", ",")}% sucesso`} type="success" />
                <Badge label={`${teseCountLabel(tesisAbertasView.length)} abertas`} type="open" />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: isCompact ? "1fr" : "1fr 1fr", gap: 12, minWidth: 0 }}>
              <KPICard label="Resultado medio" value={formatPctLabel(resumoKpis.expectancyNetPct)} sub="Media por tese resolvida" valueColor={C.teal} accent={C.teal} />
              <KPICard label="Taxa de sucesso" value={`${resumoKpis.successRatePct.toFixed(2).replace(".", ",")}%`} sub={`${resumoKpis.successCount} de ${resumoKpis.totalTested}`} valueColor={C.green} accent={C.green} />
              <KPICard label="Stops" value={`${resumoKpis.stopRatePct.toFixed(2).replace(".", ",")}%`} sub="Casos que viraram aprendizado" valueColor={C.coral} accent={C.coral} />
              <KPICard label="Abertas" value={String(tesisAbertasView.length)} sub="Em monitoramento hoje" valueColor={C.amber} accent={C.amber} />
            </div>
          </div>

          <ExecutiveMethodStrip executiveData={executiveData} resumoKpis={resumoKpis} compact={isCompact} />

          <LearningJourney evolution={learningEvolution} compact={isCompact} />

          <OpenOperationsBoard rows={tesisAbertasView} compact={isCompact} />

          <LearningEvidencePanel prova={provaAprendizado} compact={isCompact} />

          <CompletedOperationsPreview rows={tesesHistoricasView} examples={executiveData?.examples || []} compact={isCompact} />
          {/* Drilldown executivo limitado para manter a pagina leve. */}
          <TabelaTeses titulo="Detalhamento recente: teses encerradas" rows={tesesHistoricasDrilldown} />

          <TabelaTeses titulo="Detalhamento recente: teses abertas" rows={tesesPosGoLiveDrilldown} />

        </div>
      </div>
    </div>
  );
}


  const rootNode = document.getElementById("finvest-root");
  if (!rootNode) {
    return;
  }
  const root = window.ReactDOM.createRoot(rootNode);
  root.render(<GraoDashboard />);
})();

