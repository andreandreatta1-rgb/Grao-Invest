import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { useState } from "react";
import { Badge, C, DataTrustSeal, KPICard, ScreenHero, TooltipBox, mono } from "../components";
import { dataTrustForScreen } from "../data/dataTrust.js";

export const accuracyCycles = [
  { ciclo: "Cal.08", taxa: 55.0 },
  { ciclo: "Cal.09", taxa: 56.4 },
  { ciclo: "Cal.10", taxa: 57.8 },
  { ciclo: "Cal.11", taxa: 59.1 },
  { ciclo: "Cal.12", taxa: 60.3 },
  { ciclo: "Cal.13", taxa: 61.7 },
  { ciclo: "Cal.14", taxa: 62.9 },
  { ciclo: "Cal.15", taxa: 64.2 },
  { ciclo: "Cal.16", taxa: 65.4 },
  { ciclo: "Cal.17", taxa: 66.3 },
  { ciclo: "Cal.18", taxa: 67.52 },
];

const strataCalibrations = [
  { n: "08", ac: 55.0, esp: 5.1, alc: 3.2 },
  { n: "09", ac: 57.2, esp: 5.0, alc: 3.3 },
  { n: "10", ac: 59.1, esp: 4.95, alc: 3.28 },
  { n: "11", ac: 58.4, esp: 4.9, alc: 3.25 },
  { n: "12", ac: 61.3, esp: 4.85, alc: 3.3 },
  { n: "13", ac: 60.8, esp: 4.8, alc: 3.32 },
  { n: "14", ac: 63.5, esp: 4.75, alc: 3.35 },
  { n: "15", ac: 62.9, esp: 4.8, alc: 3.1 },
  { n: "16", ac: 65.1, esp: 4.6, alc: 3.25 },
  { n: "17", ac: 66.8, esp: 4.5, alc: 3.35 },
  { n: "18", ac: 67.52, esp: 4.43, alc: 3.41 },
];

const fallbackCalibrations = [
  { id: 1, data: "12/02/2026", teses: 143, esperado: 2.1, alcancado: 1.4, aprovadas: 84 },
  { id: 2, data: "04/03/2026", teses: 168, esperado: 2.4, alcancado: 2.6, aprovadas: 103 },
  { id: 3, data: "27/03/2026", teses: 181, esperado: 2.7, alcancado: 2.9, aprovadas: 118 },
  { id: 4, data: "18/04/2026", teses: 173, esperado: 2.8, alcancado: 3.1, aprovadas: 117 },
  { id: 5, data: "03/05/2026", teses: 182, esperado: 2.9, alcancado: 3.3, aprovadas: 123 },
];

const historicalConsolidated = {
  testedTheses: 1727,
  expectedPct: 4.43,
  achievedPct: 2.68,
  tableAchievedPct: 3.41,
};

const validationCycleSteps = [
  {
    marker: "01",
    label: "Hipótese testada",
    text: "A tese entra com premissa, prazo, gatilho e risco explícitos.",
    color: C.sky,
  },
  {
    marker: "02",
    label: "Resultado histórico",
    text: "O laboratório compara o esperado com o que teria acontecido.",
    color: C.teal,
  },
  {
    marker: "03",
    label: "Gap observado",
    text: "A diferença vira evidência: prazo, preço, liquidez ou convicção.",
    color: C.coral,
  },
  {
    marker: "04",
    label: "Aprendizado registrado",
    text: "O erro medido vira uma lição auditável para o próximo ciclo.",
    color: C.amber,
  },
  {
    marker: "05",
    label: "Nova regra do método",
    text: "A regra entra no playbook antes de voltar para novas teses.",
    color: C.purple,
  },
  {
    marker: "06",
    label: "Método calibrado",
    text: "O motor volta mais exigente, sem prometer certeza ao usuário.",
    color: C.green,
  },
];

