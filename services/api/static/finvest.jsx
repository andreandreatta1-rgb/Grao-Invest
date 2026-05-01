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
          <Badge label={thesis.direcao} type={thesis.direcao === "Alta" ? "bull" : "bear"} />
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
        <span style={{ color: C.muted, fontSize: 10 }}>Saída</span>
        <span style={{ color: C.green, fontSize: 11, fontFamily: mono, fontWeight: 600 }}>▲ R$ {thesis.saiGanho}</span>
        <div style={{ width: 1, height: 12, background: C.border }} />
        <span style={{ color: C.coral, fontSize: 11, fontFamily: mono, fontWeight: 600 }}>▼ R$ {thesis.saiStop}</span>
        {thesis.inicio && <span style={{ color: C.muted, fontSize: 10, marginLeft: "auto" }}>go-live {thesis.inicio}</span>}
      </div>
    </div>
  );
}

function Sidebar({ active, setActive }) {
  const items = [
    { id: "dashboard", label: "Dashboard", icon: "◉" },
    { id: "mercado",   label: "Mercado",   icon: "〜" },
    { id: "operacoes", label: "Operações",  icon: "⇄" },
    { id: "backtest",  label: "Backtest",   icon: "↺" },
    { id: "risco",     label: "Risco",      icon: "◬" },
    { id: "game",      label: "Game",       icon: "◈" },
    { id: "alertas",   label: "Alertas",    icon: "◎" },
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
            <div style={{ color: C.text, fontSize: 14, fontWeight: 700, letterSpacing: "0.04em" }}>GRÃO</div>
            <div style={{ color: C.muted, fontSize: 9, letterSpacing: "0.08em", textTransform: "uppercase" }}>Invest</div>
          </div>
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 5, background: C.amber + "18", border: `1px solid ${C.amber}40`, borderRadius: 6, padding: "3px 8px" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: C.amber, display: "inline-block" }} />
          <span style={{ color: C.amber, fontSize: 9, fontWeight: 600, letterSpacing: "0.06em" }}>FASE 1 · SIMULAÇÃO</span>
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
            <div style={{ color: C.muted, fontSize: 10 }}>Configurações</div>
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
          { label: "Alcançado", value: `${alcancado}%`, color: parseFloat(alcancado) >= 0 ? C.teal : C.coral },
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
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr style={{ background: C.panel }}>
              {["#", "A??o", "Dire??o", "Esperado", "Estrutura", "Entrada", "Sa?da se", "Desfecho", "Dias", "Status", "Resultado", "Detalhe"].map((h) => (
                <th key={h} style={{ padding: "9px 12px", color: C.muted, fontWeight: 600, textAlign: "left", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: `1px solid ${C.border}`, whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.flatMap((r, i) => {
              const resColor = r.resultado > 0 ? C.teal : r.resultado < 0 ? C.coral : C.muted;
              const isExpanded = expandedId === r.id;

              const mainRow = (
                <tr
                  key={`row-${r.id}-${i}`}
                  style={{ borderBottom: `1px solid ${C.line}`, transition: "background 0.1s" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = C.hover}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <td style={{ padding: "10px 12px", color: C.dim, fontFamily: mono }}>{r.id}</td>
                  <td style={{ padding: "10px 12px", color: C.text, fontWeight: 700 }}>{r.ativo}</td>
                  <td style={{ padding: "10px 12px" }}><Badge label={r.direcao} type={r.direcao === "Alta" ? "bull" : "bear"} /></td>
                  <td style={{ padding: "10px 12px", color: C.sky, fontFamily: mono }}>{r.esperado}</td>
                  <td style={{ padding: "10px 12px", color: C.muted, maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.estrutura}</td>
                  <td style={{ padding: "10px 12px", color: C.text, fontFamily: mono }}>R$ {r.entrada}</td>
                  <td style={{ padding: "10px 12px", color: C.muted, fontFamily: mono, fontSize: 10 }}>{r.saida}</td>
                  <td style={{ padding: "10px 12px" }}><Badge label={r.desfecho} type={r.desfecho?.includes("stop") ? "warning" : r.desfecho === "Tempo" ? "neutral" : "open"} /></td>
                  <td style={{ padding: "10px 12px", color: C.muted, fontFamily: mono }}>{r.dias}d</td>
                  <td style={{ padding: "10px 12px" }}><Badge label={r.status} type={r.status === "Aberta" ? "open" : "closed"} /></td>
                  <td style={{ padding: "10px 12px", color: resColor, fontFamily: mono, fontWeight: 700 }}>{r.resultado > 0 ? "+" : ""}{r.resultado?.toFixed(2)}%</td>
                  <td style={{ padding: "10px 12px" }}>
                    <button
                      type="button"
                      onClick={() => toggleDetail(r.id)}
                      style={{
                        background: isExpanded ? `${C.gold}22` : C.panel,
                        color: isExpanded ? C.gold : C.sky,
                        border: `1px solid ${isExpanded ? `${C.gold}66` : C.border}`,
                        borderRadius: 8,
                        padding: "5px 9px",
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        cursor: "pointer",
                      }}
                    >
                      {isExpanded ? "Ocultar" : "Abrir"}
                    </button>
                  </td>
                </tr>
              );

              const detailRow = isExpanded ? (
                <tr key={`detail-${r.id}-${i}`}>
                  <td colSpan={12} style={{ padding: "12px 14px", background: C.panel, borderBottom: `1px solid ${C.line}` }}>
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

// ── Data ──────────────────────────────────────────────────────────────────────

const tesisAbertas = [
  {
    id: 162, ativo: "MGLU3", direcao: "Alta", entrada: "9,25",
    expected: 3.01, momentum: 0.83, estrutura: "Bull Call Spread · ganho 5,40% · perda 2,20%",
    saiGanho: "9,90", saiStop: "8,86", status: "Aberta", desfecho: "Em monitoramento",
    inicio: "14/04",
  },
  {
    id: 161, ativo: "MGLU3", direcao: "Alta", entrada: "9,39",
    expected: 2.76, momentum: -0.36, estrutura: "Bull Call Spread · ganho 5,40% · perda 2,20%",
    saiGanho: "9,99", saiStop: "9,03", status: "Aberta", desfecho: "Em monitoramento",
    inicio: "15/04",
  },
  {
    id: 160, ativo: "PETR4", direcao: "Neutro", entrada: "41,03",
    expected: 0.82, momentum: -3.88, estrutura: "Iron Condor · ganho 2,40% · perda 3,80%",
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
  },
  {
    id: 161,
    ativo: "MGLU3",
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
  },
  {
    id: 162,
    ativo: "MGLU3",
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
  },
];

// ── Main ──────────────────────────────────────────────────────────────────────

function GraoDashboard() {

  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap";
    document.head.appendChild(link);
    return () => { link.remove(); };
  }, []);

  const indicadorAprendizado = useMemo(() => {
    const todas = [...tesesHistoricas, ...tesesPosGoLive];
    const labels = {
      stop_antecipado: "Stop antecipado",
      range_break_rapido: "Quebra de faixa",
      confirmacao_volume: "Confirmacao por volume",
      protecao_curta: "Protecao curta",
      tempo_maximo: "Tempo maximo",
      calibragem_alvo: "Calibragem de alvo",
      tempo_da_tese: "Janela da tese",
      saida_parcial: "Saida parcial",
    };

    let tesesComAplicacao = 0;
    const porCategoria = {};

    todas.forEach((tese) => {
      const aplicacoes = Array.isArray(tese.melhoriasAplicadas) ? tese.melhoriasAplicadas : [];
      if (aplicacoes.length) {
        tesesComAplicacao += 1;
      }
      aplicacoes.forEach((item) => {
        porCategoria[item] = (porCategoria[item] || 0) + 1;
      });
    });

    const categorias = Object.entries(porCategoria)
      .map(([chave, qtd]) => ({
        chave,
        nome: labels[chave] || chave,
        qtd,
        pct: todas.length ? Math.round((qtd / todas.length) * 100) : 0,
      }))
      .sort((a, b) => b.qtd - a.qtd)
      .slice(0, 6);

    const taxaAplicacao = todas.length ? Math.round((tesesComAplicacao / todas.length) * 100) : 0;

    return {
      totalTeses: todas.length,
      tesesComAplicacao,
      taxaAplicacao,
      categorias,
    };
  }, []);


  return (
    <div style={{
      display: "flex", background: C.bg, minHeight: 640,
      fontFamily: "Sora, system-ui, sans-serif", color: C.text,
      borderRadius: 18, overflow: "hidden", border: `1px solid ${C.border}`,
    }}>
      {/* Main */}
      <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        {/* Topbar interna removida: usamos a topbar do shell principal */}

        {/* Content */}
        <div style={{ padding: "24px 28px 40px", display: "flex", flexDirection: "column", gap: 24 }}>

          {/* Section title */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ color: C.text, fontSize: 15, fontWeight: 700 }}>Resumo de teses</div>
              <div style={{ color: C.muted, fontSize: 12, marginTop: 2 }}>Período: 20/04/2026 → 01/05/2026 · histórico total</div>
            </div>
            <Badge label="162 teses testadas" type="info" />
          </div>

          {/* KPI grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
            <KPICard label="Teses testadas" value="162" sub="20/04 → 01/05" accent={C.sky} icon="◎" />
            <KPICard label="Expectância líquida" value="+3,07%" sub="Média por tese resolvida" valueColor={C.teal} accent={C.teal} icon="〜" />
            <KPICard label="Taxa de sucesso" value="93,83%" sub="152 de 162 teses" valueColor={C.green} accent={C.green} icon="✓" />
            <KPICard
              label="Alvo / Stop / Tempo"
              value={<span style={{ fontSize: 15, letterSpacing: 0 }}>
                <span style={{ color: C.teal }}>93,83%</span>
                <span style={{ color: C.dim }}> / </span>
                <span style={{ color: C.coral }}>3,09%</span>
                <span style={{ color: C.dim }}> / </span>
                <span style={{ color: C.gold }}>3,09%</span>
              </span>}
              sub="Em monitoramento: 0,00%"
              accent={C.gold}
              icon="◬"
            />
            <KPICard label="Tempo médio" value="13 dias" sub="Amostra: 1 tese" valueColor={C.amber} accent={C.amber} icon="◷" />
          </div>

          {/* Active theses */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div style={{ color: C.text, fontSize: 14, fontWeight: 700 }}>Operações ativas das teses</div>
              <Badge label="3 abertas" type="open" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
              {tesisAbertas.map((t) => <ThesisCard key={t.id} thesis={t} />)}
            </div>
          </div>

          {/* Indicador de aprendizado aplicado */}
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: "16px 20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <div style={{ color: C.text, fontSize: 14, fontWeight: 700 }}>Indicador de aprendizado aplicado</div>
                <div style={{ color: C.muted, fontSize: 11, marginTop: 2 }}>Categorias de melhoria que ja estao sendo usadas nas novas teses.</div>
              </div>
              <Badge label={`${indicadorAprendizado.categorias.length} categorias`} type="info" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div style={{ background: C.panel, borderRadius: 10, padding: "10px 12px" }}>
                <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Teses mapeadas</div>
                <div style={{ color: C.text, fontSize: 20, fontWeight: 700, fontFamily: mono }}>{indicadorAprendizado.totalTeses}</div>
              </div>
              <div style={{ background: C.panel, borderRadius: 10, padding: "10px 12px" }}>
                <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Com melhoria aplicada</div>
                <div style={{ color: C.teal, fontSize: 20, fontWeight: 700, fontFamily: mono }}>{indicadorAprendizado.tesesComAplicacao}</div>
              </div>
              <div style={{ background: C.panel, borderRadius: 10, padding: "10px 12px" }}>
                <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Taxa de adocao</div>
                <div style={{ color: C.gold, fontSize: 20, fontWeight: 700, fontFamily: mono }}>{indicadorAprendizado.taxaAplicacao}%</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {indicadorAprendizado.categorias.map((item) => (
                <div key={item.chave} style={{ background: C.panel, borderRadius: 10, padding: "10px 12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ color: C.text, fontSize: 12, fontWeight: 600 }}>{item.nome}</span>
                    <span style={{ color: C.muted, fontSize: 11, fontFamily: mono }}>{item.qtd} teses</span>
                  </div>
                  <div style={{ height: 5, borderRadius: 99, background: C.line, overflow: "hidden" }}>
                    <div style={{ width: `${Math.max(8, item.pct)}%`, height: "100%", borderRadius: 99, background: C.teal }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Teses históricas table */}
          <TabelaTeses titulo="Teses históricas (encerradas)" rows={tesesHistoricas} />

          {/* Teses pós go-live table */}
          <TabelaTeses titulo="Teses pós go-live (em aberto)" rows={tesesPosGoLive} />

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
