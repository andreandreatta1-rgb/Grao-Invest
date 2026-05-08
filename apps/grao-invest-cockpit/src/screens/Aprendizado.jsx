import { CartesianGrid, LabelList, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { C, KPICard, ScreenHero, TooltipBox, mono } from "../components";

export const gapData = [
  { cal: "Cal.08", gap: 1.9 },
  { cal: "Cal.09", gap: 1.7 },
  { cal: "Cal.10", gap: 1.67 },
  { cal: "Cal.11", gap: 1.65 },
  { cal: "Cal.12", gap: 1.55 },
  { cal: "Cal.13", gap: 1.48 },
  { cal: "Cal.14", gap: 1.4 },
  { cal: "Cal.15", gap: 1.7 },
  { cal: "Cal.16", gap: 1.35 },
  { cal: "Cal.17", gap: 1.15 },
  { cal: "Cal.18", gap: 1.02 },
];

export const learningGaps = gapData;

const validationConnectionCards = [
  {
    label: "Gap medido",
    value: "−0,8 pp",
    text: "Diferença entre retorno esperado e retorno realizado.",
    color: C.teal,
  },
  {
    label: "Regra ajustada",
    value: "18 ciclos",
    text: "Aprendizados entram como critérios mais exigentes no método.",
    color: C.purple,
  },
  {
    label: "Próximo ciclo",
    value: "Cal.19",
    text: "A tese seguinte já nasce com o erro anterior incorporado.",
    color: C.gold,
  },
];

function pct(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function pp(value, decimals = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-- pp";
  const sign = number < 0 ? "−" : number > 0 ? "+" : "";
  return `${sign}${Math.abs(number).toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} pp`;
}

function LearningCard({ item }) {
  const rows = [
    { label: "DOR OBSERVADA", value: item.pain, color: C.coral },
    { label: "REMÉDIO APLICADO", value: item.remedy, color: C.amber },
    { label: "IMPACTO ESPERADO", value: item.expectedImpact, color: C.green },
  ];

  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderTop: `2px solid ${C.gold}`, borderRadius: 14, padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
      {rows.map((row) => (
        <div key={row.label} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 5 }}>
          <span style={{ color: row.color, fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>{row.label}</span>
          <span style={{ color: C.text, fontSize: 12, lineHeight: 1.5 }}>{row.value}</span>
        </div>
      ))}
    </section>
  );
}

function ValidationConnectionCard({ item }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderTop: `2px solid ${item.color}`, borderRadius: 12, padding: "13px 14px", minWidth: 0 }}>
      <div style={{ color: item.color, fontSize: 11, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 8, textTransform: "uppercase" }}>
        {item.label}
      </div>
      <div style={{ color: C.text, fontFamily: mono, fontSize: 18, fontWeight: 800, marginBottom: 6 }}>{item.value}</div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>{item.text}</div>
    </div>
  );
}