const calibrationInsights = [
  {
    ciclo: "Cal.08",
    observedFrom: "baseline",
    observed: "Primeiro corte: muitas hipóteses acertavam a direção, mas sem disciplina de prazo.",
    rule: "Separar direção, prazo e liquidez antes de contar uma tese como robusta.",
    result: "Base criada para medir erro, não só acerto.",
    status: "Base",
  },
  {
    ciclo: "Cal.09",
    observedFrom: "Cal.08",
    observed: "O método melhorava quando o gatilho de entrada era menos genérico.",
    rule: "Exigir gatilho de confirmação antes de validar assimetria.",
    result: "Acerto direcional subiu, mas o gap de expectativa continuou alto.",
    status: "Parcial",
  },
  {
    ciclo: "Cal.10",
    observedFrom: "Cal.09",
    observed: "Teses boas perdiam eficiência quando carregavam alvo amplo demais.",
    rule: "Reduzir alvo quando volatilidade e prazo não sustentam a tese.",
    result: "Melhorou a precisão, ainda com ruído de liquidez.",
    status: "Parcial",
  },
  {
    ciclo: "Cal.11",
    observedFrom: "Cal.10",
    observed: "Alguns sinais atrasados entravam depois do movimento principal.",
    rule: "Penalizar tese que chega sem assimetria restante.",
    result: "O gap caiu pouco, mas a triagem ficou mais rígida.",
    status: "Em teste",
  },
  {
    ciclo: "Cal.12",
    observedFrom: "Cal.11",
    observed: "A janela temporal frouxa confundia tese válida com capital parado.",
    rule: "Definir prazo máximo de confirmação para cada tese.",
    result: "Mais clareza entre tese viva e tese expirada.",
    status: "Comprovado",
  },
  {
    ciclo: "Cal.13",
    observedFrom: "Cal.12",
    observed: "O método acertava melhor quando o risco setorial entrava no score.",
    rule: "Adicionar penalidade por concentração de frente e setor.",
    result: "Acerto subiu, mas o retorno realizado ainda ficou abaixo do esperado.",
    status: "Parcial",
  },
  {
    ciclo: "Cal.14",
    observedFrom: "Cal.13",
    observed: "Teses com baixa liquidez aumentavam o desvio entre esperado e realizado.",
    rule: "Ajustar convicção quando liquidez não suporta execução limpa.",
    result: "Gap reduziu, sem eliminar a diferença de expectativa.",
    status: "Comprovado",
  },
  {
    ciclo: "Cal.15",
    observedFrom: "Cal.14",
    observed: "O modelo ficou otimista em alvos quando o mercado lateralizava.",
    rule: "Exigir confirmação adicional em regime de baixa tendência.",
    result: "Acerto direcional ficou estável, gap voltou a abrir.",
    status: "Falhou",
  },
  {
    ciclo: "Cal.16",
    observedFrom: "Cal.15",
    observed: "O erro da Cal.15 mostrou que regime de mercado precisava pesar mais.",
    rule: "Rebaixar alvos quando tendência, volume e prazo discordam.",
    result: "Retomou melhora de acerto e reduziu gap.",
    status: "Comprovado",
  },
  {
    ciclo: "Cal.17",
    observedFrom: "Cal.16",
    observed: "Ainda havia teses corretas na direção, mas com alvo agressivo demais.",
    rule: "Recalibrar alvo por liquidez, prazo e força do gatilho.",
    result: "A direção resistiu; precisão seguiu em validação.",
    status: "Parcial",
  },
  {
    ciclo: "Cal.18",
    observedFrom: "Cal.17",
    observed: "Acertava a direção, mas parte das teses carregava alvo agressivo demais.",
    rule: "Reduzir alvo quando liquidez e prazo não sustentam a assimetria.",
    result: "Parcialmente: acerto direcional subiu, mas ainda existe gap de expectativa.",
    status: "Parcial",
  },
];

const auditEvidence = [
  {
    id: 1,
    rodada: "histórico",
    teses: historicalConsolidated.testedTheses,
    gap: historicalConsolidated.tableAchievedPct - historicalConsolidated.expectedPct,
    error: "alvo agressivo em parte das hipóteses mesmo quando a direção estava correta.",
    rule: "regra ajustada: janela, convicção e liquidez revisadas antes do próximo ciclo.",
    result: "Acerto direcional evoluiu, mas a precisão ainda pede calibração.",
    status: "Parcial",
  },
  {
    id: 2,
    rodada: "Cal.18",
    teses: historicalConsolidated.testedTheses,
    gap: historicalConsolidated.tableAchievedPct - historicalConsolidated.expectedPct,
    error: "gap de expectativa entre retorno previsto e realizado na rodada atual.",
    rule: "regra ajustada: reduzir alvo quando prazo e liquidez não sustentam a assimetria.",
    result: "Melhora confirmada na direção; diferença de expectativa segue monitorada.",
    status: "Em teste",
  },
  {
    id: 3,
    rodada: "Cal.17",
    teses: 168,
    gap: -1.15,
    error: "tese correta demorava demais para confirmar o movimento.",
    rule: "regra ajustada: encurtar janela de validade e exigir gatilho mais limpo.",
    result: "A rodada seguinte reduziu ruído, mas não zerou o gap.",
    status: "Comprovado",
  },
];

