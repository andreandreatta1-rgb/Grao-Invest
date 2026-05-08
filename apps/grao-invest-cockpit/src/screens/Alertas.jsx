import { Badge, C, ScreenHero, alpha, mono, withAlpha } from "../components";

const todayEvents = [
  { instrument: "Cordas", type: "Stop", badge: "danger", icon: "■", title: "Stop disparado — PETR4", description: "Saída R$ 36,88 · −1,40%", color: C.coral, time: "há 2h" },
  { instrument: "Percussão", type: "Alerta", badge: "warning", icon: "⚠", title: "Concentração em MGLU3", description: "2 teses abertas — acima do limite", color: C.amber, time: "há 3h" },
  { instrument: "Sopros", type: "Sucesso", badge: "success", icon: "✓", title: "BTCUSDT validada", description: "+7,37% atingido em 2 dias", color: C.green, time: "há 6h" },
];

const weekEvents = [
  { instrument: "Metais", type: "Motor", badge: "purple", icon: "⚗", title: "Nova calibração — Cal.18", description: "Taxa de acerto: 67,52%", color: C.purple, time: "ontem" },
  { instrument: "Cordas", type: "Análise", badge: "info", icon: "◇", title: "Padrão VALE3", description: "Candidato · 82 casos", color: C.sky, time: "há 2d" },
  { instrument: "Soprano", type: "Go-live", badge: "open", icon: "◎", title: "Tese B3-001 aberta", description: "PETR4 · entrada R$ 38,28", color: C.teal, time: "há 4d" },
  { instrument: "Sopros", type: "Aprendizado", badge: "high", icon: "✦", title: "Aprendizado registrado", description: "Filtro de volume ativado", color: C.gold, time: "há 5d" },
];

const historyRows = [
  ["■ Cordas", "Stop disparado", "PETR4", "−1,40% · R$ 36,88", "há 2h"],
  ["⚠ Percussão", "Concentração", "MGLU3", "2 teses simultâneas", "há 3h"],
  ["✓ Sopros", "Tese validada", "BTCUSDT", "+7,37% · 2 dias", "há 6h"],
  ["⚗ Metais", "Calibração concluída", "Halley Cal.18", "67,52% acerto", "ontem"],
  ["◇ Cordas", "Candidato identificado", "VALE3", "82 casos históricos", "há 2d"],
  ["◎ Soprano", "Tese aberta", "PETR4", "entrada R$ 38,28", "há 4d"],
];

function ScoreEvent({ event }) {
  return (
    <article
      style={{
        background: C.panel,
        border: `1px solid ${withAlpha(event.color, alpha.border)}`,
        borderLeft: `3px solid ${event.color}`,
        borderRadius: 12,
        padding: "10px 12px",
        display: "grid",
        gridTemplateColumns: "82px minmax(0, 1fr) auto",
        gap: 12,
        alignItems: "center",
      }}
    >
      <div>
        <div style={{ color: C.muted, fontSize: 7, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{event.instrument}</div>
        <div style={{ color: event.color, fontSize: 9, fontWeight: 700, fontFamily: mono }}>{event.type}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
        <span style={{ color: event.color, fontSize: 14, fontFamily: mono, flexShrink: 0 }}>{event.icon}</span>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: event.color, fontSize: 12, fontWeight: 700, marginBottom: 2 }}>{event.title}</div>
          <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.45 }}>{event.description}</div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
        <Badge label={event.type} type={event.badge} />
        <span style={{ color: C.dim, fontSize: 9, fontFamily: mono }}>{event.time}</span>
      </div>
    </article>
  );
}

function MovementPanel({ title, subtitle, events }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 16 }}>
      <div style={{ color: C.text, fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{title}</div>
      <div style={{ color: C.muted, fontSize: 10, marginBottom: 12 }}>{subtitle}</div>
      <div style={{ display: "grid", gap: 10 }}>
        {events.map((event) => <ScoreEvent key={event.title} event={event} />)}
      </div>
    </div>
  );
}

export default function Alertas() {
  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>Partitura de eventos — cada alerta é um instrumento.</p>

      <ScreenHero
        screen="alertas"
        state="alerting"
        accent={C.sky}
        message="Há alerta crítico aberto. Isso sempre parece urgente quando está acontecendo. O plano contempla isso. Tome um chá."
        insights={[
          { label: "Hoje", value: "Eventos que pedem leitura imediata.", color: C.coral },
          { label: "Semana", value: "Calibração e observação sem pressa.", color: C.sky },
          { label: "Decisão", value: "Alerta informa; tese decide a ação.", color: C.gold },
        ]}
      />

      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: 0, right: 0, width: 230, height: 170, background: `radial-gradient(ellipse at 90% 30%, ${C.sky}14, transparent 62%)`, pointerEvents: "none" }} />
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", position: "relative", zIndex: 2 }}>
          <div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Os dois movimentos de hoje</div>
            <div style={{ color: C.muted, fontSize: 11 }}>Fortissimo pela manhã · Piano durante a semana</div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 16, position: "relative", zIndex: 2 }}>
          <MovementPanel title="Primeiro movimento — hoje" subtitle="Eventos que pedem leitura imediata" events={todayEvents} />
          <MovementPanel title="Segundo movimento — esta semana" subtitle="Eventos de calibração e observação" events={weekEvents} />
        </div>
      </section>

      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}` }}>
          <div style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>Partitura completa — histórico</div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr style={{ background: C.panel }}>
                {["Instrumento", "Evento", "Ativo", "Detalhe", "Quando"].map((h) => (
                  <th key={h} style={{ padding: "9px 12px", color: C.muted, fontWeight: 600, textAlign: "left", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: `1px solid ${C.border}`, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {historyRows.map((row) => (
                <tr key={`${row[1]}-${row[2]}`} style={{ borderBottom: `1px solid ${C.line}` }}>
                  <td style={{ padding: "10px 12px", color: C.muted, fontSize: 10 }}>{row[0]}</td>
                  <td style={{ padding: "10px 12px", color: C.text, fontWeight: 600 }}>{row[1]}</td>
                  <td style={{ padding: "10px 12px", color: C.text, fontWeight: 700 }}>{row[2]}</td>
                  <td style={{ padding: "10px 12px", color: C.muted }}>{row[3]}</td>
                  <td style={{ padding: "10px 12px", color: C.muted, fontFamily: mono, fontSize: 10 }}>{row[4]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