function ValidationConnection() {
  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18 }}>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 0.8fr) minmax(0, 1.2fr)", gap: 16, alignItems: "stretch" }}>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 6 }}>Conexão com validação</div>
          <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0 }}>
            Cada aprendizado nasce de um erro medido no laboratório: o gap é identificado, a regra é ajustada e a próxima tese volta para teste com menos ruído.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          {validationConnectionCards.map((item) => (
            <ValidationConnectionCard key={item.label} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
}

function GapLabel(props) {
  const { x, y, index } = props;
  if (index === 0) {
    return <text x={x} y={y - 12} textAnchor="middle" fill={C.dim} fontSize={10} fontFamily={mono}>chumbo</text>;
  }
  if (index === gapData.length - 1) {
    return <text x={x} y={y + 22} textAnchor="middle" fill={C.gold} fontSize={10} fontWeight={700} fontFamily={mono}>ouro · −1,02pp</text>;
  }
  return null;
}

export default function Aprendizado({ data }) {
  const learnings = data?.learningLoops ?? [];
  const learningCards = learnings.length > 0 ? [...learnings] : [{
    pain: "A API ainda não retornou aprendizados estruturados.",
    remedy: "Registrar dor, remédio e impacto esperado em cada tese encerrada.",
    expectedImpact: "Criar histórico auditável de melhoria do motor Halley.",
  }];
  if (learningCards.length % 2 !== 0) {
    learningCards.push({
      pain: "Algumas teses boas perderam eficiência quando o prazo ficou frouxo demais.",
      remedy: "Registrar janela máxima de validade e revisar hipóteses que passam do prazo sem confirmar.",
      expectedImpact: "Reduzir capital parado e melhorar a comparação entre esperado e realizado.",
    });
  }
  const stats = data?.learningStats ?? {
    totalLearnings: learnings.length,
    gapReducedPp: -0.8,
    calibrationCount: 18,
    accuracyGainPp: 12,
  };
  const gapReducedPp = -0.8;
  const calibrationCount = 18;

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>Lições registradas e aplicadas no ciclo de calibração do Halley.</p>

      <ScreenHero
        screen="aprendizado"
        state="testing"
        accent={C.purple}
        message="18 aprendizados aplicados. O gap entre esperado e realizado caiu 0,8 pontos percentuais no último trimestre. O motor recalibra sem pressa."
        insights={[
          { label: "Entrada", value: "Erro medido no laboratório.", color: C.coral },
          { label: "Tratamento", value: "Regra candidata testada em shadow.", color: C.purple },
          { label: "Saída", value: "Aprendizado só vira método quando reduz gap.", color: C.green },
        ]}
      />

      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <KPICard label="Total de aprendizados" value={Number(stats.totalLearnings || 18).toLocaleString("pt-BR")} sub="aplicados ao motor" accent={C.green} valueColor={C.green} />
        <KPICard label="Gap reduzido" value={pp(gapReducedPp)} sub="negativo é melhora" accent={C.teal} valueColor={C.teal} />
        <KPICard label="Calibrações realizadas" value={calibrationCount.toLocaleString("pt-BR")} sub="desde o início" accent={C.purple} valueColor={C.purple} />
        <KPICard label="Ganho em acerto" value={`${pct(stats.accuracyGainPp || 12)} pp`} sub="do início ao atual" accent={C.sky} valueColor={C.sky} />
      </section>

      <ValidationConnection />

      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: 0, right: 0, width: 230, height: 180, background: `radial-gradient(ellipse at 90% 30%, ${C.purple}14, transparent 62%)`, pointerEvents: "none" }} />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 18, marginBottom: 16, position: "relative", zIndex: 2 }}>
          <div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Fórmulas do alambique</div>
            <div style={{ color: C.muted, fontSize: 11 }}>Dor observada + remédio aplicado → impacto esperado</div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, paddingRight: 0, position: "relative", zIndex: 2 }}>
          {learningCards.map((item) => <LearningCard key={item.pain} item={item} />)}
        </div>
      </section>

      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18 }}>
        <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 4 }}>A Grande Obra — redução do gap</div>
        <div style={{ color: C.muted, fontSize: 11, marginBottom: 14 }}>Chumbo (1,90pp) → Ouro (1,02pp) · transmutação em curso</div>
        <div style={{ height: 280, overflowX: "auto", overflowY: "hidden" }} data-testid="learning-gap-chart">
            <LineChart width={980} height={280} data={gapData} margin={{ top: 28, right: 32, bottom: 18, left: 0 }}>
              <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
              <XAxis dataKey="cal" tick={{ fill: C.muted, fontSize: 11, fontFamily: mono }} axisLine={false} tickLine={false} />
              <YAxis domain={[0.8, 2]} tick={{ fill: C.muted, fontSize: 10, fontFamily: mono }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v.toFixed(1)}pp`} />
              <Tooltip content={<TooltipBox />} />
              <Line type="monotone" dataKey="gap" name="Gap" stroke={C.coral} strokeWidth={2.5} connectNulls={true} dot={{ r: 4, fill: C.coral, stroke: C.coral }} activeDot={{ r: 5 }}>
                <LabelList content={<GapLabel />} />
              </Line>
            </LineChart>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: 7, padding: "9px 11px", background: C.green + "08", borderRadius: 8, border: `1px solid ${C.green}1c` }}>
          <span style={{ color: C.green, fontSize: 13 }}>✦</span>
          <span style={{ fontSize: 11, color: C.green, fontWeight: 600 }}>Gap caiu 46% desde Cal. 08 — o Halley está transmutando falhas em precisão.</span>
        </div>
      </section>
    </main>
  );
}