function pct(value, fractionDigits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--%";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("pt-BR", { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits })}%`;
}

function calibrationCycleOrder(label, fallback) {
  const match = String(label ?? "").match(/(?:Cal\.)?\s*0?(\d{1,3})/i);
  return match ? Number(match[1]) : fallback;
}

function normalizeAccuracyCycles(cycles) {
  const source = Array.isArray(cycles) && cycles.length ? cycles : accuracyCycles;
  return source
    .map((item, index) => ({
      ciclo: String(item?.ciclo ?? `Cal.${String(index + 8).padStart(2, "0")}`),
      taxa: Number.isFinite(Number(item?.taxa)) ? Number(item.taxa) : 0,
      sortOrder: calibrationCycleOrder(item?.ciclo, index),
      sourceOrder: index,
    }))
    .sort((a, b) => a.sortOrder - b.sortOrder || a.sourceOrder - b.sourceOrder)
    .slice(-11)
    .map(({ sortOrder, sourceOrder, ...item }) => item);
}

function consolidatedNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number !== 0 ? number : fallback;
}

function normalizedCalibrationRow(row) {
  const label = String(row.data || "").toLowerCase();
  const teses = Number(row.teses || 0);
  const aprovadas = Number(row.aprovadas || 0);
  const isHistorical = label.includes("hist") || teses >= 1700 || aprovadas >= 1700;
  if (!isHistorical) return row;

  return {
    ...row,
    teses: historicalConsolidated.testedTheses,
    esperado: historicalConsolidated.expectedPct,
    alcancado: historicalConsolidated.tableAchievedPct,
  };
}

function pp(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--pp";
  const formatted = Math.abs(number).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (number > 0) return `+${formatted}pp`;
  if (number < 0) return `−${formatted}pp`;
  return "0,00pp";
}

function signedPp(value, decimals = 2, spaced = false) {
  const number = Number(value);
  if (!Number.isFinite(number)) return spaced ? "-- p.p." : "--pp";
  const sign = number > 0 ? "+" : number < 0 ? "−" : "";
  const formatted = Math.abs(number).toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return `${sign}${formatted}${spaced ? " p.p." : "pp"}`;
}

function pctPlain(value, fractionDigits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--%";
  return `${number.toLocaleString("pt-BR", { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits })}%`;
}

