import { useState, useEffect } from "react";

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
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>{titulo}</div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr style={{ background: C.panel }}>
              {["#", "Ação", "Direção", "Esperado", "Estrutura", "Entrada", "Saída se", "Desfecho", "Dias", "Status", "Resultado"].map((h) => (
                <th key={h} style={{ padding: "9px 12px", color: C.muted, fontWeight: 600, textAlign: "left", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: `1px solid ${C.border}`, whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const resColor = r.resultado > 0 ? C.teal : r.resultado < 0 ? C.coral : C.muted;
              return (
                <tr key={i} style={{ borderBottom: `1px solid ${C.line}`, transition: "background 0.1s" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = C.hover}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
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
                </tr>
              );
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
  { id: 159, ativo: "PETR4", direcao: "Alta", esperado: "+4,82%", estrutura: "Bull Call Spread | ganho 5,40% | perda 2,20%", entrada: "40,53", saida: "≥43,37 / ≤38,83", desfecho: "Tempo", dias: 13, status: "Fechada", resultado: 3.14 },
];

const tesesPosGoLive = [
  { id: 160, ativo: "PETR4", direcao: "Neutro", esperado: "+0,82%", estrutura: "Iron Condor | ganho 2,40% | perda 3,80%", entrada: "41,03", saida: "≥41,03 / ≤40,41", desfecho: "Alerta de stop", dias: 0, status: "Aberta", resultado: -3.88 },
  { id: 161, ativo: "MGLU3", direcao: "Alta", esperado: "+2,76%", estrutura: "Bull Call Spread | ganho 5,40% | perda 2,20%", entrada: "9,39", saida: "≥9,99 / ≤9,03", desfecho: "Em monitoramento", dias: 0, status: "Aberta", resultado: -0.36 },
  { id: 162, ativo: "MGLU3", direcao: "Alta", esperado: "+3,01%", estrutura: "Bull Call Spread | ganho 5,40% | perda 2,20%", entrada: "9,25", saida: "≥9,90 / ≤8,86", desfecho: "Em monitoramento", dias: 0, status: "Aberta", resultado: 0.83 },
];

// ── Main ──────────────────────────────────────────────────────────────────────

export default function GraoDashboard() {
  const [activeNav, setActiveNav] = useState("dashboard");
  const [now, setNow] = useState("");

  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap";
    document.head.appendChild(link);
    const tick = () => setNow(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    tick();
    const t = setInterval(tick, 1000);
    return () => { clearInterval(t); link.remove(); };
  }, []);

  return (
    <div style={{
      display: "flex", background: C.bg, minHeight: 640,
      fontFamily: "Sora, system-ui, sans-serif", color: C.text,
      borderRadius: 18, overflow: "hidden", border: `1px solid ${C.border}`,
    }}>
      <Sidebar active={activeNav} setActive={setActiveNav} />

      {/* Main */}
      <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>

        {/* Topbar */}
        <div style={{ borderBottom: `1px solid ${C.border}`, padding: "14px 28px", display: "flex", justifyContent: "space-between", alignItems: "center", background: C.panel, flexShrink: 0 }}>
          <div>
            <div style={{ color: C.text, fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em" }}>Dashboard</div>
            <div style={{ color: C.muted, fontSize: 11, marginTop: 1 }}>Visão consolidada da simulação, risco e trilha operacional</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: C.amber + "18", border: `1px solid ${C.amber}35`, borderRadius: 8, padding: "5px 10px" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.amber, display: "inline-block", boxShadow: `0 0 8px ${C.amber}` }} />
              <span style={{ color: C.amber, fontSize: 11, fontWeight: 600 }}>Feed sem telemetria</span>
            </div>
            <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, padding: "5px 12px" }}>
              <span style={{ color: C.muted, fontSize: 11, fontFamily: mono }}>01/05 · {now}</span>
            </div>
            <button style={{ background: C.gold, color: "#000", border: "none", borderRadius: 9, padding: "7px 16px", fontSize: 12, fontWeight: 700, cursor: "pointer", letterSpacing: "0.02em" }}>
              Atualizar ↺
            </button>
          </div>
        </div>

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

          {/* Exercício histórico + pós go-live */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <TabelaExercicio
              titulo="Exercício histórico"
              periodo="até 2026-04-27 · base histórica global — case studies consolidados"
              teses={97} esperado="4,43" alcancado="3,41" aprovadas={96}
            />
            <TabelaExercicio
              titulo="Exercício pós go-live"
              periodo="desde 2026-04-27 · simulação atual — teses monitoradas"
              teses={3} esperado="2,20" alcancado="-1,11" aprovadas={0}
            />
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