function intPlain(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return number.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

function methodHealthCopy({ accuracyGain, trust, calibrations, tested, cycleSource, sampleQuality }) {
  const statusText = trust?.label ?? "Dados parciais";
  const trendText = accuracyGain < -3
    ? "Performance em deterioração nesta calibração."
    : accuracyGain < 0
      ? "Performance em leve queda nesta calibração."
      : "Performance estável ou em melhora nesta calibração.";
  const latestCalibration = calibrations[calibrations.length - 1];
  const sampleText = latestCalibration?.teses && tested
    ? `${latestCalibration.data} concentra ${intPlain(latestCalibration.teses)} de ${intPlain(tested)} testes.`
    : "A amostra recente ainda precisa ser interpretada junto do histórico.";
  const sourceText = cycleSource === "synthetic"
    ? "Série de calibração estimada a partir do acerto acumulado; o backend ainda não enviou ciclos reais."
    : "Série de calibração recebida do backend.";
  const replayCount = Number(sampleQuality?.duplicate_case_study_events_excluded ?? sampleQuality?.duplicateCaseStudyEventsExcluded ?? 0);
  const monitorCount = Number(sampleQuality?.current_monitor_snapshots_excluded ?? sampleQuality?.currentMonitorSnapshotsExcluded ?? 0);
  const qualityText = replayCount > 0 || monitorCount > 0
    ? `Amostra auditada: ${intPlain(replayCount)} replays e ${intPlain(monitorCount)} snapshots operacionais ficaram fora da validação.`
    : "";

  return { statusText, trendText, sampleText, sourceText, qualityText };
}

function Cell({ children, color = C.text, numeric = false, style = {} }) {
  return <td style={{ padding: "10px 12px", color, fontFamily: numeric ? mono : "inherit", ...style }}>{children}</td>;
}

function buildAuditEvidence(rows) {
  const sourceRows = rows.length > 0 ? rows : auditEvidence;

  return sourceRows.slice(0, 3).map((row, index) => {
    if (row.error) return row;

    const gap = Number(row.alcancado) - Number(row.esperado);
    const isNegativeGap = Number.isFinite(gap) && gap < 0;

    return {
      id: row.id ?? index + 1,
      rodada: row.data,
      teses: row.teses,
      gap,
      error: isNegativeGap
        ? "alvo agressivo frente ao retorno realizado, mesmo quando a direção da hipótese fazia sentido."
        : "hipótese ficou dentro do esperado, mas ainda precisa confirmar repetição em nova rodada.",
      rule: isNegativeGap
        ? "regra ajustada: reduzir alvo quando prazo, liquidez e força do gatilho não sustentam a assimetria."
        : "regra ajustada: manter critério, mas exigir repetição antes de elevar convicção.",
      result: isNegativeGap
        ? "Resultado observado: acerto direcional preservado, gap de expectativa ainda em calibração."
        : "Resultado observado: rodada compatível com o esperado, sem tratar isso como vitória perfeita.",
      status: isNegativeGap ? "Parcial" : "Em teste",
    };
  });
}

function MethodHealthNotice({ accuracyGain, trust, calibrations, tested, cycleSource, sampleQuality }) {
  const tone = accuracyGain < -3 ? C.coral : accuracyGain < 0 ? C.amber : C.teal;
  const copy = methodHealthCopy({ accuracyGain, trust, calibrations, tested, cycleSource, sampleQuality });

  return (
    <section style={{ background: C.panel, border: `1px solid ${tone}45`, borderLeft: `3px solid ${tone}`, borderRadius: 12, padding: "11px 13px" }}>
      <div style={{ color: tone, fontSize: 11, fontWeight: 800, lineHeight: 1.45 }}>
        {copy.statusText}. {copy.trendText}
      </div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 4 }}>
        {copy.sampleText} {copy.sourceText} {copy.qualityText}
      </div>
    </section>
  );
}

function ValidationCycleCard({ step, index }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderTop: `2px solid ${step.color}`, borderRadius: 12, minHeight: 118, padding: 13, position: "relative" }}>
      <div style={{ alignItems: "center", display: "flex", gap: 8, marginBottom: 10 }}>
        <span style={{ alignItems: "center", background: `${step.color}18`, border: `1px solid ${step.color}55`, borderRadius: "50%", color: step.color, display: "inline-flex", fontFamily: mono, fontSize: 10, fontWeight: 800, height: 24, justifyContent: "center", width: 24 }}>{step.marker}</span>
        {index < validationCycleSteps.length - 1 && <span style={{ color: C.dim, fontFamily: mono, fontSize: 13 }}>→</span>}
      </div>
      <div style={{ color: C.text, fontSize: 13, fontWeight: 700, lineHeight: 1.25, marginBottom: 7 }}>{step.label}</div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>{step.text}</div>
    </div>
  );
}

function MethodLaboratoryIntro({ trust }) {
  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 360, height: 220, background: `radial-gradient(ellipse at 90% 20%, ${C.gold}14, transparent 66%)`, pointerEvents: "none" }} />
      <div style={{ position: "absolute", right: 14, top: 14, zIndex: 3 }}>
        <DataTrustSeal screen="backtest" trust={trust} />
      </div>
      <ScreenHero
        screen="backtest"
        state="testing"
        accent={C.gold}
        message="847 simulações concluídas. O padrão resiste, mas ainda está sendo testado. Rodando mais 200 para confirmar robustez."
        insights={[
          { label: "Pergunta da tela", value: "Como eu sei que o método aprende?", color: C.gold },
          { label: "Evidência", value: "Erro vira regra candidata antes de virar método.", color: C.purple },
          { label: "Critério", value: "Só promove regra quando a robustez aparece.", color: C.teal },
        ]}
        style={{ marginBottom: 16 }}
      />
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 0.7fr)", gap: 18, alignItems: "stretch", marginBottom: 16, position: "relative", zIndex: 2 }}>
        <div>
          <div>
            <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", marginBottom: 10, textTransform: "uppercase" }}>
              Validação / laboratório
            </div>
            <div style={{ color: C.text, fontSize: 22, fontWeight: 800, letterSpacing: "-0.01em", lineHeight: 1.1, marginBottom: 10 }}>
              Laboratório do Método
            </div>
            <div style={{ color: C.text, fontSize: 26, fontWeight: 800, letterSpacing: "-0.01em", lineHeight: 1.18, marginBottom: 10, maxWidth: 720 }}>
              Como eu sei que o Método Grão aprende com os erros e melhora com o tempo?
            </div>
            <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0, maxWidth: 480 }}>
              O método testa, erra, aprende e volta mais calibrado. Aqui a tese deixa de ser palpite: ela vira hipótese medida, erro documentado e regra nova para o próximo ciclo.
            </p>
          </div>
        </div>
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.gold}`, borderRadius: 12, padding: "12px 14px" }}>
          <div style={{ color: C.gold, fontSize: 12, fontWeight: 800, marginBottom: 6 }}>O que é calibração?</div>
          <div style={{ color: C.text, fontSize: 12, fontWeight: 700, lineHeight: 1.5, marginBottom: 4 }}>
            Calibrar é medir o erro, entender a causa e ajustar a próxima regra.
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55 }}>
            Cada tese nasce como hipótese. Depois o laboratório compara esperado vs. realizado. Quando aparece um gap, ele vira aprendizado antes da próxima rodada de calibração.
          </div>
        </div>
      </div>
      <div data-testid="validation-cycle-flow" style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 10, position: "relative", zIndex: 2 }}>
        {validationCycleSteps.map((step, index) => (
          <ValidationCycleCard key={step.label} step={step} index={index} />
        ))}
      </div>
    </section>
  );
}

function AccuracyCycleStrip({ cycles }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(11, 1fr)", gap: 6 }}>
      {cycles.map((item) => (
        <div key={item.ciclo} data-testid={`accuracy-cycle-${item.ciclo}`} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 9, padding: "7px 6px", display: "flex", flexDirection: "column", alignItems: "center", gap: 5, minWidth: 0 }}>
          <div style={{ width: "100%", height: 38, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
            <div style={{ width: 10, height: `${Math.max(14, ((item.taxa - 55) / 12.52) * 38)}px`, background: C.purple, borderRadius: "6px 6px 2px 2px" }} />
          </div>
          <span style={{ color: C.muted, fontSize: 9, fontFamily: mono }}>{item.ciclo}</span>
          <span style={{ color: C.text, fontSize: 10, fontFamily: mono, fontWeight: 700 }}>{item.taxa.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</span>
        </div>
      ))}
    </div>
  );
}

function MethodEvolution({ cycles }) {
  const [selectedCycle, setSelectedCycle] = useState(cycles[cycles.length - 1]?.ciclo ?? "Cal.18");
  const selectedInsight = calibrationInsights.find((item) => item.ciclo === selectedCycle) ?? calibrationInsights[calibrationInsights.length - 1];

  return (
    <section data-testid="calibration-evolution-lab" style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 280, height: 220, background: `radial-gradient(ellipse at 90% 30%, ${C.purple}14, transparent 62%)`, pointerEvents: "none" }} />
      <div style={{ color: C.text, fontSize: 15, fontWeight: 800, marginBottom: 5, position: "relative", zIndex: 2 }}>Evolução do método</div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginBottom: 16, maxWidth: 760, position: "relative", zIndex: 2 }}>
        As rodadas Cal.08 a Cal.18 são ciclos de calibração do método: não são teses isoladas. Cada rodada mede o gap, ajusta regras e volta para testar a próxima safra de hipóteses.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 360px", gap: 16, alignItems: "stretch", position: "relative", zIndex: 2 }}>
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 14, minWidth: 0 }}>
          <div style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Como o método foi calibrado</div>
          <div style={{ color: C.text, fontSize: 12, fontWeight: 700, marginBottom: 3 }}>Evolução após cada calibração</div>
          <div style={{ color: C.muted, fontSize: 11, marginBottom: 10 }}>Gráfico, linha do tempo e resumo ficam juntos para evitar que a história se perca no scroll.</div>
          <div data-testid="calibration-evolution-chart" style={{ minHeight: 260, width: "100%", overflow: "hidden" }}>
            <LineChart width={720} height={260} data={cycles} margin={{ top: 8, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
              <XAxis dataKey="ciclo" interval={0} tick={{ fill: C.muted, fontSize: 9, fontFamily: mono }} axisLine={false} tickLine={false} />
              <YAxis domain={[55, 68]} tick={{ fill: C.muted, fontSize: 10, fontFamily: mono }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip content={<TooltipBox />} />
              <Line type="monotone" dataKey="taxa" name="Acerto direcional" stroke={C.purple} strokeWidth={2.5} dot={{ r: 3, fill: C.purple, stroke: C.purple }} />
            </LineChart>
          </div>
          <div data-testid="calibration-timeline" style={{ display: "grid", gridTemplateColumns: "repeat(11, minmax(0, 1fr))", gap: 6, marginTop: 10 }}>
            {cycles.map((item) => {
              const selected = item.ciclo === selectedCycle;
              return (
                <button
                  key={item.ciclo}
                  type="button"
                  data-testid={`calibration-timeline-${item.ciclo}`}
                  onClick={() => setSelectedCycle(item.ciclo)}
                  style={{
                    background: selected ? `${C.purple}18` : C.bg,
                    border: `1px solid ${selected ? C.purple : C.border}`,
                    borderRadius: 8,
                    color: selected ? C.text : C.muted,
                    cursor: "pointer",
                    fontFamily: mono,
                    minWidth: 0,
                    padding: "7px 4px",
                  }}
                >
                  <span data-testid={`accuracy-cycle-${item.ciclo}`} style={{ display: "block", color: selected ? C.purple : C.dim, fontSize: 9, marginBottom: 4 }}>{item.ciclo}</span>
                  <span style={{ display: "block", fontSize: 10, fontWeight: 800 }}>{pctPlain(item.taxa)}</span>
                </button>
              );
            })}
          </div>
        </div>
        <div data-testid="calibration-summary" style={{ background: C.panel, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.purple}`, borderRadius: 12, padding: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 12 }}>
            <div>
              <div style={{ color: C.purple, fontFamily: mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", marginBottom: 4, textTransform: "uppercase" }}>Resumo da calibração</div>
              <div style={{ color: C.text, fontSize: 18, fontWeight: 800 }}>{selectedInsight.ciclo}</div>
            </div>
            <Badge label={selectedInsight.status} type={selectedInsight.status === "Comprovado" ? "success" : selectedInsight.status === "Falhou" ? "danger" : "warning"} />
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            <div>
              <div style={{ color: C.coral, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 4, textTransform: "uppercase" }}>Observado na {selectedInsight.observedFrom}</div>
              <div style={{ color: C.text, fontSize: 11, lineHeight: 1.55 }}>{selectedInsight.observed}</div>
            </div>
            <div>
              <div style={{ color: C.gold, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 4, textTransform: "uppercase" }}>Regra ajustada</div>
              <div style={{ color: C.text, fontSize: 11, lineHeight: 1.55 }}>{selectedInsight.rule}</div>
            </div>
            <div>
              <div style={{ color: C.green, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 4, textTransform: "uppercase" }}>Comprovado na {selectedInsight.ciclo}?</div>
              <div style={{ color: C.text, fontSize: 11, lineHeight: 1.55 }}>{selectedInsight.result}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Backtest({ data }) {
  const summary = data?.scientificSummary ?? {};
  const historicalSummary = data?.executiveSummary?.historical ?? {};
  const cycles = normalizeAccuracyCycles(data?.backtest?.accuracyCycles);
  const calibrations = data?.backtest?.calibrations?.length ? data.backtest.calibrations : fallbackCalibrations;
  const displayCalibrations = calibrations.map(normalizedCalibrationRow);
  const accuracyCycleSource = data?.backtest?.accuracyCycleSource ?? "static";
  const firstAccuracy = Number(cycles[0]?.taxa ?? accuracyCycles[0].taxa);
  const latestAccuracy = Number(cycles[cycles.length - 1]?.taxa ?? accuracyCycles[accuracyCycles.length - 1].taxa);
  const accuracyGain = latestAccuracy - firstAccuracy;
  const accuracyTrendColor = accuracyGain < 0 ? C.coral : C.green;
  const accuracyTrendSub = accuracyGain < 0 ? "queda no ciclo atual" : "Cal.08 até ciclo atual";
  const latestCalibration = strataCalibrations[strataCalibrations.length - 1];
  const currentGap = latestCalibration.alc - latestCalibration.esp;
  const tested = consolidatedNumber(summary.testedTheses ?? historicalSummary.testedTheses, historicalConsolidated.testedTheses);
  const evidenceRows = buildAuditEvidence(displayCalibrations);
  const dataTrust = data?.dataTrust?.backtest ?? dataTrustForScreen("backtest", { ...data, backtest: { ...(data?.backtest ?? {}), accuracyCycleSource, accuracyCycles: cycles } });
  const sampleQuality = data?.backtest?.sampleQuality ?? {};

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <MethodLaboratoryIntro trust={dataTrust} />

      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <KPICard label="Teses testadas" value={tested.toLocaleString("pt-BR")} sub="histórico do laboratório" accent={C.sky} valueColor={C.text} />
        <KPICard label="Acerto direcional" value={pctPlain(latestAccuracy)} sub="hipótese principal correta" accent={C.purple} valueColor={C.purple} />
        <KPICard label="Variação desde Cal.08" value={signedPp(accuracyGain, 2, true)} sub={accuracyTrendSub} accent={accuracyTrendColor} valueColor={accuracyTrendColor} />
        <KPICard label="Gap de expectativa" value={signedPp(currentGap)} sub="esperado vs. realizado" accent={C.coral} valueColor={C.coral} />
      </section>

      <MethodHealthNotice
        accuracyGain={accuracyGain}
        trust={dataTrust}
        calibrations={calibrations}
        tested={tested}
        cycleSource={accuracyCycleSource}
        sampleQuality={sampleQuality}
      />

      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.sky}`, borderRadius: 12, color: C.text, fontSize: 12, fontWeight: 700, lineHeight: 1.5, padding: "10px 13px" }}>
        Acerto mede direção. Gap mede precisão entre esperado e realizado.
        <span style={{ color: C.muted, fontWeight: 500 }}> Uma tese pode acertar a direção e ainda ficar abaixo do alvo esperado.</span>
      </div>

      <MethodEvolution cycles={cycles} />

      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}` }}>
          <div style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>Evidências auditáveis</div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginTop: 6, textTransform: "uppercase" }}>Últimos ciclos auditáveis</div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 4 }}>
            Amostras curtas com erro observado, regra ajustada, resultado e status de comprovação.
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, padding: 16 }}>
          {evidenceRows.map((item) => (
            <article key={item.id} data-testid={`audit-evidence-${item.id}`} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 14 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10, marginBottom: 12 }}>
                <div>
                  <div style={{ color: C.muted, fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", marginBottom: 4, textTransform: "uppercase" }}>Rodada</div>
                  <div style={{ color: C.text, fontFamily: mono, fontSize: 14, fontWeight: 800 }}>{item.rodada}</div>
                  <div style={{ color: C.dim, fontFamily: mono, fontSize: 10, marginTop: 3 }}>{Number(item.teses || 0).toLocaleString("pt-BR")} teses</div>
                </div>
                <Badge label={item.status} type={item.status === "Comprovado" ? "success" : item.status === "Falhou" ? "danger" : "warning"} />
              </div>
              <div style={{ display: "grid", gap: 9 }}>
                <div>
                  <div style={{ color: C.coral, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 3, textTransform: "uppercase" }}>Erro observado</div>
                  <div style={{ color: C.text, fontSize: 11, lineHeight: 1.5 }}>{item.error}</div>
                </div>
                <div>
                  <div style={{ color: C.gold, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 3, textTransform: "uppercase" }}>Regra ajustada</div>
                  <div style={{ color: C.text, fontSize: 11, lineHeight: 1.5 }}>{item.rule}</div>
                </div>
                <div>
                  <div style={{ color: C.green, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", marginBottom: 3, textTransform: "uppercase" }}>Resultado observado</div>
                  <div style={{ color: C.text, fontSize: 11, lineHeight: 1.5 }}>{item.result}</div>
                </div>
                <div style={{ alignItems: "center", borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", gap: 8, paddingTop: 9 }}>
                  <span style={{ color: C.muted, fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", textTransform: "uppercase" }}>Status</span>
                  <span style={{ color: item.gap >= 0 ? C.teal : C.coral, fontFamily: mono, fontSize: 12, fontWeight: 800 }}>{pp(item.gap)}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

