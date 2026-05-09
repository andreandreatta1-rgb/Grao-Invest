import { useEffect, useMemo, useState } from "react";
import { Badge, C, DataTrustSeal, KPICard, PatrickJane, alpha, mono, withAlpha } from "../components";
import { resolveRealEstatePending, saveRealEstateVisitEvidence } from "../data/cockpitHalleyApi.js";
import { dataTrustForScreen } from "../data/dataTrust.js";

const statusFilters = [
  { label: "Go-live", type: "open" },
  { label: "Histórica", type: "closed" },
  { label: "Em análise", type: "neutral" },
];

const frontFilters = ["B3", "Cripto", "Imóveis"];

const historicalFallback = [
  { id: "H-1719", ativo: "PETR4", frente: "B3", direcao: "Alta", esperado: 4.82, estrutura: "Compra estruturada com alvo e stop", entrada: 39.92, saida: "alvo R$ 43,37 / stop R$ 38,83", desfecho: "Tempo", dias: 13, status: "Histórica", resultado: 3.14, hipotese: "A hipótese sugeria continuidade de alta após suporte respeitado e volume acima da média.", aprendizado: "Exigir confirmação de volume no fechamento antes de promover a tese para go-live." },
  { id: "H-1720", ativo: "VALE3", frente: "B3", direcao: "Alta", esperado: 3.2, estrutura: "Compra com proteção por stop técnico", entrada: 70.1, saida: "alvo R$ 72,34 / stop R$ 68,75", desfecho: "Validada", dias: 7, status: "Histórica", resultado: 3.38, hipotese: "O ciclo apontava retomada após compressão de volatilidade e reação em suporte histórico.", aprendizado: "Quando volatilidade comprime e volume confirma, reduzir prazo melhora a aderência do alvo." },
  { id: "H-1721", ativo: "MGLU3", frente: "B3", direcao: "Baixa", esperado: 5.44, estrutura: "Venda protegida com stop de rompimento", entrada: 9.72, saida: "alvo R$ 9,19 / stop R$ 10,05", desfecho: "Stop", dias: 4, status: "Histórica", resultado: -1.7, hipotese: "A hipótese sugeria perda de faixa após falha de rompimento, mas o volume comprador voltou cedo.", aprendizado: "Evitar tese de baixa quando o ativo recupera a faixa no mesmo pregão com volume crescente." },
  { id: "H-1722", ativo: "BTCUSDT", frente: "Cripto", direcao: "Alta", esperado: 7.37, estrutura: "Compra com alvo parcial e stop fixo", entrada: 62400, saida: "alvo R$ 67.000 / stop R$ 60.400", desfecho: "Validada", dias: 2, status: "Histórica", resultado: 7.37, hipotese: "O padrão de força apareceu após recuperação rápida e sustentação acima da média curta.", aprendizado: "Em cripto, alvo parcial reduz ruído quando o movimento ocorre rápido demais." },
  { id: "H-1723", ativo: "Galpão Campinas", frente: "Imóveis", direcao: "Encerrada", esperado: 7.06, estrutura: "Tese imobiliária com margem de segurança", entrada: 850000, saida: "alvo R$ 910K / piso R$ 820K", desfecho: "Observando", dias: 18, status: "Histórica", resultado: 7.06, resultadoTipo: "estimate", isOpen: false, hipotese: "O preço indicava desconto frente a comparáveis e liquidez regional consistente.", aprendizado: "Separar desconto real de desconto por liquidez: imóvel precisa de gatilho de saída mais longo." },
];

function money(value) {
  if (value === null || value === undefined || value === "") return "R$ --";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (number >= 1000000) return `R$ ${(number / 1000000).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M`;
  if (number >= 100000) return `R$ ${(number / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}K`;
  return `R$ ${number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function pct(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--%";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function statusType(status) {
  if (status === "Go-live") return "open";
  if (status === "Histórica") return "closed";
  return "neutral";
}

function directionType(direction) {
  if (direction === "Baixa") return "bear";
  if (direction === "Revisar") return "warning";
  if (direction === "Descartada") return "danger";
  if (direction === "Encerrada") return "closed";
  if (direction === "Neutra") return "info";
  return "bull";
}

function isOpenThesis(status) {
  return status === "Go-live" || status === "Em análise";
}

function realEstateLabel(row) {
  if (row.front !== "Imóveis") return row.direction;
  const normalizedStatus = String(row.status || row.statusGroup || "").toLowerCase();
  if (row.isOpen === false || row.statusGroup === "Histórica") {
    return normalizedStatus.includes("descart") || normalizedStatus.includes("fechad")
      ? "Descartada"
      : "Encerrada";
  }
  return Number(row.expectedPct) > 0 ? "Potencial positivo" : "Revisar";
}

function displayAssetName(row) {
  const asset = String(row.asset || "");
  if (row.front !== "Imóveis") return asset;
  return asset.replace(/^REAL\s*[-–—]\s*/i, "").trim() || asset;
}

function isEstimatedRealEstate(thesis) {
  return thesis.frente === "Imóveis" && (thesis.resultadoTipo === "estimate" || thesis.isOpen === false);
}

function exitText(row) {
  const target = row.targetPrice ? `alvo ${money(row.targetPrice)}` : "";
  const stop = row.stopPrice ? `stop ${money(row.stopPrice)}` : "";
  const priceRule = [target, stop].filter(Boolean).join(" · ");
  return priceRule || row.exitRule || "--";
}

function compactExitRule(value) {
  return String(value || "--").replace(/\s*\/\s*/g, " · ");
}

function hasUsefulText(value) {
  const text = String(value ?? "").trim();
  return Boolean(text && text !== "--" && text !== "R$ --");
}

function usefulText(value, fallback = "Dados incompletos") {
  const text = String(value ?? "").trim();
  return hasUsefulText(text) ? text : fallback;
}

function entryDateLabel(row) {
  const formatted = formatDate(row.openedAt);
  return formatted === "--" ? "Data incompleta" : formatted;
}

function entryPriceLabel(row) {
  const formatted = money(row.entrada);
  return formatted === "R$ --" ? "Preço incompleto" : formatted;
}

function holdingPeriodLabel(row) {
  const days = Number(row.dias);
  if (!Number.isFinite(days)) return "Prazo incompleto";
  const rounded = Math.max(0, Math.round(days));
  if (rounded === 0) return "Hoje";
  if (rounded === 1) return "1 dia";
  return `${rounded} dias`;
}

function exitPlanText(row) {
  if (hasUsefulText(row.exitRule)) return compactExitRule(row.exitRule);
  if (hasUsefulText(row.saida)) return compactExitRule(row.saida);
  return "Critério de saída incompleto";
}

function exitReferenceText(row) {
  const target = row.targetPrice ? `alvo ${money(row.targetPrice)}` : "";
  const stop = row.stopPrice ? `stop ${money(row.stopPrice)}` : "";
  return [target, stop].filter(Boolean).join(" · ");
}

function resultKindLabel(row) {
  if (row.resultadoTipo === "estimate") return "estimado";
  if (!isOpenThesis(row.status)) return "realizado";
  return "momento atual";
}

function stickyColumnStyle(left, background, zIndex) {
  return {
    position: "sticky",
    left,
    background,
    zIndex,
  };
}

function headerStyle(label, index) {
  return {
    padding: "7px 8px",
    color: C.muted,
    fontWeight: 600,
    textAlign: "left",
    fontSize: label === "Resultado" ? 7 : 10,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    borderBottom: `1px solid ${C.border}`,
    whiteSpace: "nowrap",
    ...(index === 0 ? stickyColumnStyle(0, C.panel, 5) : {}),
    ...(index === 1 ? stickyColumnStyle(70, C.panel, 5) : {}),
  };
}

function ensureHistoricalRows(rows) {
  const historicalCount = rows.filter((row) => row.status === "Histórica").length;
  if (historicalCount >= 5) return rows;
  const existing = new Set(rows.map((row) => String(row.id)));
  return [...rows, ...historicalFallback.filter((row) => !existing.has(String(row.id)))];
}

function FilterButton({ active, children, onClick }) {
  return (
    <button type="button" onClick={onClick} style={{ background: active ? withAlpha(C.gold, alpha.glow) : "transparent", border: active ? `1px solid ${withAlpha(C.gold, alpha.border)}` : "1px solid transparent", borderRadius: 8, cursor: "pointer", fontFamily: "inherit", padding: 0 }}>
      {children}
    </button>
  );
}

function Cell({ children, color = C.text, numeric = false, style = {}, testId }) {
  return <td data-testid={testId} style={{ padding: "7px 8px", color, fontFamily: numeric ? mono : "inherit", ...style }}>{children}</td>;
}

function countBy(rows, predicate) {
  return rows.filter(predicate).length;
}

function compactDirectionLabel(row) {
  if (row.frente === "Imóveis" && row.direcao === "Potencial positivo") return "POT. POSITIVO";
  return row.direcao;
}

function searchableText(row) {
  return [
    row.ativo,
    row.estrutura,
    row.hipotese,
    row.aprendizado,
    row.sourceUrl,
    row.realEstateAnalysis?.next_action,
  ]
    .filter(Boolean)
    .join(" ")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function hasAnyTerm(text, terms) {
  return terms.some((term) => text.includes(term));
}

const realEstateFrontDefinitions = [
  {
    key: "auction",
    label: "Leilão / Caixa",
    accent: C.gold,
    strategyIds: ["leilao_venda_online"],
    objective: "Comprar com desconto, mas só depois de matrícula, ocupação e débitos claros.",
    emptyAction: "Trazer novos links da Caixa ou leiloeiros oficiais.",
  },
  {
    key: "direct",
    label: "Compra Direta",
    accent: C.sky,
    strategyIds: ["venda_direta_negociacao"],
    objective: "Negociar com vendedor/portal e testar se o preço cabe no teto.",
    emptyAction: "Importar oportunidades de VivaReal, Zap, QuintoAndar ou Imovelweb.",
  },
  {
    key: "arbitrage",
    label: "Arbitragem sem reforma",
    accent: C.amber,
    strategyIds: ["arbitragem_sem_reforma"],
    objective: "Comprar abaixo de comparáveis líquidos sem depender de obra para criar valor.",
    emptyAction: "Buscar assimetria de preço com liquidez comprovada.",
  },
  {
    key: "flipping",
    label: "House Flipping",
    accent: C.teal,
    strategyIds: ["house_flipping_leve"],
    objective: "Comprar bem, reformar leve e sair rápido com margem de segurança.",
    emptyAction: "Buscar imóveis com reforma estética, não estrutural.",
  },
  {
    key: "heavy-flip",
    label: "Reforma pesada",
    accent: C.coral,
    strategyIds: ["house_flipping_pesada"],
    objective: "Só estudar quando o desconto paga prazo, obra, reserva e risco de execução.",
    emptyAction: "Exigir margem maior e orçamento antes de virar tese.",
  },
  {
    key: "income",
    label: "Renda / Plano B",
    accent: C.green,
    strategyIds: ["renda_plano_b"],
    objective: "Validar se aluguel sustenta o plano caso a venda demore.",
    emptyAction: "Levantar aluguel de mercado e liquidez da região.",
  },
  {
    key: "requalification",
    label: "Condomínio antigo em requalificação",
    accent: C.purple,
    strategyIds: ["condominio_antigo_requalificacao"],
    objective: "Procurar unidade em prédio antigo cuja fachada, portaria ou áreas comuns estejam melhorando.",
    emptyAction: "Confirmar sinal do prédio e depois buscar unidade com preço assimétrico.",
  },
  {
    key: "launch",
    label: "Lançamentos",
    accent: C.purple,
    strategyIds: ["lancamentos_ciclo_entrega"],
    objective: "Monitorar ciclo longo, entrega, distrato e valorização real.",
    emptyAction: "Só estudar quando prazo e risco de entrega estiverem explícitos.",
  },
];

const neighborhoodCondoTargets = [
  {
    key: "pinheiros",
    label: "Pinheiros",
    accent: C.teal,
    thesis: "Alta procura, estoque antigo e barreira de reposição no miolo mais desejado.",
    signals: ["Barreira de reposição", "Prédios antigos bons", "Gastronomia e serviços", "Metrô e mobilidade"],
    searchTerms: ["pinheiros", "vila madalena", "sumarezinho"],
  },
  {
    key: "perdizes-pompeia",
    label: "Perdizes / Pompéia",
    accent: C.gold,
    thesis: "Bairros consolidados, muita unidade antiga e comprador final sensível a prédio bem cuidado.",
    signals: ["Estoque consolidado", "Condomínios conhecidos", "Demanda familiar", "Reforma interna valorizável"],
    searchTerms: ["perdizes", "pompeia", "pompéia", "agua branca"],
  },
  {
    key: "vila-mariana",
    label: "Vila Mariana",
    accent: C.sky,
    thesis: "Liquidez forte, metrô e prédios antigos onde produto reformado pode competir bem.",
    signals: ["Liquidez", "Metrô", "2 dormitórios", "Prédio preservado"],
    searchTerms: ["vila mariana", "paraiso", "paraíso", "chacara klabin", "chácara klabin"],
  },
];

function realEstateFrontKey(row) {
  const text = searchableText(row);
  if (hasAnyTerm(text, ["condominio antigo", "requalificacao", "fachada reformada", "area comum reformada", "areas comuns reformadas", "retrofit"])) return "requalification";
  if (hasAnyTerm(text, ["reforma pesada", "obra pesada", "estrutural"])) return "heavy-flip";
  if (hasAnyTerm(text, ["leilao", "caixa", "venda online", "arremat"])) return "auction";
  if (hasAnyTerm(text, ["arbitragem", "sem reforma"])) return "arbitrage";
  if (hasAnyTerm(text, ["house flipping", "flip", "reforma", "retrofit", "revenda"])) return "flipping";
  if (hasAnyTerm(text, ["plano b", "aluguel", "locacao", "renda"])) return "income";
  if (hasAnyTerm(text, ["lancamento", "planta", "obra", "entrega"])) return "launch";
  if (hasAnyTerm(text, ["compra direta", "quintoandar", "vivareal", "zap", "imovelweb", "vendedor direto"])) return "direct";
  return "direct";
}

function neighborhoodCondoTargetKey(row) {
  const text = searchableText(row);
  const target = neighborhoodCondoTargets.find((item) => hasAnyTerm(text, item.searchTerms));
  return target?.key || null;
}

function scoreOf(row) {
  return Number(row.realEstateAnalysis?.score) || 0;
}

function bestRowByScore(rows) {
  return rows.reduce((best, row) => {
    if (!best) return row;
    return scoreOf(row) > scoreOf(best) ? row : best;
  }, null);
}

function reportArray(report, camelKey, snakeKey) {
  const value = report?.[camelKey] ?? report?.[snakeKey];
  return Array.isArray(value) ? value : [];
}

function realEstateMatrixBriefs(report) {
  return reportArray(report, "matrixBriefs", "matrix_briefs");
}

function realEstateRequalificationSignals(report) {
  return reportArray(report, "condominiumRequalificationWatchlist", "condominium_requalification_watchlist");
}

function realEstateStrategySourceCandidates(report) {
  return reportArray(report, "strategyCandidateWatchlist", "strategy_candidate_watchlist");
}

function briefField(brief, camelKey, snakeKey, fallback = "") {
  return brief?.[camelKey] ?? brief?.[snakeKey] ?? fallback;
}

function briefStrategyId(brief) {
  return String(briefField(brief, "strategyId", "strategy_id")).trim();
}

function realEstateReportSummary(report) {
  const summary = report?.summary ?? {};
  const matrixBriefs = realEstateMatrixBriefs(report);
  const sourceCandidates = realEstateStrategySourceCandidates(report);
  const signals = realEstateRequalificationSignals(report);
  return {
    strategyCount: Number(summary.strategyCount ?? summary.strategy_count) || 0,
    territoryCount: Number(summary.territoryCount ?? summary.territory_count) || 0,
    matrixBriefCount: Number(summary.matrixBriefCount ?? summary.matrix_brief_count) || matrixBriefs.length,
    sourceCandidateCount: Number(summary.sourceCandidateCount ?? summary.source_candidate_count) || sourceCandidates.length,
    sourceConfirmedRequalificationCount: Number(summary.sourceConfirmedRequalificationCount ?? summary.source_confirmed_requalification_count) || signals.length,
    actionability: usefulText(summary.actionability, "Briefs e fontes são triagem; unidade, preço, comparáveis, disponibilidade e P0 ainda precisam ser confirmados."),
  };
}

function realEstateBriefsForDefinition(report, definition) {
  const strategyIds = new Set(definition.strategyIds || []);
  if (!strategyIds.size) return { briefs: [], signals: [], sources: [] };
  const briefs = realEstateMatrixBriefs(report).filter((brief) => strategyIds.has(briefStrategyId(brief)));
  const sources = realEstateStrategySourceCandidates(report).filter((brief) => strategyIds.has(briefStrategyId(brief)));
  const signals = realEstateRequalificationSignals(report).filter((brief) => strategyIds.has(briefStrategyId(brief)));
  return { briefs, signals, sources };
}

function realEstateFrontSummaries(rows, strategyReport) {
  return realEstateFrontDefinitions.map((definition) => {
    const groupRows = rows.filter((row) => realEstateFrontKey(row) === definition.key);
    const activeRows = groupRows.filter((row) => isOpenThesis(row.status));
    const best = bestRowByScore(groupRows);
    const { briefs, signals, sources } = realEstateBriefsForDefinition(strategyReport, definition);
    const avgScore = groupRows.length
      ? Math.round(groupRows.reduce((sum, row) => sum + scoreOf(row), 0) / groupRows.length)
      : 0;
    const p0 = groupRows.reduce((sum, row) => sum + getP0Count(row), 0);

    return {
      ...definition,
      rows: groupRows,
      active: activeRows.length,
      briefCount: briefs.length,
      signalCount: signals.length,
      sourceCount: sources.length,
      avgScore,
      p0,
      best,
      action: best?.realEstateAnalysis?.next_action || sources[0]?.candidateAngle || sources[0]?.candidate_angle || definition.emptyAction,
    };
  });
}

function bestRealEstateAction(rows) {
  const candidates = rows
    .filter((row) => isOpenThesis(row.status))
    .slice()
    .sort((a, b) => {
      const p0Diff = getP0Count(b) - getP0Count(a);
      if (p0Diff !== 0) return p0Diff;
      return scoreOf(b) - scoreOf(a);
    });
  return candidates[0] || rows[0] || null;
}

function sourceHost(url) {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return String(url).replace(/^https?:\/\//, "").split("/")[0];
  }
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

function moneyPrecise(value) {
  if (value === null || value === undefined || value === "") return "R$ --";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (Math.abs(number) >= 1000000) return `R$ ${(number / 1000000).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M`;
  if (Math.abs(number) >= 100000) return `R$ ${(number / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}K`;
  return `R$ ${number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function moneyCompact(value) {
  if (value === null || value === undefined || value === "") return "R$ --";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (Math.abs(number) >= 1000000) return `R$ ${(number / 1000000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}M`;
  if (Math.abs(number) >= 1000) return `R$ ${(number / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}K`;
  return `R$ ${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

function ViewTab({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        background: active ? C.gold + "18" : C.panel,
        border: `1px solid ${active ? C.gold + "45" : C.border}`,
        borderRadius: 999,
        color: active ? C.gold : C.muted,
        cursor: "pointer",
        fontFamily: "inherit",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.04em",
        padding: "8px 12px",
        textTransform: "uppercase",
      }}
    >
      {children}
    </button>
  );
}

function HubSection({ title, eyebrow, children, action }) {
  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div>
          {eyebrow && <div style={{ color: C.gold, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>{eyebrow}</div>}
          <h2 style={{ color: C.text, fontSize: 15, fontWeight: 800, margin: 0 }}>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function frontAccent(front) {
  if (front === "Cripto") return C.amber;
  if (front === "Imóveis") return C.purple;
  return C.sky;
}

function getP0Count(row) {
  const pending = row.realEstateAnalysis?.pending_items || [];
  return pending.filter((item) => item.priority === "P0").length;
}

function attentionReason(row) {
  const p0 = getP0Count(row);
  if (p0) return `${p0} P0 bloqueia decisão`;
  if (String(row.desfecho || "").toLowerCase().includes("stop")) return "Stop registrado";
  if (String(row.desfecho || "").toLowerCase().includes("pend")) return "Pendências abertas";
  if (Number(row.resultado) < 0) return "Resultado abaixo do plano";
  return "Prioridade de acompanhamento";
}

function needsThesisAttention(row) {
  return getP0Count(row) > 0 || Number(row.resultado) < 0 || /stop|pend/i.test(String(row.desfecho || ""));
}

function FrontSummaryCard({ front, rows, onClick }) {
  const total = rows.length;
  const active = rows.filter((row) => isOpenThesis(row.status)).length;
  const historical = rows.filter((row) => row.status === "Histórica").length;
  const expectedValues = rows.map((row) => Number(row.esperado)).filter(Number.isFinite);
  const avgExpected = expectedValues.length ? expectedValues.reduce((sum, value) => sum + value, 0) / expectedValues.length : 0;
  const accent = frontAccent(front);

  return (
    <button
      type="button"
      aria-label={`Abrir resumo ${front}`}
      onClick={onClick}
      style={{
        background: `linear-gradient(135deg, ${C.panel}, ${C.card})`,
        border: `1px solid ${C.border}`,
        borderTop: `2px solid ${accent}`,
        borderRadius: 14,
        cursor: "pointer",
        fontFamily: "inherit",
        minHeight: 128,
        overflow: "hidden",
        padding: 14,
        position: "relative",
        textAlign: "left",
      }}
    >
      <div style={{ position: "absolute", right: -28, top: -28, width: 92, height: 92, borderRadius: "50%", background: accent + "14" }} />
      <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
          <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>{front}</div>
          <Badge label={front === "Imóveis" ? "Radar" : "Teses"} type="info" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <div style={{ color: accent, fontFamily: mono, fontSize: 22, fontWeight: 800 }}>{total}</div>
            <div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Mapeadas</div>
          </div>
          <div>
            <div style={{ color: active ? C.teal : C.dim, fontFamily: mono, fontSize: 22, fontWeight: 800 }}>{active}</div>
            <div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>{front === "Imóveis" ? "No radar" : "Vivas"}</div>
          </div>
        </div>
        <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>
          Histórico: <span style={{ color: C.text, fontFamily: mono }}>{historical}</span> · Esperado médio: <span style={{ color: accent, fontFamily: mono }}>{pct(avgExpected)}</span>
        </div>
      </div>
    </button>
  );
}

function RealEstateFrontCard({ summary, active, onClick }) {
  const total = summary.rows.length;
  const sourceCount = Number(summary.sourceCount) || 0;
  const hasBriefs = summary.briefCount > 0 || summary.signalCount > 0 || sourceCount > 0;

  return (
    <button
      type="button"
      aria-label={`Ver candidatos ${summary.label}`}
      onClick={onClick}
      data-testid={`real-estate-front-card-${summary.key}`}
      style={{
        background: active ? `linear-gradient(145deg, ${summary.accent}24, ${C.panel})` : `linear-gradient(145deg, ${summary.accent}12, ${C.panel})`,
        border: `1px solid ${active ? summary.accent : summary.accent + "35"}`,
        borderTop: `3px solid ${summary.accent}`,
        borderRadius: 14,
        boxShadow: active ? `0 0 0 2px ${summary.accent}22` : "none",
        color: "inherit",
        cursor: "pointer",
        fontFamily: "inherit",
        minHeight: 176,
        overflow: "hidden",
        padding: 14,
        position: "relative",
        textAlign: "left",
        transition: "border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease",
        width: "100%",
      }}
    >
      <div style={{ position: "absolute", right: -34, top: -34, width: 108, height: 108, borderRadius: "50%", background: summary.accent + "14" }} />
      <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
          <div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>{summary.label}</div>
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 5 }}>{summary.objective}</div>
          </div>
          <span style={{ color: summary.accent, fontFamily: mono, fontSize: 24, fontWeight: 800, lineHeight: 1 }}>{total}</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <DetailCell label="Candidatos" value={total} color={total ? C.teal : C.muted} numeric />
          <DetailCell label="Briefs busca" value={summary.briefCount} color={summary.briefCount ? summary.accent : C.muted} numeric />
          <DetailCell label="Abertos" value={summary.active} color={summary.active ? C.teal : C.muted} numeric />
          <DetailCell label="Fontes" value={sourceCount} color={sourceCount ? C.sky : C.muted} numeric />
        </div>
        <div style={{ background: C.bg + "70", border: `1px solid ${C.border}`, borderRadius: 10, padding: "9px 10px" }}>
          <div style={{ color: summary.accent, fontSize: 9, fontWeight: 800, letterSpacing: "0.08em", marginBottom: 5, textTransform: "uppercase" }}>
            Próximo passo
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>{summary.action}</div>
        </div>
        {hasBriefs && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Badge label="Hipótese de busca" type="warning" />
            {sourceCount > 0 && <Badge label="Fonte candidata" type="info" />}
            {summary.signalCount > 0 && <Badge label="Sinal confirmado" type="success" />}
          </div>
        )}
        {summary.p0 > 0 && <Badge label={`${summary.p0} P0`} type="danger" />}
      </div>
    </button>
  );
}

function RealEstateFrontCards({ rows, strategyReport, activeKey, onSelect }) {
  const summaries = realEstateFrontSummaries(rows, strategyReport);

  return (
    <div data-testid="real-estate-front-cards" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
      {summaries.map((summary) => (
        <RealEstateFrontCard
          key={summary.key}
          summary={summary}
          active={activeKey === summary.key}
          onClick={() => onSelect(summary.key)}
        />
      ))}
    </div>
  );
}

function trustBadgeForBrief(brief) {
  const trust = String(briefField(brief, "trustLevel", "trust_level")).toLowerCase();
  if (trust === "source_confirmed") {
    return { label: "Sinal confirmado", type: "success" };
  }
  return trust === "source_listed"
    ? { label: "Fonte candidata", type: "info" }
    : { label: "Hipótese de busca", type: "warning" };
}

function displayBriefTitle(brief) {
  return usefulText(briefField(brief, "title", "title"), "Brief de busca imobiliária");
}

function displayBriefStrategy(brief) {
  const strategyId = briefStrategyId(brief);
  return realEstateFrontDefinitions.find((definition) => (definition.strategyIds || []).includes(strategyId))?.label
    || usefulText(briefField(brief, "strategyLabel", "strategy_label"), "Estratégia imobiliária");
}

function displayBriefTerritory(brief) {
  return usefulText(briefField(brief, "territoryLabel", "territory_label"), "Território a validar");
}

function displayBriefRule(brief) {
  return usefulText(
    briefField(brief, "decisionRule", "decision_rule"),
    "Não vira tese de compra até existir unidade, preço, comparáveis e pendências P0 fechadas.",
  );
}

function RealEstateStrategyTerritoryBriefs({ report }) {
  const matrixBriefs = realEstateMatrixBriefs(report);
  const sourceCandidates = realEstateStrategySourceCandidates(report);
  const signals = realEstateRequalificationSignals(report);
  const summary = realEstateReportSummary(report);
  const strategySummaries = realEstateFrontDefinitions
    .map((definition) => {
      const { briefs, signals: definitionSignals, sources } = realEstateBriefsForDefinition(report, definition);
      return { ...definition, briefs, signals: definitionSignals, sources };
    })
    .filter((definition) => definition.briefs.length || definition.signals.length || definition.sources.length);
  const previewBriefs = matrixBriefs.slice(0, 4);
  const previewSources = sourceCandidates.slice(0, 4);
  const previewSignals = signals.slice(0, 4);

  return (
    <section data-testid="real-estate-strategy-territory-briefs" style={{ background: `linear-gradient(135deg, ${C.panel}, ${C.faint})`, border: `1px solid ${C.gold}35`, borderLeft: `4px solid ${C.gold}`, borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>
            Busca antes da tese
          </div>
          <div style={{ color: C.text, fontSize: 16, fontWeight: 900 }}>Briefs por estratégia e território</div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 5, maxWidth: 720 }}>
            Estes itens explicam onde procurar e o que validar. Eles não entram na lista de candidatos cadastrados até existir unidade, preço, comparáveis e P0 fechados.
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <Badge label="Hipótese de busca" type="warning" />
          {summary.sourceCandidateCount > 0 && <Badge label="Fonte candidata" type="info" />}
          {summary.sourceConfirmedRequalificationCount > 0 && <Badge label="Sinal confirmado" type="success" />}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
        <DetailCell label="Briefs" value={summary.matrixBriefCount} color={summary.matrixBriefCount ? C.gold : C.muted} numeric />
        <DetailCell label="Estratégias" value={summary.strategyCount} color={C.sky} numeric />
        <DetailCell label="Territórios" value={summary.territoryCount} color={C.teal} numeric />
        <DetailCell label="Fontes candidatas" value={summary.sourceCandidateCount} color={summary.sourceCandidateCount ? C.sky : C.muted} numeric />
        <DetailCell label="Sinais confirmados" value={summary.sourceConfirmedRequalificationCount} color={summary.sourceConfirmedRequalificationCount ? C.green : C.muted} numeric />
      </div>

      <div style={{ background: C.bg + "70", border: `1px solid ${C.border}`, borderRadius: 12, color: C.muted, fontSize: 11, lineHeight: 1.55, padding: "10px 12px" }}>
        {summary.actionability}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 10 }}>
        {strategySummaries.map((definition) => (
          <article key={`brief-summary-${definition.key}`} style={{ background: C.card, border: `1px solid ${definition.accent}35`, borderTop: `3px solid ${definition.accent}`, borderRadius: 12, padding: 12 }}>
            <div style={{ color: definition.accent, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>
              {definition.briefs.length} briefs · {definition.sources.length} fontes
            </div>
            <div style={{ color: C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.3 }}>{definition.label}</div>
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 7 }}>
              {definition.signals.length > 0
                ? `${definition.signals.length} sinal confirmado de prédio/território.`
                : definition.sources.length > 0
                  ? `${definition.sources.length} fonte candidata para triagem.`
                  : "Sem sinal confirmado ainda; é mapa de busca para triagem."}
            </div>
          </article>
        ))}
      </div>

      {previewSources.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ color: C.sky, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>Fontes candidatas</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 }}>
            {previewSources.map((brief) => {
              const badge = trustBadgeForBrief(brief);
              return (
                <article key={briefField(brief, "id", "brief_id", displayBriefTitle(brief))} style={{ background: C.sky + "10", border: `1px solid ${C.sky}35`, borderRadius: 12, padding: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
                    <div style={{ color: C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.35 }}>{displayBriefTitle(brief)}</div>
                    <Badge label={badge.label} type={badge.type} />
                  </div>
                  <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 7 }}>
                    {displayBriefStrategy(brief)} · {displayBriefTerritory(brief)}
                  </div>
                  <div style={{ color: C.sky, fontSize: 11, fontWeight: 800, lineHeight: 1.45, marginTop: 7 }}>
                    {usefulText(briefField(brief, "candidateAngle", "candidate_angle"), "Validar fonte, disponibilidade e pendências antes de virar tese.")}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      )}

      {previewSignals.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ color: C.green, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>Watchlist confirmada</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 }}>
            {previewSignals.map((brief) => {
              const badge = trustBadgeForBrief(brief);
              return (
                <article key={briefField(brief, "id", "brief_id", displayBriefTitle(brief))} style={{ background: C.green + "10", border: `1px solid ${C.green}35`, borderRadius: 12, padding: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
                    <div style={{ color: C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.35 }}>{displayBriefTitle(brief)}</div>
                    <Badge label={badge.label} type={badge.type} />
                  </div>
                  <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 7 }}>
                    {displayBriefTerritory(brief)} · {usefulText(briefField(brief, "sourceName", "source_name"), "Fonte a conferir")}
                  </div>
                  <div style={{ color: C.green, fontSize: 11, fontWeight: 800, lineHeight: 1.45, marginTop: 7 }}>
                    {usefulText(briefField(brief, "sourceSummary", "source_summary"), "Sinal de requalificação confirmado na fonte.")}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      )}

      {previewBriefs.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>Amostra de briefs</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 }}>
            {previewBriefs.map((brief) => {
              const badge = trustBadgeForBrief(brief);
              return (
                <article key={briefField(brief, "id", "brief_id", displayBriefTitle(brief))} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
                    <div style={{ color: C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.35 }}>{displayBriefStrategy(brief)}</div>
                    <Badge label={badge.label} type={badge.type} />
                  </div>
                  <div style={{ color: C.gold, fontSize: 11, fontWeight: 850, lineHeight: 1.45, marginTop: 7 }}>{displayBriefTerritory(brief)}</div>
                  <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 7 }}>{displayBriefRule(brief)}</div>
                </article>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

function evaluationStatus(label, value, color, state = "Atenção") {
  return { label, value, color, state };
}

function DealEvaluationBlock({ item }) {
  return (
    <div style={{ background: C.bg + "72", border: `1px solid ${item.color}35`, borderLeft: `3px solid ${item.color}`, borderRadius: 12, padding: "10px 11px", minHeight: 88 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
        <div style={{ color: C.text, fontSize: 13, fontWeight: 900 }}>{item.label}</div>
        <span style={{ background: item.color + "16", border: `1px solid ${item.color}35`, borderRadius: 999, color: item.color, fontFamily: mono, fontSize: 8, fontWeight: 900, padding: "2px 6px", textTransform: "uppercase" }}>
          {item.state}
        </span>
      </div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 8 }}>{item.value}</div>
    </div>
  );
}

function RealEstateDealCockpit({ rows, allRows, selected, onSelect }) {
  const candidates = rows.length ? rows : allRows;
  const focusFromSelection = selected?.frente === "Imóveis" && candidates.some((item) => String(item.id) === String(selected.id));
  const row = focusFromSelection ? selected : bestRealEstateAction(candidates);
  const [manualDecision, setManualDecision] = useState(null);
  const [decisionReason, setDecisionReason] = useState("");

  useEffect(() => {
    setManualDecision(null);
    setDecisionReason("");
  }, [row?.id]);

  const total = allRows.length;
  const active = allRows.filter((item) => isOpenThesis(item.status)).length;
  const totalP0 = allRows.reduce((sum, item) => sum + getP0Count(item), 0);
  const p0 = row ? getP0Count(row) : 0;
  const score = row ? scoreOf(row) : 0;
  const confidence = Number(row?.realEstateAnalysis?.confidence) || 0;
  const front = row ? realEstateFrontDefinitions.find((item) => item.key === realEstateFrontKey(row)) : null;
  const building = row ? goodBuildingScore(row) : null;
  const candidate = row ? realEstateCandidatePayload(row) : {};
  const priceStatus = row?.realEstateAnalysis?.price_ceiling_status || "Preço em validação";
  const nextAction = row?.realEstateAnalysis?.next_action || row?.saida || "Escolher um candidato para começar.";
  const suggestedDecision = !row
    ? "Escolher candidato"
    : p0
      ? "Não avançar antes dos P0"
      : score >= 70
        ? "Avançar para due diligence"
        : "Estudar com cautela";
  const decisionColor = p0 ? C.coral : score >= 70 ? C.teal : C.amber;
  const baseScenario = row?.realEstateAnalysis?.scenarios?.base || {};
  const renovation = firstText(
    candidate.renovation_type,
    candidate.renovation_budget && money(candidate.renovation_budget),
    row?.realEstateAnalysis?.renovation_type,
    "Reforma a validar",
  );
  const exitSignal = firstText(
    baseScenario.roi_pct !== undefined && `ROI base ${pct(baseScenario.roi_pct)}`,
    row?.saida,
    "Saída a validar",
  );
  const orderedQueue = candidates
    .slice()
    .sort((a, b) => {
      const p0Diff = getP0Count(b) - getP0Count(a);
      if (p0Diff !== 0) return p0Diff;
      return scoreOf(b) - scoreOf(a);
    })
    .slice(0, 5);
  const evaluation = [
    evaluationStatus("Preço", priceStatus, priceStatus === "Acima do teto" ? C.coral : C.teal, priceStatus === "Acima do teto" ? "Bloqueio" : "OK"),
    evaluationStatus("Prédio", building?.label || "Prédio a validar", building?.color || C.amber, building?.score >= 70 ? "OK" : "Atenção"),
    evaluationStatus("Reforma", renovation, C.teal, renovation === "Reforma a validar" ? "Pendente" : "OK"),
    evaluationStatus("Saída", exitSignal, C.sky, "Validar"),
    evaluationStatus("Risco", p0 ? `${p0} P0 bloqueia proposta` : "Sem P0 aberto", p0 ? C.coral : C.green, p0 ? "Bloqueio" : "OK"),
  ];

  return (
    <section
      data-testid="real-estate-deal-cockpit"
      style={{
        background: `radial-gradient(circle at 8% 0%, ${C.gold}1f, transparent 32%), linear-gradient(135deg, ${C.card}, ${C.panel})`,
        border: `1px solid ${C.gold}45`,
        borderTop: `2px solid ${C.gold}`,
        borderRadius: 18,
        display: "grid",
        gridTemplateColumns: "minmax(0, 1.45fr) minmax(260px, 0.55fr)",
        gap: 14,
        overflow: "hidden",
        padding: 18,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(220px, 0.58fr)", gap: 14 }}>
          <div>
            <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
              Deal cockpit
            </div>
            <h2 style={{ color: C.muted, fontSize: 12, fontWeight: 900, letterSpacing: "0.08em", margin: "0 0 6px", textTransform: "uppercase" }}>Radar imobiliário</h2>
            <div style={{ color: C.text, fontSize: 24, fontWeight: 950, lineHeight: 1.08 }}>Este candidato deve avançar?</div>
            <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.55, margin: "8px 0 0", maxWidth: 660 }}>
              Um imóvel em foco por vez. A fila prioriza o que exige decisão; categorias, bairros e lista completa ficam recolhidos como apoio.
            </p>
          </div>
          <div style={{ background: C.bg + "8f", border: `1px solid ${decisionColor}45`, borderLeft: `4px solid ${decisionColor}`, borderRadius: 14, padding: 13 }}>
            <div style={{ color: decisionColor, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              Decisão sugerida
            </div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 900, lineHeight: 1.3 }}>{suggestedDecision}</div>
            <div style={{ color: C.gold, fontSize: 11, fontWeight: 800, lineHeight: 1.45, marginTop: 8 }}>{nextAction}</div>
          </div>
        </div>

        <div style={{ background: C.bg + "64", border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
          <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
            Candidato em avaliação
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: C.text, fontSize: 16, fontWeight: 950, lineHeight: 1.25 }}>{row?.ativo || "Nenhum candidato selecionado"}</div>
              <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 5 }}>{front?.label || "Frente a classificar"} · {row?.estrutura || "Tese em formação"}</div>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
              <Badge label={`${score}/100 score`} type={score >= 70 ? "success" : "warning"} />
              <Badge label={`${confidence}/100 confiança`} type="info" />
              <Badge label={`${p0} P0`} type={p0 ? "danger" : "success"} />
            </div>
          </div>
        </div>

        <div>
          <div style={{ color: C.muted, fontSize: 10, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
            Ritual de avaliação
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(142px, 1fr))", gap: 8 }}>
            {evaluation.map((item) => <DealEvaluationBlock key={item.label} item={item} />)}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) auto", gap: 10, alignItems: "end" }}>
          <label style={{ color: C.muted, fontSize: 11, fontWeight: 800, lineHeight: 1.45 }}>
            Motivo da decisão
            <textarea
              aria-label="Motivo da decisão"
              value={decisionReason}
              onChange={(event) => setDecisionReason(event.target.value)}
              placeholder="Ex.: Aguardar ocupação e matrícula antes de proposta."
              rows={2}
              style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, boxSizing: "border-box", color: C.text, display: "block", fontFamily: "inherit", fontSize: 12, lineHeight: 1.45, marginTop: 6, padding: "8px 10px", resize: "vertical", width: "100%" }}
            />
          </label>
          <button type="button" onClick={() => row && onSelect(row)} style={{ background: C.gold + "18", border: `1px solid ${C.gold}55`, borderRadius: 10, color: C.gold, cursor: "pointer", fontFamily: "inherit", fontSize: 11, fontWeight: 900, padding: "10px 12px", whiteSpace: "nowrap" }}>
            Ver ficha
          </button>
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["Avançar para visita", "Avançar para proposta", "Segurar", "Descartar"].map((action) => {
            const blocked = action === "Avançar para proposta" && p0 > 0;
            const accent = action === "Descartar" ? C.coral : action === "Segurar" ? C.amber : C.teal;
            return (
              <button
                key={action}
                type="button"
                disabled={blocked}
                onClick={() => setManualDecision(action)}
                title={blocked ? "Resolva os P0 antes de propor." : undefined}
                style={{ background: blocked ? C.panel : accent + "1f", border: `1px solid ${blocked ? C.border : accent + "55"}`, borderRadius: 10, color: blocked ? C.dim : accent, cursor: blocked ? "not-allowed" : "pointer", fontFamily: "inherit", fontSize: 11, fontWeight: 900, padding: "9px 11px" }}
              >
                {action}
              </button>
            );
          })}
        </div>
        {manualDecision && (
          <div style={{ background: decisionColor + "12", border: `1px solid ${decisionColor}35`, borderRadius: 12, color: C.text, fontSize: 12, fontWeight: 800, lineHeight: 1.5, padding: "10px 12px" }}>
            Decisão registrada: {manualDecision}
            {decisionReason.trim() && <span style={{ color: C.muted, display: "block", fontWeight: 600, marginTop: 4 }}>{decisionReason.trim()}</span>}
          </div>
        )}
      </div>

      <aside style={{ background: C.bg + "72", border: `1px solid ${C.border}`, borderRadius: 14, padding: 13 }}>
        <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 9 }}>Fila de decisão</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {orderedQueue.map((item, index) => {
            const activeItem = String(item.id) === String(row?.id);
            const itemP0 = getP0Count(item);
            const itemAccent = itemP0 ? C.coral : scoreOf(item) >= 70 ? C.teal : C.amber;
            return (
              <button
                key={`deal-queue-${item.id}`}
                type="button"
                onClick={() => onSelect(item)}
                style={{ background: activeItem ? itemAccent + "16" : C.panel, border: `1px solid ${activeItem ? itemAccent + "65" : C.border}`, borderLeft: `3px solid ${itemAccent}`, borderRadius: 11, color: C.text, cursor: "pointer", fontFamily: "inherit", padding: "9px 10px", textAlign: "left" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ color: itemAccent, fontFamily: mono, fontSize: 10, fontWeight: 900 }}>#{index + 1}</span>
                  <span style={{ color: itemAccent, fontFamily: mono, fontSize: 10, fontWeight: 900 }}>{scoreOf(item)}/100</span>
                </div>
                <div style={{ color: C.text, fontSize: 12, fontWeight: 900, lineHeight: 1.3, marginTop: 5 }}>{item.ativo}</div>
                <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.35, marginTop: 4 }}>{item.realEstateAnalysis?.next_action || item.saida || "Definir próxima ação"}</div>
                {itemP0 > 0 && <div style={{ color: C.coral, fontSize: 10, fontWeight: 900, marginTop: 5 }}>{itemP0} P0</div>}
              </button>
            );
          })}
        </div>
        <div style={{ borderTop: `1px solid ${C.border}`, display: "flex", gap: 7, flexWrap: "wrap", marginTop: 12, paddingTop: 11 }}>
          <Badge label={`${total} candidatos`} type="info" />
          <Badge label={`${active} no radar`} type="open" />
          <Badge label={`${totalP0} P0`} type={totalP0 ? "danger" : "success"} />
        </div>
      </aside>
    </section>
  );
}

function SupportDisclosure({ title, eyebrow, children }) {
  return (
    <details style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
      <summary style={{ alignItems: "center", cursor: "pointer", display: "flex", gap: 12, justifyContent: "space-between", listStyle: "none", padding: "13px 15px" }}>
        <span>
          {eyebrow && <span style={{ color: C.gold, display: "block", fontSize: 9, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 4, textTransform: "uppercase" }}>{eyebrow}</span>}
          <span style={{ color: C.text, fontSize: 14, fontWeight: 900 }}>{title}</span>
        </span>
        <span aria-hidden="true" style={{ color: C.gold, fontFamily: mono, fontSize: 15, fontWeight: 900 }}>+</span>
      </summary>
      <div style={{ borderTop: `1px solid ${C.border}`, display: "flex", flexDirection: "column", gap: 12, padding: 14 }}>
        {children}
      </div>
    </details>
  );
}

function NeighborhoodCondoRadar({ rows, activeKey, onSelect }) {
  return (
    <section data-testid="neighborhood-condo-radar" style={{ background: `linear-gradient(135deg, ${C.panel}, ${C.faint})`, border: `1px solid ${C.border}`, borderLeft: `4px solid ${C.teal}`, borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ color: C.teal, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>
            Antes do imóvel
          </div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>Radar de bairros e condomínios</div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, marginTop: 4 }}>
            Primeiro achamos o território certo: bairro com demanda, prédio que sustenta a tese e apartamento que ainda pode ser melhorado.
          </div>
        </div>
        {activeKey && (
          <button
            type="button"
            onClick={() => onSelect(null)}
            style={{
              background: C.card,
              border: `1px solid ${C.border}`,
              borderRadius: 9,
              color: C.muted,
              cursor: "pointer",
              fontFamily: "inherit",
              fontSize: 10,
              fontWeight: 800,
              padding: "7px 9px",
              textTransform: "uppercase",
            }}
          >
            Limpar bairro
          </button>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 10 }}>
        {neighborhoodCondoTargets.map((target) => {
          const count = rows.filter((row) => neighborhoodCondoTargetKey(row) === target.key).length;
          const active = activeKey === target.key;
          return (
            <button
              key={target.key}
              type="button"
              aria-label={`Filtrar candidatos ${target.label}`}
              onClick={() => onSelect(active ? null : target.key)}
              style={{
                background: active ? target.accent + "18" : C.card,
                border: `1px solid ${active ? target.accent : target.accent + "35"}`,
                borderTop: `3px solid ${target.accent}`,
                borderRadius: 12,
                color: "inherit",
                cursor: "pointer",
                fontFamily: "inherit",
                padding: 12,
                textAlign: "left",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                <div>
                  <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>{target.label}</div>
                  <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 5 }}>{target.thesis}</div>
                </div>
                <span style={{ color: target.accent, fontFamily: mono, fontSize: 20, fontWeight: 800 }}>{count}</span>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                {target.signals.map((signal) => (
                  <span key={signal} style={{ background: target.accent + "12", border: `1px solid ${target.accent}35`, borderRadius: 999, color: target.accent, fontSize: 9, fontWeight: 800, padding: "4px 7px" }}>
                    {signal}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function RealEstateBestAction({ rows, onSelect }) {
  const row = bestRealEstateAction(rows);
  const action = row?.realEstateAnalysis?.next_action || row?.saida || "Importar um candidato real para começar a análise.";
  const p0 = row ? getP0Count(row) : 0;

  return (
    <section style={{ background: C.amber + "10", border: `1px solid ${C.amber}35`, borderLeft: `4px solid ${C.amber}`, borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
      <div>
        <div style={{ color: C.amber, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>
          Próxima melhor ação
        </div>
        <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>{row?.ativo || "Sem candidato selecionado"}</div>
      </div>
      <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.55 }}>{action}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginTop: "auto" }}>
        {row && <Badge label={`${scoreOf(row)}/100 score`} type={scoreOf(row) >= 70 ? "success" : "warning"} />}
        {p0 > 0 && <Badge label={`${p0} P0 aberto`} type="danger" />}
        {row && (
          <button
            type="button"
            onClick={() => onSelect(row)}
            style={{
              background: C.amber,
              border: 0,
              borderRadius: 9,
              color: C.bg,
              cursor: "pointer",
              fontFamily: "inherit",
              fontSize: 11,
              fontWeight: 800,
              padding: "8px 10px",
            }}
          >
            Abrir dossiê
          </button>
        )}
      </div>
    </section>
  );
}

function RealEstateImportPanel() {
  const [link, setLink] = useState("");
  const [message, setMessage] = useState("");

  function handleCreateDraft() {
    if (!link.trim()) {
      setMessage("Cole um link real para criar o rascunho de triagem.");
      return;
    }
    setMessage("Rascunho preparado. Próximo passo: preencher preço, fonte e pendências.");
  }

  return (
    <section style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
      <div>
        <div style={{ color: C.sky, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Importar link</div>
        <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>Novo candidato real</div>
        <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 4 }}>
          Cole um anúncio, leilão ou página de imóvel. Por enquanto ele cria uma triagem local; a automação vem depois.
        </div>
      </div>
      <textarea
        aria-label="Link do candidato imobiliário"
        value={link}
        onChange={(event) => setLink(event.target.value)}
        placeholder="Cole aqui o link do VivaReal, Zap, QuintoAndar, Caixa..."
        rows={2}
        style={{
          background: C.bg,
          border: `1px solid ${C.border}`,
          borderRadius: 9,
          boxSizing: "border-box",
          color: C.text,
          fontFamily: "inherit",
          fontSize: 12,
          lineHeight: 1.45,
          outline: "none",
          padding: "8px 10px",
          resize: "vertical",
          width: "100%",
        }}
      />
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={handleCreateDraft}
          style={{
            background: C.sky + "22",
            border: `1px solid ${C.sky}55`,
            borderRadius: 9,
            color: C.sky,
            cursor: "pointer",
            fontFamily: "inherit",
            fontSize: 11,
            fontWeight: 800,
            padding: "8px 10px",
          }}
        >
          Criar rascunho
        </button>
        {message && <span style={{ color: link.trim() ? C.green : C.amber, fontSize: 11, fontWeight: 700 }}>{message}</span>}
      </div>
    </section>
  );
}

function CompactThesisList({ rows, title, emptyText, onSelect, selectedId, limit = 4 }) {
  const visibleRows = rows.slice(0, limit);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {title && <div style={{ color: C.muted, fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase" }}>{title}</div>}
      {visibleRows.length === 0 ? (
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, color: C.muted, fontSize: 12, padding: 14 }}>{emptyText}</div>
      ) : visibleRows.map((row) => {
        const accent = frontAccent(row.frente);
        const selected = String(selectedId) === String(row.id);
        return (
          <button
            key={row.id}
            type="button"
            aria-label={`Abrir tese ${row.ativo}`}
            data-testid={`teses-row-${row.id}`}
            onClick={() => onSelect(row)}
            style={{
              alignItems: "center",
              background: selected ? C.hover : C.panel,
              border: `1px solid ${selected ? accent + "55" : C.border}`,
              borderLeft: `3px solid ${accent}`,
              borderRadius: 12,
              color: C.text,
              cursor: "pointer",
              display: "grid",
              fontFamily: "inherit",
              gap: 12,
              gridTemplateColumns: "minmax(118px, 1.1fr) 88px 112px 92px",
              padding: "12px 14px",
              textAlign: "left",
              width: "100%",
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div style={{ color: C.text, fontSize: 13, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.ativo}</div>
              <div style={{ color: C.dim, fontFamily: mono, fontSize: 10, marginTop: 3 }}>#{row.id}</div>
            </div>
            <Badge label={row.frente} type="info" />
            <span data-testid={`direction-badge-${row.id}`}><Badge label={compactDirectionLabel(row)} type={directionType(row.direcao)} /></span>
            <div style={{ color: Number(row.resultado) >= 0 ? C.teal : C.coral, fontFamily: mono, fontSize: 12, fontWeight: 800, textAlign: "right" }}>{pct(row.resultado)}</div>
          </button>
        );
      })}
    </div>
  );
}

function ActiveCoverageNotice({ activeRows }) {
  const activeRealEstate = activeRows.filter((row) => row.frente === "Imóveis").length;
  const activeB3AndCrypto = activeRows.length - activeRealEstate;

  if (activeRows.length === 0 || activeB3AndCrypto > 0 || activeRealEstate === 0) return null;

  return (
    <section data-testid="active-coverage-notice" style={{ background: C.panel, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.purple}`, borderRadius: 12, padding: "12px 14px" }}>
      <div style={{ color: C.text, fontSize: 13, fontWeight: 800, marginBottom: 5 }}>B3 e Cripto sem teses ativas</div>
      <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.55 }}>
        O monitor atual não trouxe B3 ou Cripto em go-live; por isso a tela mostra apenas os planos imobiliários em acompanhamento.
      </div>
    </section>
  );
}

function AttentionQueue({ rows, onSelect, selectedId }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
      {rows.slice(0, 4).map((row) => {
        const p0 = getP0Count(row);
        const severity = p0 || Number(row.resultado) < 0 || String(row.desfecho || "").toLowerCase().includes("stop") ? C.coral : C.amber;
        return (
          <button
            key={`attention-${row.id}`}
            type="button"
            aria-label={`Abrir tese em atenção ${row.ativo}`}
            data-testid={`teses-row-${row.id}`}
            onClick={() => onSelect(row)}
            style={{
              background: selectedId === row.id ? C.hover : C.panel,
              border: `1px solid ${C.border}`,
              borderLeft: `3px solid ${severity}`,
              borderRadius: 12,
              cursor: "pointer",
              fontFamily: "inherit",
              padding: 14,
              textAlign: "left",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 10 }}>
              <div style={{ color: C.text, fontSize: 13, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.ativo}</div>
              <Badge label={row.frente} type="info" />
            </div>
            <div style={{ color: severity, fontSize: 11, fontWeight: 800, lineHeight: 1.45 }}>{attentionReason(row)}</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
              <span data-testid={`direction-badge-${row.id}`}><Badge label={compactDirectionLabel(row)} type={directionType(row.direcao)} /></span>
              <Badge label={row.status} type={statusType(row.status)} />
            </div>
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 6 }}>{row.estrutura || row.hipotese}</div>
          </button>
        );
      })}
    </div>
  );
}

function DecisionActionCard({ accent, eyebrow, title, value, description, buttonLabel, onClick, children }) {
  return (
    <article style={{ background: `linear-gradient(145deg, ${withAlpha(accent, "14")}, ${C.panel})`, border: `1px solid ${withAlpha(accent, "35")}`, borderTop: `2px solid ${accent}`, borderRadius: 14, display: "flex", flexDirection: "column", gap: 12, minHeight: 174, overflow: "hidden", padding: 14, position: "relative" }}>
      <div style={{ position: "absolute", right: -34, top: -34, width: 112, height: 112, borderRadius: "50%", background: withAlpha(accent, "14") }} />
      <div style={{ position: "relative" }}>
        <div style={{ color: accent, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>{eyebrow}</div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
          <h3 style={{ color: C.text, fontSize: 14, fontWeight: 800, lineHeight: 1.25, margin: 0 }}>{title}</h3>
          <div style={{ color: accent, fontFamily: mono, fontSize: 22, fontWeight: 800, lineHeight: 1, whiteSpace: "nowrap" }}>{value}</div>
        </div>
      </div>
      <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0, minHeight: 34 }}>{description}</p>
      {children}
      <button type="button" onClick={onClick} style={{ alignSelf: "flex-start", background: withAlpha(accent, "18"), border: `1px solid ${withAlpha(accent, "45")}`, borderRadius: 9, color: accent, cursor: "pointer", fontFamily: mono, fontSize: 9, fontWeight: 800, letterSpacing: "0.06em", marginTop: "auto", padding: "8px 10px", textTransform: "uppercase" }}>
        {buttonLabel}
      </button>
    </article>
  );
}

function DecisionDesk({ activeRows, attentionRows, historicalRows, realEstateRows, onOpenActive, onOpenArchive, onSelectAttention }) {
  const firstAttention = attentionRows[0];
  const realEstateOpen = realEstateRows.filter((row) => isOpenThesis(row.status)).length;
  const activeB3AndCrypto = activeRows.filter((row) => row.frente !== "Imóveis").length;

  return (
    <section data-testid="decision-desk" style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 16, overflow: "hidden", padding: 18, position: "relative" }}>
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(circle at 12% 0%, ${withAlpha(C.gold, "10")}, transparent 34%), radial-gradient(circle at 90% 8%, ${withAlpha(C.sky, "10")}, transparent 30%)`, pointerEvents: "none" }} />
      <div style={{ position: "relative", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 18, marginBottom: 14 }}>
        <div>
          <div style={{ color: C.gold, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Mesa de decisão</div>
          <h2 style={{ color: C.text, fontSize: 18, fontWeight: 800, margin: 0 }}>Decisões agora</h2>
          <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: "6px 0 0", maxWidth: 720 }}>
            Primeiro o que pede ação. O arquivo completo continua disponível, mas não precisa ser o ponto de partida.
          </p>
        </div>
        <Badge label="Resumo antes da lista" type="info" />
      </div>

      <div style={{ position: "relative", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
        <DecisionActionCard
          accent={C.teal}
          eyebrow="Go-live"
          title="Acompanhamento ativo"
          value={activeRows.length}
          description={`${activeB3AndCrypto} teses de B3/Cripto e ${realEstateOpen} imóveis continuam em acompanhamento.`}
          buttonLabel="Ver acompanhamento ativo"
          onClick={onOpenActive}
        >
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Badge label="Planos vivos" type="open" />
            <Badge label="Sem arquivo" type="info" />
          </div>
        </DecisionActionCard>

        <DecisionActionCard
          accent={C.amber}
          eyebrow="Histórico"
          title="Lista completa"
          value={historicalRows.length}
          description="Use quando quiser auditar evidência linha a linha, filtrar frente ou conferir encerradas."
          buttonLabel="Abrir lista completa"
          onClick={onOpenArchive}
        >
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Badge label="Arquivo" type="closed" />
            <Badge label="Filtros" type="info" />
          </div>
        </DecisionActionCard>

        {firstAttention && (
          <DecisionActionCard
            accent={getP0Count(firstAttention) || Number(firstAttention.resultado) < 0 ? C.coral : C.gold}
            eyebrow="Primeiro olhar"
            title="Tese em atenção"
            value={firstAttention.frente}
            description={`${firstAttention.ativo}: ${attentionReason(firstAttention)}`}
            buttonLabel="Abrir tese em atenção"
            onClick={() => onSelectAttention(firstAttention)}
          >
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Badge label={compactDirectionLabel(firstAttention)} type={directionType(firstAttention.direcao)} />
              <Badge label={firstAttention.status} type={statusType(firstAttention.status)} />
            </div>
          </DecisionActionCard>
        )}
      </div>
    </section>
  );
}

function ArchivePrompt({ historicalCount, onOpen }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, padding: 16 }}>
      <div>
        <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>Arquivo histórico</div>
        <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, marginTop: 4 }}>
          {historicalCount.toLocaleString("pt-BR")} teses ficam guardadas como evidência. Abra só quando quiser investigar linha a linha.
        </div>
      </div>
      <button
        type="button"
        onClick={onOpen}
        style={{
          background: C.gold + "18",
          border: `1px solid ${C.gold + "45"}`,
          borderRadius: 10,
          color: C.gold,
          cursor: "pointer",
          fontFamily: "inherit",
          fontSize: 11,
          fontWeight: 800,
          letterSpacing: "0.06em",
          padding: "10px 12px",
          textTransform: "uppercase",
          whiteSpace: "nowrap",
        }}
      >
        Abrir arquivo completo
      </button>
    </div>
  );
}

function ThesesTable({ rows, selected, onSelect, decisionHeader, compactRealEstateTable }) {
  return (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden", position: "relative" }}>
      <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", position: "relative", zIndex: 2 }}>
        <div>
          <div style={{ color: C.muted, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase" }}>Lista de teses</div>
          <div style={{ color: C.text, fontWeight: 800, fontSize: 15, marginTop: 4 }}>Mapa operacional das teses</div>
          <div style={{ color: C.muted, fontSize: 11, marginTop: 3 }}>Cada linha mostra por que a tese existe, qual operação foi aberta e como ela deve sair.</div>
        </div>
      </div>
      <div data-testid="teses-table-wrapper" style={{ overflowX: compactRealEstateTable ? "hidden" : "auto", overflowY: "hidden", position: "relative", zIndex: 2 }}>
        <table data-testid="teses-table" style={{ width: "100%", minWidth: compactRealEstateTable ? 0 : 980, borderCollapse: "collapse", fontSize: 11, tableLayout: "fixed" }}>
          <colgroup>
            <col style={{ width: 70 }} />
            <col style={{ width: 128 }} />
            <col style={{ width: 260 }} />
            <col style={{ width: 132 }} />
            <col style={{ width: 230 }} />
            <col style={{ width: 140 }} />
            <col style={{ width: 90 }} />
          </colgroup>
          <thead>
            <tr style={{ background: C.panel }}>
              {["#", "Ativo", "Tese e motivo", "Operação e entrada", "Critério de saída", "Estado da tese", "Resultado"].map((h, index) => (
                <th
                  key={h}
                  data-testid={index === 0 ? "teses-header-id" : index === 1 ? "teses-header-asset" : undefined}
                  style={headerStyle(h, index)}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const result = Number(row.resultado);
              const resultColor = Number.isFinite(result) && result >= 0 ? C.teal : C.coral;
              const stickyBackground = selected?.id === row.id ? C.hover : C.card;
              const operation = usefulText(row.operation || row.estrutura, "Operação incompleta");
              const entryDate = entryDateLabel(row);
              const entryPrice = entryPriceLabel(row);
              const exitPlan = exitPlanText(row);
              const exitReference = exitReferenceText(row);
              const showExitReference = exitReference && !exitPlan.includes("R$") && compactExitRule(exitReference) !== compactExitRule(exitPlan);
              return (
                <tr data-testid={`teses-row-${row.id}`} key={row.id} onClick={() => onSelect(row)} style={{ borderBottom: `1px solid ${C.line}`, cursor: "pointer", background: selected?.id === row.id ? C.hover : "transparent" }}>
                  <Cell color={C.dim} numeric testId={`teses-cell-id-${row.id}`} style={stickyColumnStyle(0, stickyBackground, 4)}>{row.id}</Cell>
                  <Cell testId={`teses-cell-asset-${row.id}`} style={{ ...stickyColumnStyle(70, stickyBackground, 4), fontWeight: 700, minWidth: 120, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{row.ativo}</Cell>
                  <Cell>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
                      <Badge label={row.frente || "Frente"} type="info" />
                      <span data-testid={`direction-badge-${row.id}`}><Badge label={compactDirectionLabel(row)} type={directionType(row.direcao)} /></span>
                    </div>
                    <div style={{ color: C.text, fontSize: 11, fontWeight: 700, lineHeight: 1.45 }}>{usefulText(row.hipotese, "Motivo ainda não registrado")}</div>
                  </Cell>
                  <Cell>
                    <div style={{ color: C.text, fontSize: 11, fontWeight: 800, lineHeight: 1.35 }}>{operation}</div>
                    <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.45, marginTop: 6 }}>
                      Entrada {entryDate} · {entryPrice}
                    </div>
                  </Cell>
                  <Cell color={C.muted} style={{ fontSize: 10, lineHeight: 1.5, whiteSpace: "normal" }}>
                    <div style={{ color: C.text, fontWeight: 700 }}>{exitPlan}</div>
                    {showExitReference && <div style={{ color: C.muted, marginTop: 5 }}>{exitReference}</div>}
                  </Cell>
                  <Cell>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                      <Badge label={usefulText(row.status, "Sem status")} type={statusType(row.status)} />
                      <Badge label={usefulText(row.desfecho, "Sem desfecho")} type={row.desfecho === "Validada" ? "success" : row.desfecho === "Stop" ? "warning" : "neutral"} />
                    </div>
                    <div style={{ color: C.muted, fontFamily: mono, fontSize: 10, marginTop: 7 }}>{holdingPeriodLabel(row)}</div>
                  </Cell>
                  <Cell color={resultColor} numeric style={{ fontWeight: 800 }}>
                    <div>{pct(row.resultado)}</div>
                    <div style={{ color: C.muted, fontFamily: "inherit", fontSize: 9, fontWeight: 700, lineHeight: 1.35, marginTop: 5, textTransform: "uppercase" }}>{resultKindLabel(row)}</div>
                  </Cell>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const realEstateSectionIcons = {
  "Decisão do Radar": "📡",
  "Filtro HF: prédio": "🏢",
  "Prédio e condomínio": "🏙️",
  "Score Prédio Bom": "🏛️",
  "Checklist de visita HF": "📝",
  "Mapa de Assimetria": "🧭",
  "Score e Confiança": "📊",
  "Números da Operação": "💰",
  "Simular preço negociado": "🧮",
  "Cenários": "📐",
  "Pendências abertas": "⚠️",
  "Pontos já esclarecidos": "✅",
};

function RealEstateSection({ title, children, variant = "default" }) {
  const isRadar = variant === "radar";
  const icon = realEstateSectionIcons[title];

  return (
    <section
      style={{
        background: isRadar ? `linear-gradient(135deg, ${C.panel}, ${C.faint})` : C.panel,
        border: `1px solid ${C.border}`,
        borderTop: isRadar ? `2px solid ${C.amber}` : `1px solid ${C.border}`,
        borderRadius: 12,
        padding: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.text, fontSize: 13, fontWeight: 700, marginBottom: 12 }}>
        {icon && <span style={{ fontSize: 15, lineHeight: 1 }}>{icon}</span>}
        <span>{title}</span>
      </div>
      {children}
    </section>
  );
}

function DetailCell({ label, value, color = C.text, numeric = false, cardStyle = {}, labelColor = C.muted }) {
  return (
    <div style={{ background: C.faint, border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px", minWidth: 0, ...cardStyle }}>
      <div style={{ color: labelColor, fontSize: 9, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 5 }}>{label}</div>
      <div style={{ color, fontSize: 12, fontWeight: 700, fontFamily: numeric ? mono : "inherit", lineHeight: 1.35 }}>{value || "--"}</div>
    </div>
  );
}

function RadarDetailCell({ label, value, color = C.text, highlight = false }) {
  return (
    <DetailCell
      label={label}
      value={value}
      color={color}
      cardStyle={highlight ? { background: C.gold + "12", border: `1px solid ${C.gold + "30"}` } : undefined}
      labelColor={highlight ? C.gold : C.muted}
    />
  );
}

const hfBuildingPrinciple = "O que não pode ser melhorado tem que estar bom";

function plainText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function realEstateCandidatePayload(thesis) {
  const analysis = thesis?.realEstateAnalysis || {};
  return analysis.candidate || analysis.candidate_snapshot || analysis.candidateSnapshot || {};
}

function compactEvidenceText(value) {
  if (Array.isArray(value)) return value.filter(Boolean).join("; ");
  if (value && typeof value === "object") return Object.values(value).filter(Boolean).join("; ");
  return String(value || "");
}

function firstText(...values) {
  for (const value of values) {
    const text = compactEvidenceText(value).trim();
    if (text) return text;
  }
  return "";
}

function houseFlippingBuildingEvidence(thesis) {
  const analysis = thesis?.realEstateAnalysis || {};
  const candidate = realEstateCandidatePayload(thesis);
  return compactEvidenceText([
    candidate.building_condition,
    candidate.condo_condition,
    candidate.common_areas_condition,
    candidate.building_modernization,
    candidate.building_notes,
    candidate.condo_notes,
    analysis.building_condition,
    analysis.condo_condition,
    analysis.building_assessment,
    analysis.building_notes,
  ]);
}

function houseFlippingBuildingFit(thesis) {
  if (realEstateFrontKey(thesis) !== "flipping") return null;

  const evidence = houseFlippingBuildingEvidence(thesis);
  const text = plainText(`${evidence} ${searchableText(thesis)}`);
  const positiveTerms = [
    "bom estado",
    "bem cuidado",
    "organizado",
    "organizada",
    "modernizado",
    "modernizada",
    "fachada nova",
    "fachada reformada",
    "hall reformado",
    "hall modernizado",
    "elevador modernizado",
    "portaria organizada",
    "areas comuns boas",
    "areas comuns reformadas",
  ];
  const riskTerms = [
    "fachada ruim",
    "predio ruim",
    "sem elevador",
    "elevador antigo",
    "chamada extra",
    "inadimplencia",
    "infiltracao",
    "areas comuns ruins",
    "condominio problemático",
    "condominio problematico",
  ];
  const hasPositiveSignal = positiveTerms.some((term) => text.includes(term));
  const hasRiskSignal = riskTerms.some((term) => text.includes(term));

  if (hasRiskSignal) {
    return {
      label: "Prédio em atenção",
      color: C.amber,
      detail: "O apartamento pode ser reformável, mas o prédio ainda pode limitar a saída. Confirmar fachada, elevadores, portaria, chamadas extras e áreas comuns antes de avançar.",
      evidence: evidence || "Sem evidência objetiva registrada sobre o prédio.",
    };
  }

  if (hasPositiveSignal) {
    return {
      label: "Prédio favorável",
      color: C.teal,
      detail: "O prédio parece sustentar a tese: a reforma interna pode capturar valor sem carregar um problema que o comprador final enxergaria fora do apartamento.",
      evidence,
    };
  }

  return {
    label: "Prédio pendente",
    color: C.sky,
    detail: "Antes de visitar, precisamos validar se o que não conseguimos melhorar está bom: fachada, hall, elevadores, portaria, garagem e manutenção do condomínio.",
    evidence: evidence || "Ainda sem evidência sobre áreas comuns ou modernização do prédio.",
  };
}

function HouseFlippingBuildingFit({ thesis }) {
  const fit = houseFlippingBuildingFit(thesis);
  if (!fit) return null;

  return (
    <RealEstateSection title="Filtro HF: prédio" variant="radar">
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ background: C.bg + "80", border: `1px solid ${fit.color}40`, borderLeft: `4px solid ${fit.color}`, borderRadius: 10, padding: "10px 12px" }}>
          <div style={{ color: fit.color, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
            {fit.label}
          </div>
          <div style={{ color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.45 }}>
            {hfBuildingPrinciple}
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 7 }}>
            {fit.detail}
          </div>
        </div>
        <div style={{ background: C.faint, border: `1px solid ${C.border}`, borderRadius: 10, color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "9px 10px" }}>
          Evidência registrada: <span style={{ color: C.text, fontWeight: 700 }}>{fit.evidence}</span>
        </div>
      </div>
    </RealEstateSection>
  );
}

function buildingFieldStatus(value) {
  const text = plainText(value);
  if (!text || text.includes("pendente") || text.includes("nao informado") || text.includes("não informado")) return C.amber;
  if (text.includes("ruim") || text.includes("problema") || text.includes("chamada extra") || text.includes("infiltr")) return C.coral;
  if (text.includes("bom") || text.includes("boa") || text.includes("modern") || text.includes("organizado") || text.includes("organizada") || text.includes("funcional")) return C.teal;
  return C.sky;
}

function buildingCondoFields(thesis) {
  const analysis = thesis?.realEstateAnalysis || {};
  const candidate = realEstateCandidatePayload(thesis);
  const field = (...keys) => {
    const values = keys.flatMap((key) => [candidate[key], analysis[key]]);
    return firstText(...values) || "Pendente";
  };

  return [
    { label: "Perfil do prédio", value: field("building_age_profile", "buildingAgeProfile", "age_profile") },
    { label: "Fachada", value: field("facade_condition", "facadeCondition") },
    { label: "Hall", value: field("hall_condition", "hallCondition") },
    { label: "Elevadores", value: field("elevators_condition", "elevator_condition", "elevatorsCondition", "elevatorCondition") },
    { label: "Portaria", value: field("concierge_condition", "portaria_condition", "conciergeCondition", "portariaCondition") },
    { label: "Garagem", value: field("garage_condition", "garageCondition") },
    { label: "Condomínio", value: field("condo_condition", "condominium_condition", "condoCondition", "condominiumCondition") },
    { label: "Chamada extra", value: field("extra_fee_status", "special_assessment_status", "extraFeeStatus", "specialAssessmentStatus") },
    { label: "AVCB", value: field("avcb_status", "avcbStatus") },
  ];
}

function BuildingCondoStructuredFields({ thesis }) {
  if (thesis?.frente !== "Imóveis") return null;
  const fields = buildingCondoFields(thesis);

  return (
    <RealEstateSection title="Prédio e condomínio" variant="radar">
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.55 }}>
          Campos que viram evidência objetiva do HF: o apartamento muda por obra; o prédio precisa sustentar a venda desde o começo.
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))", gap: 10 }}>
          {fields.map((item) => (
            <DetailCell
              key={item.label}
              label={item.label}
              value={item.value}
              color={buildingFieldStatus(item.value)}
            />
          ))}
        </div>
      </div>
    </RealEstateSection>
  );
}

function buildingFieldKind(value) {
  const color = buildingFieldStatus(value);
  if (color === C.teal) return "strong";
  if (color === C.coral) return "risk";
  if (color === C.amber) return "pending";
  return "neutral";
}

function goodBuildingScore(thesis) {
  if (realEstateFrontKey(thesis) !== "flipping") return null;
  const fields = buildingCondoFields(thesis);
  const stats = fields.reduce((acc, field) => {
    const kind = buildingFieldKind(field.value);
    acc[kind] = (acc[kind] || 0) + 1;
    return acc;
  }, { strong: 0, neutral: 0, pending: 0, risk: 0 });
  const rawScore = 45 + stats.strong * 7 + stats.neutral * 3 - stats.pending * 4 - stats.risk * 12;
  const score = Math.max(0, Math.min(100, Math.round(rawScore)));
  const label = score >= 75
    ? "Sustenta a tese HF"
    : score >= 55
      ? "Pede validação antes da visita"
      : "Enfraquece a tese HF";
  const color = score >= 75 ? C.teal : score >= 55 ? C.amber : C.coral;

  return { score, label, color, stats };
}

function GoodBuildingScore({ thesis }) {
  const result = goodBuildingScore(thesis);
  if (!result) return null;

  return (
    <RealEstateSection title="Score Prédio Bom" variant="radar">
      <div style={{ display: "grid", gridTemplateColumns: "minmax(140px, 0.7fr) minmax(180px, 1fr)", gap: 12, alignItems: "stretch" }}>
        <div style={{ background: result.color + "12", border: `1px solid ${result.color}40`, borderLeft: `4px solid ${result.color}`, borderRadius: 12, padding: "12px 13px" }}>
          <div style={{ color: result.color, fontFamily: mono, fontSize: 28, fontWeight: 900, lineHeight: 1 }}>
            {result.score}/100
          </div>
          <div style={{ color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.35, marginTop: 8 }}>
            {result.label}
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, marginTop: 7 }}>
            Quanto maior a nota, mais o prédio ajuda a tese de reforma interna.
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <DetailCell label="Itens fortes" value={`Itens fortes: ${result.stats.strong}`} color={C.teal} />
          <DetailCell label="Pendências" value={`Pendências: ${result.stats.pending}`} color={C.amber} />
          <DetailCell label="Riscos" value={`Riscos: ${result.stats.risk}`} color={result.stats.risk ? C.coral : C.teal} />
          <DetailCell label="Neutros" value={`Neutros: ${result.stats.neutral}`} color={C.sky} />
        </div>
      </div>
    </RealEstateSection>
  );
}

const houseFlippingVisitChecklist = [
  {
    title: "Apartamento",
    detail: "Verificar elétrica, hidráulica, piso, janelas, infiltração, luz natural e ruído.",
    action: "Registrar fotos de cozinha, banheiro, quadro de luz, paredes com umidade e vista.",
    color: C.teal,
  },
  {
    title: "Prédio",
    detail: "Fotografar fachada, hall, elevadores, garagem, portaria e áreas comuns.",
    action: "Validar se o que não pode ser melhorado já está bom.",
    color: C.sky,
  },
  {
    title: "Corretor / vendedor",
    detail: "Confirmar motivo da venda, abertura para proposta, prazo, documentação e chamadas extras.",
    action: "Perguntar condomínio, IPTU, matrícula, obras aprovadas e histórico de preço.",
    color: C.amber,
  },
];

function visitEvidenceEntries(thesis) {
  const analysis = thesis?.realEstateAnalysis || {};
  const candidate = realEstateCandidatePayload(thesis);
  return [
    ...(Array.isArray(analysis.visit_evidence) ? analysis.visit_evidence : []),
    ...(Array.isArray(candidate.visit_evidence) ? candidate.visit_evidence : []),
  ];
}

function visitEvidenceBySection(thesis) {
  return visitEvidenceEntries(thesis).reduce((acc, item) => {
    const section = String(item?.section || item?.title || "").trim();
    const evidence = String(item?.evidence || item?.text || item?.value || "").trim();
    if (section && evidence) acc[section] = evidence;
    return acc;
  }, {});
}

function HouseFlippingVisitChecklist({ thesis, onRefresh }) {
  const persistedEvidence = useMemo(() => visitEvidenceBySection(thesis), [thesis]);
  const [drafts, setDrafts] = useState({});
  const [saved, setSaved] = useState(persistedEvidence);
  const [saving, setSaving] = useState({});
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setSaved(persistedEvidence);
  }, [persistedEvidence]);

  if (realEstateFrontKey(thesis) !== "flipping") return null;

  async function handleSave(title) {
    const value = String(drafts[title] || "").trim();
    if (!value) return;
    setSaving((current) => ({ ...current, [title]: true }));
    setErrors((current) => ({ ...current, [title]: "" }));
    try {
      await saveRealEstateVisitEvidence({
        thesisId: thesis.thesisId,
        section: title,
        evidence: value,
      });
      setSaved((current) => ({ ...current, [title]: value }));
      await onRefresh?.();
    } catch (error) {
      setErrors((current) => ({
        ...current,
        [title]: error instanceof Error ? error.message : "Nao foi possivel registrar a evidencia.",
      }));
    } finally {
      setSaving((current) => ({ ...current, [title]: false }));
    }
  }

  return (
    <RealEstateSection title="Checklist de visita HF" variant="radar">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
        {houseFlippingVisitChecklist.map((item) => (
          <div key={item.title} style={{ background: `linear-gradient(180deg, ${item.color}10, ${C.faint})`, border: `1px solid ${item.color}35`, borderLeft: `4px solid ${item.color}`, borderRadius: 12, padding: "12px 13px", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ color: item.color, fontSize: 13, fontWeight: 800 }}>{item.title}</div>
            <div style={{ color: C.text, fontSize: 12, fontWeight: 700, lineHeight: 1.5 }}>{item.detail}</div>
            <div style={{ background: C.bg + "70", border: `1px solid ${C.border}`, borderRadius: 9, color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: "auto", padding: "8px 9px" }}>
              {item.action}
            </div>
            <label style={{ color: C.muted, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Evidência da visita: {item.title}
              <textarea
                aria-label={`Evidência da visita: ${item.title}`}
                value={drafts[item.title] || ""}
                onChange={(event) => setDrafts((current) => ({ ...current, [item.title]: event.target.value }))}
                rows={2}
                placeholder="Registre fotos, observações ou resposta do corretor..."
                style={{
                  background: C.bg,
                  border: `1px solid ${C.border}`,
                  borderRadius: 8,
                  boxSizing: "border-box",
                  color: C.text,
                  display: "block",
                  fontFamily: "inherit",
                  fontSize: 12,
                  lineHeight: 1.45,
                  marginTop: 6,
                  outline: "none",
                  padding: "8px 10px",
                  resize: "vertical",
                  width: "100%",
                }}
              />
            </label>
            <button
              type="button"
              aria-label={`Registrar evidência ${item.title}`}
              onClick={() => handleSave(item.title)}
              disabled={Boolean(saving[item.title])}
              style={{
                background: item.color,
                border: 0,
                borderRadius: 8,
                color: C.bg,
                cursor: saving[item.title] ? "wait" : "pointer",
                fontFamily: "inherit",
                fontSize: 11,
                fontWeight: 800,
                opacity: saving[item.title] ? 0.7 : 1,
                padding: "8px 10px",
              }}
            >
              {saving[item.title] ? "Registrando..." : "Registrar evidência"}
            </button>
            {errors[item.title] && (
              <div style={{ background: C.coral + "10", border: `1px solid ${C.coral}35`, borderRadius: 9, color: C.coral, fontSize: 11, lineHeight: 1.45, padding: "8px 9px" }}>
                {errors[item.title]}
              </div>
            )}
            {saved[item.title] && (
              <div style={{ background: C.green + "10", border: `1px solid ${C.green}35`, borderRadius: 9, color: C.text, fontSize: 11, lineHeight: 1.45, padding: "8px 9px" }}>
                <span style={{ color: C.green, fontWeight: 800 }}>Evidência registrada</span>: {saved[item.title]}
              </div>
            )}
          </div>
        ))}
      </div>
    </RealEstateSection>
  );
}

function firstNumber(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number) && number > 0) return number;
  }
  return 0;
}

function realEstateAsymmetry(thesis) {
  if (thesis?.frente !== "Imóveis") return null;

  const analysis = thesis.realEstateAnalysis || {};
  const candidate = realEstateCandidatePayload(thesis);
  const purchasePrice = firstNumber(thesis.entrada, analysis.ask_price, analysis.entry_price, candidate.price, candidate.ask_price);
  const renovationCost = firstNumber(
    analysis.renovation_budget,
    analysis.renovationBudget,
    analysis.reform_budget,
    analysis.reformBudget,
    candidate.renovation_budget,
    candidate.renovationBudget,
    candidate.reform_budget,
    candidate.reformBudget,
  );
  const transactionCosts = firstNumber(
    analysis.transaction_costs,
    analysis.transactionCosts,
    analysis.operational_costs,
    analysis.operationalCosts,
    candidate.transaction_costs,
    candidate.transactionCosts,
    candidate.operational_costs,
    candidate.operationalCosts,
  );
  const salePrice = firstNumber(
    analysis.scenarios?.base?.sale_price,
    analysis.scenarios?.base?.salePrice,
    analysis.estimated_sale_base,
    analysis.estimatedSaleBase,
    candidate.estimated_sale_base,
    candidate.estimatedSaleBase,
    thesis.valorReferencia,
  );

  if (purchasePrice <= 0 || salePrice <= 0) return null;

  const totalProjectCost = purchasePrice + renovationCost + transactionCosts;
  const estimatedMargin = salePrice - totalProjectCost;
  const downPayment = purchasePrice * 0.2;
  const financedDebt = purchasePrice * 0.8;
  const financedCashNeeded = downPayment + renovationCost + transactionCosts;
  const cashRoi = financedCashNeeded > 0 ? (estimatedMargin / financedCashNeeded) * 100 : 0;
  const projectRoi = totalProjectCost > 0 ? (estimatedMargin / totalProjectCost) * 100 : 0;

  return {
    purchasePrice,
    renovationCost,
    transactionCosts,
    salePrice,
    totalProjectCost,
    estimatedMargin,
    downPayment,
    financedDebt,
    financedCashNeeded,
    cashRoi,
    projectRoi,
  };
}

function AsymmetryMetric({ label, value, color = C.text, sub }) {
  return (
    <div style={{ background: C.faint, border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px" }}>
      <div style={{ color: C.muted, fontSize: 9, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 5 }}>{label}</div>
      <div style={{ color, fontFamily: mono, fontSize: 13, fontWeight: 800 }}>{value}</div>
      {sub && <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.45, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function RealEstateAsymmetryMap({ thesis }) {
  const map = realEstateAsymmetry(thesis);
  if (!map) return null;

  const marginColor = map.estimatedMargin >= 0 ? C.teal : C.coral;

  return (
    <RealEstateSection title="Mapa de Assimetria" variant="radar">
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.55 }}>
          Compara compra, reforma e custos contra a venda base. A leitura financiada mostra o caixa necessário usando 20% de entrada.
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))", gap: 10 }}>
          <AsymmetryMetric label="Compra" value={moneyCompact(map.purchasePrice)} numeric />
          <AsymmetryMetric label="Reforma" value={moneyCompact(map.renovationCost)} color={C.amber} />
          <AsymmetryMetric label="Custos" value={moneyCompact(map.transactionCosts)} color={C.sky} />
          <AsymmetryMetric label="Venda base" value={moneyCompact(map.salePrice)} color={C.gold} />
          <AsymmetryMetric label="Custo total" value={moneyCompact(map.totalProjectCost)} />
          <AsymmetryMetric label="Margem estimada" value={moneyCompact(map.estimatedMargin)} color={marginColor} sub={`ROI projeto: ${pct(map.projectRoi)}`} />
        </div>
        <div style={{ background: C.gold + "12", border: `1px solid ${C.gold}35`, borderLeft: `4px solid ${C.gold}`, borderRadius: 10, padding: "10px 12px" }}>
          <div style={{ color: C.gold, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 7 }}>
            Financiamento 20% entrada
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 8 }}>
            <div style={{ color: C.text, fontSize: 12, fontWeight: 800 }}>Caixa estimado: {moneyCompact(map.financedCashNeeded)}</div>
            <div style={{ color: C.text, fontSize: 12, fontWeight: 800 }}>Dívida financiada: {moneyCompact(map.financedDebt)}</div>
            <div style={{ color: marginColor, fontSize: 12, fontWeight: 800 }}>Margem estimada: {moneyCompact(map.estimatedMargin)}</div>
            <div style={{ color: C.muted, fontSize: 12, fontWeight: 700 }}>ROI sobre caixa: {pct(map.cashRoi)}</div>
          </div>
        </div>
      </div>
    </RealEstateSection>
  );
}

function formatUpdateDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DataOriginPanel({ feedStatus = "fallback", updatedAt, compact = false }) {
  const isLive = feedStatus === "live";
  const statusLabel = isLive ? "API real" : feedStatus === "fallback" ? "Fallback temporário" : "Mock temporário";
  const accent = isLive ? C.teal : C.amber;

  return (
    <section
      data-testid={compact ? "data-origin-panel-compact" : "data-origin-panel"}
      style={{
        background: compact ? C.faint : C.card,
        border: `1px solid ${accent}35`,
        borderLeft: `3px solid ${accent}`,
        borderRadius: 12,
        padding: compact ? "10px 12px" : "12px 14px",
        display: "flex",
        flexDirection: compact ? "column" : "row",
        alignItems: compact ? "flex-start" : "center",
        justifyContent: "space-between",
        gap: 10,
        flexWrap: "wrap",
      }}
    >
      <div>
        <div style={{ color: C.text, fontSize: 13, fontWeight: 800 }}>Origem dos dados</div>
        <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, marginTop: 4 }}>
          Fonte oficial da tela: <span style={{ color: C.sky, fontFamily: mono }}>/api/dashboard/summary/1</span>
        </div>
      </div>
      <div style={{ display: "flex", gap: 7, flexWrap: "wrap", alignItems: "center" }}>
        <Badge label={statusLabel} type={isLive ? "open" : "warning"} />
        <span style={{ color: C.purple, fontFamily: mono, fontSize: 10, fontWeight: 800 }}>thesis_open_operations</span>
        <span style={{ color: C.muted, fontFamily: mono, fontSize: 10 }}>{formatUpdateDate(updatedAt)}</span>
      </div>
    </section>
  );
}

function GaugeCircle({ label, value, color, help, testId, valueTestId }) {
  const score = Math.max(0, Math.min(100, Number(value) || 0));
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div
      data-testid={testId}
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        padding: 14,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        minWidth: 0,
      }}
    >
      <svg width="132" height="132" viewBox="0 0 132 132" role="img" aria-label={`${label}: ${score} de 100`}>
        <circle cx="66" cy="66" r={radius} fill="none" stroke={C.border} strokeWidth="10" />
        <circle
          cx="66"
          cy="66"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 66 66)"
        />
        <text
          data-testid={valueTestId}
          x="66"
          y="63"
          textAnchor="middle"
          fill={color}
          fontFamily={mono}
          fontSize="24"
          fontWeight="700"
        >
          {score}
        </text>
        <text x="66" y="82" textAnchor="middle" fill={C.muted} fontFamily={mono} fontSize="11" fontWeight="700">
          /100
        </text>
      </svg>
      <div style={{ color: C.text, fontSize: 12, fontWeight: 700, textAlign: "center" }}>{label}</div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, textAlign: "center" }}>{help}</div>
    </div>
  );
}

function RealEstateScoreHero({ analysis }) {
  const score = Math.max(0, Math.min(100, Number(analysis.score) || 0));
  const confidence = Math.max(0, Math.min(100, Number(analysis.confidence) || 0));
  const scoreColor = score >= 70 ? C.teal : score >= 55 ? C.amber : C.coral;
  const confidenceColor = C.sky;

  return (
    <section
      data-testid="real-estate-score-hero"
      style={{
        background: C.faint,
        border: `1px solid ${C.gold + "45"}`,
        borderTop: `2px solid ${C.gold}`,
        borderRadius: 14,
        padding: "16px 18px",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.text, fontSize: 13, fontWeight: 700, marginBottom: 2 }}>
        <span style={{ fontSize: 15, lineHeight: 1 }}>📊</span>
        <span>Score e Confiança</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <GaugeCircle
          label="Score do candidato"
          value={score}
          color={scoreColor}
          help="Qualidade potencial do negócio."
          testId="real-estate-score-gauge"
          valueTestId="real-estate-score-value"
        />
        <GaugeCircle
          label="Confiança da análise"
          value={confidence}
          color={confidenceColor}
          help="Quanto da análise já está comprovada."
          testId="real-estate-confidence-gauge"
          valueTestId="real-estate-confidence-value"
        />
      </div>
    </section>
  );
}

function realEstateJaneComment(thesis) {
  const analysis = thesis.realEstateAnalysis || {};
  const p0 = (analysis.pending_items || []).filter((item) => item.priority === "P0");
  const p0Titles = p0
    .slice(0, 3)
    .map((item) =>
      String(item.title || "")
        .toLowerCase()
        .replace(/^(confirmar|buscar|validar|conferir)\s+/i, "")
        .replace("ocupacao", "ocupação")
        .replace("matricula", "matrícula")
        .replace("onus", "ônus"),
    )
    .filter(Boolean);
  const requiredChecks = p0Titles.length ? p0Titles.join(", ") : "ocupação, matrícula e débitos";
  const ceiling = String(analysis.price_ceiling_status || "").toLowerCase();

  if (p0.length > 0) {
    return `Este imóvel só deve avançar depois das pendências P0. Antes de qualquer proposta, confirme ${requiredChecks}. O preço está ${ceiling || "em análise"}; o plano pede ${String(analysis.next_action || "nova verificação documental").toLowerCase()}.`;
  }

  return `Este imóvel não tem pendência P0 bloqueando a decisão. Antes de proposta, confirme as premissas P1 e o preço teto; o plano pede ${String(analysis.next_action || "registrar nova evidência").toLowerCase()}.`;
}

function PatrickJaneTextInsight({ message }) {
  return (
    <section style={{ background: C.sky + "10", border: `1px solid ${C.sky + "35"}`, borderLeft: `3px solid ${C.sky}`, borderRadius: 12, padding: "12px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
        <span style={{ color: C.text, fontSize: 13, fontWeight: 700 }}>Patrick Jane</span>
        <Badge label="Observando" type="info" />
      </div>
      <div style={{ color: C.sky, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: mono, marginBottom: 6 }}>
        Comentário sobre o imóvel selecionado
      </div>
      <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.6 }}>{message}</div>
    </section>
  );
}

function ScenarioCard({ label, scenario }) {
  return (
    <div style={{ background: C.faint, border: `1px solid ${C.border}`, borderTop: `2px solid ${C.gold}`, borderRadius: 10, padding: 12 }}>
      <div style={{ color: C.gold, fontSize: 11, fontWeight: 700, marginBottom: 8 }}>{label}</div>
      <div style={{ display: "grid", gap: 6 }}>
        <DetailCell label="Venda estimada" value={money(scenario?.sale_price)} numeric />
        <DetailCell label="Lucro líquido" value={money(scenario?.net_profit)} color={Number(scenario?.net_profit) >= 0 ? C.teal : C.coral} numeric />
        <DetailCell label="ROI" value={pct(scenario?.roi_pct)} color={Number(scenario?.roi_pct) >= 0 ? C.teal : C.coral} numeric />
      </div>
    </div>
  );
}

function RealEstateSourceMeta({ thesis }) {
  if (!thesis.sourceUrl) return null;

  const host = sourceHost(thesis.sourceUrl);

  return (
    <div style={{ background: C.gold + "10", border: `1px solid ${C.gold}35`, borderRadius: 10, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 7 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        <Badge label="Caso real em estudo" type="high" />
        <span style={{ color: C.muted, fontSize: 11 }}>Não é recomendação; é material de análise.</span>
      </div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>
        Fonte: <span style={{ color: C.text, fontWeight: 700 }}>{host || "--"}</span>
      </div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>
        Coleta: <span style={{ color: C.text, fontWeight: 700 }}>{formatDate(thesis.openedAt)}</span>
      </div>
    </div>
  );
}

function NegotiationSimulator({ thesis, analysis }) {
  const [discount, setDiscount] = useState(5);
  const askingPrice = Number(thesis.entrada);
  const maxPurchasePrice = Number(analysis.max_purchase_price);

  if (!Number.isFinite(askingPrice) || askingPrice <= 0 || !Number.isFinite(maxPurchasePrice) || maxPurchasePrice <= 0) {
    return null;
  }

  const negotiatedPrice = askingPrice * (1 - discount / 100);
  const gapToCeiling = maxPurchasePrice - negotiatedPrice;
  const gapText = gapToCeiling >= 0
    ? `${moneyPrecise(gapToCeiling)} abaixo do teto`
    : `${moneyPrecise(Math.abs(gapToCeiling))} acima do teto`;
  const gapColor = gapToCeiling >= 0 ? C.teal : C.coral;

  return (
    <RealEstateSection title="Simular preço negociado" variant="radar">
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.5 }}>
          Teste rapidamente se uma proposta com desconto aproxima o imóvel do teto calculado pelo radar.
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {[5, 10, 15].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setDiscount(item)}
              style={{
                background: discount === item ? C.gold : C.bg,
                border: `1px solid ${discount === item ? C.gold : C.border}`,
                borderRadius: 999,
                color: discount === item ? C.bg : C.muted,
                cursor: "pointer",
                fontFamily: mono,
                fontSize: 11,
                fontWeight: 800,
                padding: "6px 10px",
              }}
            >
              -{item}%
            </button>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <DetailCell label="Preço simulado" value={moneyPrecise(negotiatedPrice)} color={C.gold} numeric />
          <DetailCell label="Distância do teto" value={gapText} color={gapColor} numeric />
          <DetailCell label="Preço pedido" value={moneyPrecise(askingPrice)} numeric />
          <DetailCell label="Teto de compra" value={moneyPrecise(maxPurchasePrice)} color={C.amber} numeric />
        </div>
      </div>
    </RealEstateSection>
  );
}

function PendingResolutionCard({ item, color, thesis, onResolved }) {
  const [evidence, setEvidence] = useState("");
  const [state, setState] = useState("idle");
  const [message, setMessage] = useState("");
  const title = item.title || "Pendencia";
  const disabled = state === "saving";
  const isP0 = item.priority === "P0";
  const priorityLabel = isP0 ? "Bloqueia decisão" : "Melhora análise";

  async function handleSubmit() {
    const trimmed = evidence.trim();
    if (!trimmed) {
      setState("error");
      setMessage("Informe a evidencia antes de fechar a pendencia.");
      return;
    }

    setState("saving");
    setMessage("");
    try {
      await resolveRealEstatePending({ thesisId: thesis.thesisId, item, evidence: trimmed });
      setState("saved");
      setMessage("Registrado. O radar vai recalcular esta tese.");
      await onResolved?.();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Nao foi possivel registrar agora.");
    }
  }

  return (
    <div
      style={{
        background: `linear-gradient(180deg, ${color}12, ${C.faint})`,
        border: `1px solid ${color}45`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 12,
        boxShadow: `0 14px 30px ${C.bg}30`,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        minHeight: 232,
        padding: "12px 13px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ color, fontFamily: mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", marginBottom: 6 }}>{item.priority}</div>
          <div style={{ color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.35 }}>{title}</div>
        </div>
        <span
          style={{
            background: color + "18",
            border: `1px solid ${color}50`,
            borderRadius: 999,
            color,
            flexShrink: 0,
            fontSize: 9,
            fontWeight: 800,
            letterSpacing: "0.05em",
            padding: "4px 7px",
            textTransform: "uppercase",
          }}
        >
          {priorityLabel}
        </span>
      </div>
      <div style={{ background: C.bg + "70", border: `1px solid ${C.border}`, borderRadius: 9, color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "8px 9px" }}>Ação: {item.action}</div>
      <div style={{ display: "grid", gap: 8, marginTop: "auto" }}>
        <label style={{ color: C.muted, fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Evidência para fechar
          <textarea
            aria-label={`Evidencia para ${title}`}
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
            rows={2}
            placeholder="Ex.: matrícula baixada, ocupação confirmada, 3 comparáveis encontrados..."
            style={{
              background: C.bg,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              boxSizing: "border-box",
              color: C.text,
              display: "block",
              fontFamily: "inherit",
              fontSize: 12,
              lineHeight: 1.45,
              marginTop: 6,
              outline: "none",
              padding: "8px 10px",
              resize: "vertical",
              width: "100%",
            }}
          />
        </label>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <button
            type="button"
            aria-label={`Registrar e fechar ${title}`}
            onClick={handleSubmit}
            disabled={disabled}
            style={{
              background: disabled ? C.border : color,
              border: 0,
              borderRadius: 8,
              color: disabled ? C.muted : C.bg,
              cursor: disabled ? "wait" : "pointer",
              fontFamily: "inherit",
              fontSize: 11,
              fontWeight: 800,
              padding: "8px 10px",
            }}
          >
            {disabled ? "Registrando..." : "Registrar e fechar"}
          </button>
          {message && <span style={{ color: state === "saved" ? C.green : C.amber, fontSize: 11, fontWeight: 700 }}>{message}</span>}
        </div>
      </div>
    </div>
  );
}

function PendingGroup({ title, items, color, thesis, onResolved }) {
  if (!items.length) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
      <div style={{ color, fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>{title}</div>
      <div
        data-testid={`pending-grid-${items[0]?.priority || title}`}
        style={{
          display: "grid",
          gap: 10,
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        }}
      >
        {items.map((item) => (
          <PendingResolutionCard
            key={`${item.priority}-${item.key || item.title}`}
            item={item}
            color={color}
            thesis={thesis}
            onResolved={onResolved}
          />
        ))}
      </div>
    </div>
  );
}

const dossierGridStyle = {
  display: "grid",
  gap: 10,
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
};

function EmptyDossierCard({ message }) {
  return (
    <div style={{ background: C.faint, border: `1px dashed ${C.border}`, borderRadius: 12, color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "12px 13px" }}>
      {message}
    </div>
  );
}

function ClarifiedItemsGrid({ items }) {
  const rows = items || [];
  if (!rows.length) return <EmptyDossierCard message="Nenhuma evidência esclarecida ainda." />;

  return (
    <div data-testid="clarified-grid" style={dossierGridStyle}>
      {rows.map((item, index) => (
        <div
          key={`${item.title}-${index}`}
          data-testid={`clarified-card-${index}`}
          style={{
            background: `linear-gradient(180deg, ${C.green}10, ${C.faint})`,
            border: `1px solid ${C.green}35`,
            borderLeft: `4px solid ${C.green}`,
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            minHeight: 118,
            padding: "12px 13px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
            <div style={{ color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.35 }}>{item.title}</div>
            <span style={{ background: C.green + "18", border: `1px solid ${C.green}45`, borderRadius: 999, color: C.green, flexShrink: 0, fontSize: 9, fontWeight: 800, letterSpacing: "0.05em", padding: "4px 7px", textTransform: "uppercase" }}>
              Evidencia confirmada
            </span>
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>{item.detail}</div>
        </div>
      ))}
    </div>
  );
}

function BreakdownRows({ rows, accent, showStatus = false, testIdPrefix = "breakdown" }) {
  const items = rows || [];
  if (!items.length) return <EmptyDossierCard message="Sem critérios registrados para esta análise." />;

  return (
    <div data-testid={`${testIdPrefix}-grid`} style={dossierGridStyle}>
      {items.map((item, index) => {
        const points = Number(item.points) || 0;
        const max = Number(item.max_points) || 0;
        const width = max > 0 ? Math.max(0, Math.min(100, (points / max) * 100)) : 0;
        return (
          <div
            key={`${item.label}-${item.points}-${index}`}
            data-testid={`${testIdPrefix}-card-${index}`}
            style={{
              background: `linear-gradient(180deg, ${accent}10, ${C.faint})`,
              border: `1px solid ${accent}35`,
              borderTop: `3px solid ${accent}`,
              borderRadius: 12,
              display: "flex",
              flexDirection: "column",
              gap: 9,
              minHeight: 132,
              padding: "12px 13px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.35 }}>{item.label}</div>
                <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.4, marginTop: 3 }}>Critério da análise</div>
              </div>
              <span style={{ background: accent + "18", border: `1px solid ${accent}45`, borderRadius: 999, color: accent, flexShrink: 0, fontFamily: mono, fontSize: 10, fontWeight: 800, padding: "4px 7px" }}>
                {points}/{max}
              </span>
            </div>
            <div style={{ height: 7, background: C.bg, borderRadius: 999, overflow: "hidden", border: `1px solid ${C.border}` }}>
              <div data-testid={`${testIdPrefix}-fill-${index}`} style={{ width: `${width}%`, height: "100%", background: accent, borderRadius: 999 }} />
            </div>
            {showStatus && <div><Badge label={item.status || "sem status"} type={item.status === "pendente" ? "warning" : item.status === "esclarecido" ? "success" : "info"} /></div>}
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>{item.detail}</div>
          </div>
        );
      })}
    </div>
  );
}

function RealEstateGuidedJourney({ thesis, analysis, p0, p1 }) {
  const building = goodBuildingScore(thesis);
  const candidate = realEstateCandidatePayload(thesis);
  const evidenceSections = new Set(visitEvidenceEntries(thesis).map((item) => String(item.section || "").trim()).filter(Boolean));
  const evidenceCount = Math.min(3, evidenceSections.size);
  const score = Math.max(0, Math.min(100, Number(analysis.score) || 0));
  const confidence = Math.max(0, Math.min(100, Number(analysis.confidence) || 0));
  const priceStatus = String(analysis.price_ceiling_status || "Preço em validação");
  const priceColor = priceStatus === "Acima do teto" ? C.coral : C.teal;
  const nextAction = analysis.next_action || "Registrar próxima evidência";
  const isFlipping = realEstateFrontKey(thesis) === "flipping";
  const suggestedStatus = analysis.suggested_status || thesis.desfecho || "Em análise";
  const renovationAnswer = firstText(
    analysis.renovation_type,
    candidate.renovation_type,
    candidate.renovationBudget && money(candidate.renovationBudget),
    candidate.renovation_budget && money(candidate.renovation_budget),
    "Orçamento pendente",
  );
  const blockers = [
    p0.length ? `${p0.length} P0 bloqueando decisão` : "",
    priceStatus === "Acima do teto" ? "Preço acima do teto" : "",
    building?.score < 55 ? "Prédio enfraquece o HF" : "",
    confidence < 50 ? "Confiança baixa" : "",
    isFlipping && evidenceCount < 3 ? "Visita HF incompleta" : "",
  ].filter(Boolean);
  const nodes = [
    {
      number: "01",
      title: "Tese",
      question: "Por que entrou no radar?",
      detail: thesis.hipotese || suggestedStatus,
      status: score ? `Score ${score}/100` : "Score pendente",
      color: score >= 70 ? C.teal : score >= 55 ? C.amber : C.coral,
    },
    {
      number: "02",
      title: "Prédio",
      question: "O que não pode ser melhorado está bom?",
      detail: building?.label || "Contexto do imóvel pendente",
      status: building ? `${building.score}/100` : "pendente",
      color: building?.color || C.sky,
    },
    {
      number: "03",
      title: "Reforma",
      question: "A obra cria valor sem virar reforma pesada?",
      detail: renovationAnswer,
      status: `${evidenceCount}/3 evidências`,
      color: evidenceCount >= 3 ? C.green : C.amber,
    },
    {
      number: "04",
      title: "Números",
      question: "O preço respeita o teto e a margem?",
      detail: priceStatus,
      status: money(analysis.max_purchase_price),
      color: priceColor,
    },
    {
      number: "05",
      title: "Decisão",
      question: "Qual é o próximo movimento?",
      detail: p0.length ? "Não avançar antes dos bloqueios" : nextAction,
      status: p0.length ? `${p0.length} P0` : `${p1.length} P1`,
      color: p0.length ? C.coral : C.teal,
    },
  ];

  return (
    <section
      data-testid="real-estate-decision-map"
      style={{
        background: `radial-gradient(circle at top left, ${C.gold}22, transparent 36%), linear-gradient(135deg, ${C.panel}, ${C.faint})`,
        border: `1px solid ${C.gold}45`,
        borderTop: `2px solid ${C.gold}`,
        borderRadius: 18,
        boxShadow: `0 18px 40px ${C.bg}30`,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        padding: "16px 17px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>
            Mapa mental da decisão
          </div>
          <div style={{ color: C.text, fontSize: 18, fontWeight: 950, lineHeight: 1.15 }}>Este imóvel deve avançar?</div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 6, maxWidth: 520 }}>
            Primeiro entenda a decisão. Depois abra os detalhes técnicos só quando eles ajudarem a responder a pergunta central.
          </div>
        </div>
        <div style={{ alignSelf: "stretch", background: C.bg + "92", border: `1px solid ${C.gold}35`, borderRadius: 13, minWidth: 178, padding: "10px 12px" }}>
          <div style={{ color: C.gold, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 5 }}>Decisão sugerida</div>
          <div style={{ color: p0.length ? C.coral : C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.3 }}>{suggestedStatus}</div>
          <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.45, marginTop: 7 }}>Próxima ação</div>
          <div style={{ color: C.gold, fontSize: 11, fontWeight: 850, lineHeight: 1.35 }}>{nextAction}</div>
          <div style={{ color: C.sky, fontFamily: mono, fontSize: 10, fontWeight: 800, marginTop: 8 }}>
            Confiança {confidence}/100 · {p0.length} P0 · {p1.length} P1
          </div>
        </div>
      </div>

      <div style={{ color: C.muted, fontSize: 10, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>
        O que precisa ser verdade
      </div>

      <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(124px, 1fr))" }}>
        {nodes.map((node, index) => (
          <div key={node.number} style={{ display: "grid", gridTemplateColumns: index < nodes.length - 1 ? "1fr auto" : "1fr", gap: 7, alignItems: "center" }}>
            <div
              style={{
                background: C.bg + "78",
                border: `1px solid ${node.color}35`,
                borderTop: `3px solid ${node.color}`,
                borderRadius: 13,
                minHeight: 134,
                padding: "10px 11px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", marginBottom: 7 }}>
                <span style={{ color: node.color, fontFamily: mono, fontSize: 10, fontWeight: 900 }}>{node.number}</span>
                <span style={{ background: node.color + "18", border: `1px solid ${node.color}35`, borderRadius: 999, color: node.color, fontFamily: mono, fontSize: 9, fontWeight: 900, padding: "2px 6px" }}>{node.status}</span>
              </div>
              <div style={{ color: C.text, fontSize: 13, fontWeight: 950, lineHeight: 1.2 }}>{node.title}</div>
              <div style={{ color: node.color, fontSize: 10, fontWeight: 850, lineHeight: 1.35, marginTop: 6 }}>{node.question}</div>
              <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.4, marginTop: 6 }}>{node.detail}</div>
            </div>
            {index < nodes.length - 1 && (
              <div aria-hidden="true" style={{ color: C.gold, fontFamily: mono, fontSize: 14, fontWeight: 900 }}>→</div>
            )}
          </div>
        ))}
      </div>

      <div style={{ background: blockers.length ? C.coral + "10" : C.green + "10", border: `1px solid ${blockers.length ? C.coral : C.green}35`, borderLeft: `4px solid ${blockers.length ? C.coral : C.green}`, borderRadius: 12, padding: "10px 12px" }}>
        <div style={{ color: blockers.length ? C.coral : C.green, fontSize: 10, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
          O que pode matar a tese
        </div>
        <div style={{ color: C.text, fontSize: 12, fontWeight: 850, lineHeight: 1.45 }}>
          {blockers.length ? blockers.join(" · ") : "Nenhum bloqueio crítico apareceu no mapa mental até agora."}
        </div>
      </div>
    </section>
  );
}

function JourneyDetailGroup({ id, title, subtitle, accent = C.gold, defaultOpen = false, children }) {
  return (
    <details
      data-testid={`journey-detail-${id}`}
      open={defaultOpen}
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderLeft: `3px solid ${accent}`,
        borderRadius: 14,
        overflow: "hidden",
      }}
    >
      <summary
        style={{
          alignItems: "center",
          cursor: "pointer",
          display: "flex",
          gap: 10,
          justifyContent: "space-between",
          listStyle: "none",
          padding: "12px 14px",
        }}
      >
        <span style={{ minWidth: 0 }}>
          <span style={{ color: accent, display: "block", fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>{title}</span>
          <span style={{ color: C.muted, display: "block", fontSize: 11, lineHeight: 1.45, marginTop: 3 }}>{subtitle}</span>
        </span>
        <span aria-hidden="true" style={{ color: accent, fontFamily: mono, fontSize: 13, fontWeight: 900 }}>+</span>
      </summary>
      <div style={{ borderTop: `1px solid ${C.border}`, display: "flex", flexDirection: "column", gap: 12, padding: 12 }}>
        {children}
      </div>
    </details>
  );
}

function RealEstateDossier({ thesis, onRefresh }) {
  const analysis = thesis.realEstateAnalysis || (thesis.frente === "Imóveis" ? {} : null);
  if (!analysis) return null;

  const scenarios = analysis.scenarios || {};
  const pending = analysis.pending_items || [];
  const p0 = pending.filter((item) => item.priority === "P0");
  const p1 = pending.filter((item) => item.priority !== "P0");
  const pendingSummary = `Pendências: ${p0.length} P0 ${p0.length === 1 ? "bloqueia" : "bloqueiam"} decisão, ${p1.length} P1 ${p1.length === 1 ? "melhora" : "melhoram"} análise.`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <RealEstateGuidedJourney thesis={thesis} analysis={analysis} p0={p0} p1={p1} />

      <div data-testid="real-estate-technical-details" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <JourneyDetailGroup id="decisao" title="1. Decisão e score" subtitle="O que o radar está dizendo agora." accent={C.gold} defaultOpen>
          <RealEstateSection title="Decisão do Radar" variant="radar">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <RadarDetailCell label="Status sugerido" value={analysis.suggested_status} color={analysis.suggested_status === "Descartado" ? C.coral : C.teal} />
              <RadarDetailCell label="Próxima ação" value={analysis.next_action} color={C.gold} highlight />
              <RadarDetailCell label="Status do preço teto" value={analysis.price_ceiling_status} color={analysis.price_ceiling_status === "Acima do teto" ? C.coral : C.teal} />
              <RadarDetailCell label="Status operacional" value={thesis.statusRaw || thesis.status} color={C.sky} />
              <RadarDetailCell label="Resultado/decisão" value={thesis.desfecho} color={C.gold} />
            </div>
            <div style={{ background: C.amber + "12", border: `1px solid ${C.amber + "35"}`, borderRadius: 10, color: C.amber, fontSize: 12, fontWeight: 700, lineHeight: 1.5, marginTop: 10, padding: "10px 12px" }}>
              {pendingSummary}
            </div>
          </RealEstateSection>

          <RealEstateScoreHero analysis={analysis} />
        </JourneyDetailGroup>

        <JourneyDetailGroup id="hf" title="2. Prédio e visita" subtitle="O que valida se o HF faz sentido na vida real." accent={C.teal} defaultOpen>
          <HouseFlippingBuildingFit thesis={thesis} />
          <GoodBuildingScore thesis={thesis} />
          <BuildingCondoStructuredFields thesis={thesis} />
          <HouseFlippingVisitChecklist thesis={thesis} onRefresh={onRefresh} />
        </JourneyDetailGroup>

        <JourneyDetailGroup id="numeros" title="3. Números e cenários" subtitle="Abra quando quiser conferir preço teto, ROI e simulações." accent={C.sky}>
          <RealEstateAsymmetryMap thesis={thesis} />

          <RealEstateSection title="Números da Operação">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <DetailCell label="Preço pedido" value={money(thesis.entrada)} numeric />
              <DetailCell label="Valor de referência/mercado" value={money(thesis.valorReferencia)} numeric />
              <DetailCell label="Preço máximo de compra" value={money(analysis.max_purchase_price)} color={C.amber} numeric />
              <DetailCell label="Diferença para o teto" value={money(analysis.price_gap_to_ceiling)} color={Number(analysis.price_gap_to_ceiling) > 0 ? C.coral : C.teal} numeric />
              <DetailCell label="Caixa necessário" value={money(analysis.cash_needed)} numeric />
              <DetailCell label="Preço de equilíbrio" value={money(analysis.breakeven_sale_price)} numeric />
              <DetailCell label="ROI alvo" value={pct(analysis.target_roi_pct)} color={C.teal} numeric />
              <DetailCell label="ROI base esperado" value={pct(analysis.base_profit_pct)} color={Number(analysis.base_profit_pct) >= 0 ? C.teal : C.coral} numeric />
            </div>
          </RealEstateSection>

          <NegotiationSimulator thesis={thesis} analysis={analysis} />

          <RealEstateSection title="Cenários">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <ScenarioCard label="Conservador" scenario={scenarios.conservative} />
              <ScenarioCard label="Base" scenario={scenarios.base} />
              <ScenarioCard label="Otimista" scenario={scenarios.optimistic} />
            </div>
          </RealEstateSection>
        </JourneyDetailGroup>

        <JourneyDetailGroup id="evidencias" title="4. Pendências e critérios" subtitle="Área de auditoria: o que falta, o que já fechou e como o score foi composto." accent={C.amber}>
          <RealEstateSection title="Pendências abertas">
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <PendingGroup title="P0 · bloqueia decisão" items={p0} color={C.coral} thesis={thesis} onResolved={onRefresh} />
              <PendingGroup title="P1 · melhora análise" items={p1} color={C.amber} thesis={thesis} onResolved={onRefresh} />
            </div>
          </RealEstateSection>

          <RealEstateSection title="Pontos já esclarecidos">
            <ClarifiedItemsGrid items={analysis.clarified_items} />
          </RealEstateSection>

          <RealEstateSection title="Composição do Score">
            <BreakdownRows rows={analysis.score_breakdown} accent={C.gold} testIdPrefix="score-breakdown" />
          </RealEstateSection>

          <RealEstateSection title="Composição da Confiança">
            <BreakdownRows rows={analysis.confidence_breakdown} accent={C.sky} showStatus testIdPrefix="confidence-breakdown" />
          </RealEstateSection>
        </JourneyDetailGroup>
      </div>

      {thesis.sourceUrl && (
        <a
          href={thesis.sourceUrl}
          target="_blank"
          rel="noreferrer"
          style={{
            alignSelf: "flex-start",
            background: C.gold + "18",
            border: `1px solid ${C.gold + "45"}`,
            borderRadius: 10,
            color: C.gold,
            fontSize: 12,
            fontWeight: 700,
            padding: "10px 12px",
            textDecoration: "none",
          }}
        >
          Abrir fonte do imóvel
        </a>
      )}
    </div>
  );
}

function marketAccent(thesis) {
  if (thesis.frente === "Cripto") return C.amber;
  return C.sky;
}

function marketJaneComment(thesis) {
  if (thesis.frente === "Cripto") {
    return `O ciclo aponta movimento em ${thesis.ativo}, mas cripto não fecha o pregão. O plano separa preço, liquidez e stop antes de qualquer conclusão.`;
  }

  return `A hipótese sugere ${String(thesis.direcao || "movimento").toLowerCase()} em ${thesis.ativo}. O histórico indica que entrada, alvo e stop precisam aparecer juntos; o plano foi seguido.`;
}

function MarketSection({ title, accent, children }) {
  return (
    <section style={{ background: C.panel, border: `1px solid ${C.border}`, borderTop: `2px solid ${accent}`, borderRadius: 12, padding: 14 }}>
      <div style={{ color: C.text, fontSize: 13, fontWeight: 800, marginBottom: 12 }}>{title}</div>
      {children}
    </section>
  );
}

function marketGap(thesis) {
  const expected = Number(thesis.esperado) || 0;
  const current = Number(thesis.resultado) || 0;
  return current - expected;
}

function MarketThesisDossier({ thesis, isNarrow = false }) {
  const isCrypto = thesis.frente === "Cripto";
  const accent = marketAccent(thesis);
  const resultColor = Number(thesis.resultado) >= 0 ? C.teal : C.coral;
  const gap = marketGap(thesis);
  const gridColumns = isNarrow ? "1fr" : "1fr 1fr";
  const threeColumns = isNarrow ? "1fr" : "repeat(3, 1fr)";

  if (isCrypto) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <MarketSection title="Mesa cripto 24/7" accent={accent}>
          <div style={{ display: "grid", gridTemplateColumns: gridColumns, gap: 10 }}>
            <DetailCell label="Preço agora" value={money(thesis.valorReferencia || thesis.entrada)} color={C.gold} numeric />
            <DetailCell label="Entrada planejada" value={money(thesis.entrada)} numeric />
            <DetailCell label="Volatilidade" value={pct(Math.abs(gap))} color={C.amber} numeric />
            <DetailCell label="Liquidez" value="Monitorada 24/7" color={C.sky} />
            <DetailCell label="Janela do ciclo" value={`${Number.isFinite(Number(thesis.dias)) ? Math.round(Number(thesis.dias)) : 0} d`} color={C.purple} numeric />
            <DetailCell label="Saída se" value={compactExitRule(thesis.saida)} color={C.muted} />
          </div>
        </MarketSection>

        <div style={{ display: "grid", gridTemplateColumns: gridColumns, gap: 12 }}>
          <KPICard label="Momento atual" value={pct(thesis.resultado)} sub={`esperado ${pct(thesis.esperado)}`} accent={resultColor} valueColor={resultColor} />
          <KPICard label="Alvo do ciclo" value={money(thesis.targetPrice || thesis.alvo || thesis.entrada)} sub="plano original" accent={C.gold} valueColor={C.gold} />
        </div>

        <MarketSection title="Aprendizado Halley" accent={C.green}>
          <div style={{ color: C.green, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Aprendizado registrado</div>
          <div style={{ color: C.text, fontSize: 12, lineHeight: 1.55 }}>{thesis.aprendizado}</div>
        </MarketSection>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "grid", gridTemplateColumns: gridColumns, gap: 12 }}>
        <KPICard label="Resultado vs esperado" value={pct(thesis.resultado)} sub={`esperado ${pct(thesis.esperado)}`} accent={resultColor} valueColor={resultColor} />
        <KPICard label="Esperado" value={pct(thesis.esperado)} sub="hipótese original" accent={C.sky} valueColor={C.sky} />
      </div>

      <MarketSection title="Plano operacional B3" accent={accent}>
        <div style={{ display: "grid", gridTemplateColumns: gridColumns, gap: 10 }}>
          <DetailCell label="Entrada planejada" value={money(thesis.entrada)} color={C.sky} numeric />
          <DetailCell label="Alvo técnico" value={compactExitRule(thesis.saida).split(" · ")[0] || "--"} color={C.teal} />
          <DetailCell label="Stop do plano" value={compactExitRule(thesis.saida).split(" · ")[1] || "--"} color={C.coral} />
          <DetailCell label="Momento atual" value={pct(thesis.resultado)} color={resultColor} numeric />
        </div>
      </MarketSection>

      <MarketSection title="Ciclo Halley" accent={C.purple}>
        <div style={{ display: "grid", gridTemplateColumns: threeColumns, gap: 10 }}>
          <DetailCell label="Padrão histórico" value={thesis.estrutura} color={C.text} />
          <DetailCell label="Esperado" value={pct(thesis.esperado)} color={C.gold} numeric />
          <DetailCell label="Gap atual" value={pct(gap)} color={gap >= 0 ? C.teal : C.coral} numeric />
        </div>
      </MarketSection>

      <MarketSection title="Aprendizado Halley" accent={C.green}>
        <div style={{ color: C.green, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Aprendizado registrado</div>
        <div style={{ color: C.text, fontSize: 12, lineHeight: 1.55 }}>{thesis.aprendizado}</div>
      </MarketSection>
    </div>
  );
}

function ThesisDrawer({ thesis, onRefresh, feedStatus, updatedAt, isNarrow = false }) {
  if (!thesis) {
    return (
      <aside data-testid={isNarrow ? "teses-detail-mobile" : "teses-detail-desktop"} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: isNarrow ? 14 : 18, display: "flex", flexDirection: "column", gap: 14 }}>
        <PatrickJane
          screen="teses"
          state="observing"
          message="Esse padrão apareceu 97 vezes no histórico. Sabe quantas vezes quem o ignorou estava certo? Seis."
          imageHeight={90}
          imageBorderColor={C.teal + "45"}
          style={{ alignItems: "flex-start" }}
        />
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "12px 14px" }}>
          <div style={{ color: C.sky, fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Como usar</div>
          <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.55 }}>
            Clique em qualquer linha para abrir a ficha completa aqui, sem cobrir a tabela.
          </div>
        </div>
      </aside>
    );
  }
  const isRealEstate = thesis.frente === "Imóveis";
  const estimatedRealEstate = isEstimatedRealEstate(thesis);

  return (
    <aside data-testid={isNarrow ? "teses-detail-mobile" : "teses-detail-desktop"} style={{ background: C.card, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.gold}`, borderRadius: 14, padding: isNarrow ? 14 : 18, display: "flex", flexDirection: "column", gap: 14 }}>
      {isRealEstate ? (
        <PatrickJaneTextInsight message={realEstateJaneComment(thesis)} />
      ) : (
        <PatrickJane
          screen="teses"
          state="observing"
          message={marketJaneComment(thesis)}
          imageHeight={isNarrow ? 74 : 96}
          imageBorderColor={marketAccent(thesis) + "45"}
          style={{ alignItems: "flex-start" }}
        />
      )}
      <div>
        <div style={{ color: C.text, fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Ficha completa da tese</div>
        <div style={{ color: C.muted, fontSize: 11, fontFamily: mono }}>#{thesis.id} · {thesis.ativo}</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
          <Badge label={compactDirectionLabel(thesis)} type={directionType(thesis.direcao)} />
          <Badge label={thesis.status} type={statusType(thesis.status)} />
        </div>
      </div>
      <DataOriginPanel feedStatus={feedStatus} updatedAt={updatedAt} compact />
      <RealEstateSourceMeta thesis={thesis} />
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0, fontStyle: "italic", borderLeft: `3px solid ${C.purple}`, paddingLeft: 12 }}>{thesis.hipotese}</p>
      {isRealEstate ? (
        <RealEstateDossier thesis={thesis} onRefresh={onRefresh} />
      ) : (
        <MarketThesisDossier thesis={thesis} isNarrow={isNarrow} />
      )}
    </aside>
  );
}

function ThesisFicha({ thesis }) {
  const resultColor = thesis.resultado >= 0 ? C.teal : C.coral;
  const open = isOpenThesis(thesis.status);
  const estimatedRealEstate = isEstimatedRealEstate(thesis);
  const analysis = thesis.realEstateAnalysis || (thesis.frente === "Imóveis" ? {} : null);
  const pending = analysis?.pending_items || [];
  const p0 = pending.filter((item) => item.priority === "P0");

  function MiniCell({ label, value, color = C.text, sub }) {
    return (
      <div style={{ background: C.faint, border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px" }}>
        <div style={{ color: C.muted, fontSize: 9, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 5 }}>{label}</div>
        <div style={{ color, fontSize: 14, fontWeight: 800, fontFamily: mono }}>{value}</div>
        {sub && <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.4, marginTop: 4 }}>{sub}</div>}
      </div>
    );
  }

  return (
    <article data-testid={analysis ? `real-estate-summary-card-${thesis.id}` : undefined} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div>
          <div style={{ color: C.text, fontSize: 14, fontWeight: 700 }}>Ficha #{thesis.id} · {thesis.ativo}</div>
          <div style={{ color: C.muted, fontSize: 11, marginTop: 3 }}>{thesis.frente} · {thesis.status}</div>
        </div>
        <Badge label={thesis.direcao} type={directionType(thesis.direcao)} />
      </div>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.65, margin: 0, fontStyle: "italic", borderLeft: `3px solid ${C.purple}`, paddingLeft: 12 }}>{thesis.hipotese}</p>
      {analysis ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <MiniCell label="Score" value={`${analysis.score || 0}/100`} color={Number(analysis.score) >= 70 ? C.teal : C.amber} sub="qualidade do candidato" />
          <MiniCell label="Confiança" value={`${analysis.confidence || 0}/100`} color={C.sky} sub="evidência comprovada" />
          <MiniCell label="Preço teto" value={analysis.price_ceiling_status || "--"} color={analysis.price_ceiling_status === "Acima do teto" ? C.coral : C.teal} sub={money(analysis.max_purchase_price)} />
          <MiniCell label="Pendências P0" value={`${p0.length} P0`} color={p0.length ? C.coral : C.green} sub={`${pending.length} abertas`} />
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <KPICard
            label={estimatedRealEstate ? "ROI estimado no cenário base" : open ? "Momento atual" : "Resultado"}
            value={pct(thesis.resultado)}
            sub={estimatedRealEstate ? "estimativa da hipótese, não performance realizada" : open ? "tese ainda aberta" : "resultado líquido"}
            accent={resultColor}
            valueColor={resultColor}
          />
          <KPICard label="Esperado" value={pct(thesis.esperado)} sub="resultado previsto" accent={C.sky} valueColor={C.sky} />
        </div>
      )}
      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "12px 14px" }}>
        <div style={{ color: C.green, fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Aprendizado registrado</div>
        <div style={{ color: C.text, fontSize: 12, lineHeight: 1.55 }}>{thesis.aprendizado}</div>
      </div>
    </article>
  );
}

export default function Teses({ data, feedStatus = "fallback", onRefresh, entryMode }) {
  const methodDemoEntry = entryMode === "method-demo";
  const [status, setStatus] = useState(null);
  const [front, setFront] = useState(methodDemoEntry ? "Imóveis" : null);
  const [selected, setSelected] = useState(null);
  const [view, setView] = useState(methodDemoEntry ? "imoveis" : "overview");
  const [realEstateFrontFilter, setRealEstateFrontFilter] = useState(null);
  const [neighborhoodFilter, setNeighborhoodFilter] = useState(null);
  const isNarrow = typeof window !== "undefined" && window.innerWidth < 860;

  const rows = useMemo(() => {
    const normalized = (data?.thesisRows ?? []).map((row) => ({
      id: row.id,
      thesisId: row.thesisId,
      ativo: displayAssetName(row),
      ativoOriginal: row.asset,
      frente: row.front,
      direcao: realEstateLabel(row),
      esperado: row.expectedPct,
      estrutura: row.structure || row.operation,
      operation: row.operation,
      entrada: row.entryPrice,
      saida: compactExitRule(exitText(row)),
      exitRule: row.exitRule,
      targetPrice: row.targetPrice,
      stopPrice: row.stopPrice,
      desfecho: row.outcome,
      dias: row.days,
      status: row.statusGroup,
      statusRaw: row.status,
      resultado: row.front === "Imóveis" && (row.resultKind === "estimate" || row.isOpen === false) ? row.expectedPct : row.resultPct,
      resultadoTipo: row.resultKind,
      isOpen: row.isOpen,
      valorReferencia: row.currentPrice,
      sourceUrl: row.sourceUrl,
      openedAt: row.openedAt,
      realEstateAnalysis: row.realEstateAnalysis,
      hipotese: row.hypothesis,
      aprendizado: row.learning,
    }));
    return ensureHistoricalRows(normalized);
  }, [data]);

  const filteredRows = rows.filter((row) => (!status || row.status === status) && (!front || row.frente === front));
  const activeRows = rows.filter((row) => isOpenThesis(row.status));
  const realEstateRows = rows.filter((row) => row.frente === "Imóveis");
  const realEstateDisplayRows = realEstateRows.filter((row) => {
    const matchesFront = !realEstateFrontFilter || realEstateFrontKey(row) === realEstateFrontFilter;
    const matchesNeighborhood = !neighborhoodFilter || neighborhoodCondoTargetKey(row) === neighborhoodFilter;
    return matchesFront && matchesNeighborhood;
  });
  const activeRealEstateFront = realEstateFrontDefinitions.find((item) => item.key === realEstateFrontFilter);
  const activeNeighborhood = neighborhoodCondoTargets.find((item) => item.key === neighborhoodFilter);
  const historicalRows = rows.filter((row) => row.status === "Histórica");
  const activeAttentionRows = activeRows.filter(needsThesisAttention);
  const historicalAttentionRows = rows.filter((row) => !isOpenThesis(row.status) && needsThesisAttention(row));
  const attentionRows = activeAttentionRows.length ? activeAttentionRows : (historicalAttentionRows.length ? historicalAttentionRows : activeRows);
  const attentionIds = new Set(attentionRows.map((row) => String(row.id)));
  const calmActiveRows = activeRows.filter((row) => !attentionIds.has(String(row.id)));
  const tableRows = view === "imoveis" ? realEstateDisplayRows : filteredRows;
  const fichaRows = (view === "imoveis" ? realEstateDisplayRows : filteredRows).slice(0, 2);
  const decisionHeader = view === "imoveis" || front === "Imóveis" || (tableRows.length > 0 && tableRows.every((row) => row.frente === "Imóveis")) ? "Decisão" : "Direção";
  const statusCounts = Object.fromEntries(statusFilters.map((item) => [item.label, countBy(rows, (row) => row.status === item.label)]));
  const frontCounts = Object.fromEntries(frontFilters.map((item) => [item, countBy(rows, (row) => row.frente === item)]));
  const compactRealEstateTable = (view === "imoveis" || front === "Imóveis") && !isNarrow;
  const avgExpected = rows.length ? rows.reduce((sum, row) => sum + (Number(row.esperado) || 0), 0) / rows.length : 0;
  const positiveHistorical = historicalRows.filter((row) => Number(row.resultado) > 0).length;
  const summaryTestedTheses = Number(data?.scientificSummary?.testedTheses);
  const uniqueHistoricalCount = new Set(
    historicalRows.map((row) => row.thesisId || row.id).filter(Boolean),
  ).size;
  const uniqueTestedTheses = Number.isFinite(summaryTestedTheses)
    ? summaryTestedTheses
    : uniqueHistoricalCount;
  const p0Total = realEstateRows.reduce((sum, row) => sum + getP0Count(row), 0);
  const frontRows = Object.fromEntries(frontFilters.map((item) => [item, rows.filter((row) => row.frente === item)]));
  const dataUpdatedAt = data?.scientificSummary?.lastUpdatedAt;
  const dataTrust = data?.dataTrust?.teses ?? dataTrustForScreen("teses", data, feedStatus);
  const realEstateStrategyReport = data?.realEstateStrategyTerritoryCandidates;
  const hasRealEstateStrategyBriefs = realEstateMatrixBriefs(realEstateStrategyReport).length > 0
    || realEstateRequalificationSignals(realEstateStrategyReport).length > 0;

  useEffect(() => {
    if (!selected) return;
    const updated = rows.find((row) => String(row.id) === String(selected.id) || (selected.thesisId && row.thesisId && row.thesisId === selected.thesisId));
    if (updated && updated !== selected) setSelected(updated);
  }, [rows, selected?.id, selected?.thesisId]);

  useEffect(() => {
    if (!methodDemoEntry || selected) return;
    const firstRealEstateThesis = realEstateDisplayRows[0] || realEstateRows[0];
    if (firstRealEstateThesis) setSelected(firstRealEstateThesis);
  }, [methodDemoEntry, realEstateDisplayRows, realEstateRows, selected]);

  function switchView(nextView) {
    setView(nextView);
    setSelected(null);
    if (nextView === "overview" || nextView === "open") {
      setStatus(null);
      setFront(null);
      setRealEstateFrontFilter(null);
      setNeighborhoodFilter(null);
    }
    if (nextView === "imoveis") {
      setStatus(null);
      setFront("Imóveis");
    }
    if (nextView === "historico") {
      setStatus(null);
      setFront(null);
      setRealEstateFrontFilter(null);
      setNeighborhoodFilter(null);
    }
  }

  function selectRealEstateFront(key) {
    setRealEstateFrontFilter((current) => (current === key ? null : key));
    setSelected(null);
  }

  function selectNeighborhood(key) {
    setNeighborhoodFilter(key);
    setSelected(null);
  }

  const filters = (
    <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: C.muted, fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase" }}>Status</span>
        {statusFilters.map((item) => (
          <FilterButton
            key={item.label}
            active={status === item.label}
            onClick={() => {
              setView("historico");
              setFront(null);
              setStatus(status === item.label ? null : item.label);
            }}
          >
            <Badge label={`${item.label} (${statusCounts[item.label] || 0})`} type={item.type} />
          </FilterButton>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: C.muted, fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase" }}>Frente</span>
        {frontFilters.map((item) => (
          <FilterButton
            key={item}
            active={front === item}
            onClick={() => {
              const nextFront = front === item ? null : item;
              setStatus(null);
              setFront(nextFront);
              setView(nextFront === "Imóveis" ? "imoveis" : "historico");
              if (nextFront !== "Imóveis") setRealEstateFrontFilter(null);
            }}
          >
            <Badge label={`${item} (${frontCounts[item] || 0})`} type="info" />
          </FilterButton>
        ))}
      </div>
      {front === "Imóveis" && neighborhoodFilter && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ color: C.muted, fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase" }}>Bairro</span>
          <FilterButton active onClick={() => setNeighborhoodFilter(null)}>
            <Badge label={`${activeNeighborhood?.label || "Bairro"} (${realEstateDisplayRows.length})`} type="info" />
          </FilterButton>
        </div>
      )}
    </section>
  );

  const selectedDrawer = selected && (
    <ThesisDrawer
      thesis={selected}
      feedStatus={feedStatus}
      updatedAt={dataUpdatedAt}
      isNarrow={isNarrow}
      onRefresh={onRefresh}
    />
  );

  const viewLabels = {
    open: "Acompanhamento ativo",
    imoveis: "Radar imobiliário",
    historico: "Arquivo e auditoria",
  };

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <div style={{ alignItems: "flex-start", display: "flex", gap: 12, justifyContent: "space-between" }}>
        <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>Mapa de decisão das hipóteses — primeiro o que exige atenção, depois o arquivo completo.</p>
        <DataTrustSeal screen="teses" trust={dataTrust} />
      </div>

      <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: "12px 16px" }}>
        <PatrickJane
          hero
          screen="teses"
          state="observing"
          message="Esse padrão apareceu 97 vezes no histórico. Sabe quantas vezes quem o ignorou estava certo? Seis."
          insights={[
            { label: "Objetivo", value: "Decidir o que acompanha, revisa ou arquiva.", color: C.teal },
            { label: "Frente", value: "Prioridade para go-live e radar imobiliário.", color: C.gold },
            { label: "Regra", value: "Tese só avança com entrada, alvo, stop e evidência.", color: C.sky },
          ]}
          imageHeight={154}
          imageWidth="100%"
          imageBorderColor={C.teal + "45"}
          style={{ gap: 14 }}
        />
      </section>

      <DataOriginPanel feedStatus={feedStatus} updatedAt={dataUpdatedAt} />

      {view !== "overview" && (
        <section style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "10px 12px", flexWrap: "wrap" }}>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>
            {viewLabels[view] || "Recorte ativo"} · use o mapa para trocar de frente sem abrir uma barra de abas.
          </div>
          <button
            type="button"
            onClick={() => switchView("overview")}
            style={{
              background: C.card,
              border: `1px solid ${C.border}`,
              borderRadius: 9,
              color: C.gold,
              cursor: "pointer",
              fontFamily: mono,
              fontSize: 9,
              fontWeight: 800,
              letterSpacing: "0.06em",
              padding: "8px 10px",
              textTransform: "uppercase",
            }}
          >
            Voltar ao mapa
          </button>
        </section>
      )}

      {view === "historico" && filters}

      {view === "overview" && (
        <>
          <HubSection
            title="Mapa de oportunidades"
            eyebrow="Frentes e objetivos"
            action={(
              <button
                type="button"
                onClick={() => switchView("imoveis")}
                style={{
                  background: withAlpha(C.purple, "14"),
                  border: `1px solid ${withAlpha(C.purple, "35")}`,
                  borderRadius: 9,
                  color: C.purple,
                  cursor: "pointer",
                  fontFamily: mono,
                  fontSize: 9,
                  fontWeight: 800,
                  letterSpacing: "0.06em",
                  padding: "8px 10px",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                }}
              >
                Abrir radar imobiliário
              </button>
            )}
          >
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
              <KPICard label="Teses testadas únicas" value={uniqueTestedTheses.toLocaleString("pt-BR")} sub="validação deduplicada" accent={C.sky} valueColor={C.sky} />
              <KPICard label="Em acompanhamento" value={activeRows.length.toLocaleString("pt-BR")} sub="pedem acompanhamento" accent={C.teal} valueColor={C.teal} />
              <KPICard label="No radar imobiliário" value={realEstateRows.filter((row) => isOpenThesis(row.status)).length.toLocaleString("pt-BR")} sub={`${p0Total} pendências P0`} accent={C.purple} valueColor={C.purple} />
              <KPICard label="Históricas positivas" value={positiveHistorical.toLocaleString("pt-BR")} sub="evidência arquivada" accent={C.gold} valueColor={C.gold} />
              <KPICard label="Esperado médio" value={pct(avgExpected)} sub="todas as frentes" accent={C.amber} valueColor={C.amber} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
              {frontFilters.map((item) => (
                <FrontSummaryCard
                  key={item}
                  front={item}
                  rows={frontRows[item] || []}
                  onClick={() => switchView(item === "Imóveis" ? "imoveis" : "historico")}
                />
              ))}
            </div>
          </HubSection>

          <DecisionDesk
            activeRows={activeRows}
            attentionRows={attentionRows}
            historicalRows={historicalRows}
            realEstateRows={realEstateRows}
            onOpenActive={() => switchView("open")}
            onOpenArchive={() => switchView("historico")}
            onSelectAttention={setSelected}
          />

          {selectedDrawer}

          <HubSection title="Fila de atenção" eyebrow="O que olhar primeiro">
            <AttentionQueue rows={attentionRows} onSelect={setSelected} selectedId={selected?.id} />
          </HubSection>

          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.2fr) minmax(260px, 0.8fr)", gap: 14, alignItems: "start" }}>
            <HubSection title="Planos em acompanhamento" eyebrow="Em execução">
              <CompactThesisList
                rows={calmActiveRows}
                emptyText="A fila de atenção concentra as teses em acompanhamento que exigem decisão agora."
                onSelect={setSelected}
                selectedId={selected?.id}
              />
            </HubSection>
            <ArchivePrompt historicalCount={historicalRows.length} onOpen={() => switchView("historico")} />
          </div>

        </>
      )}

      {view === "open" && (
        <>
          <HubSection title="Acompanhamento ativo" eyebrow="Menos arquivo, mais decisão">
            <ActiveCoverageNotice activeRows={activeRows} />
            <CompactThesisList
              rows={activeRows}
              title="Planos vivos"
              emptyText="Nenhuma tese em acompanhamento agora. O plano contempla aguardar novo padrão."
              onSelect={setSelected}
              selectedId={selected?.id}
              limit={12}
            />
          </HubSection>
          {selectedDrawer}
        </>
      )}

      {view === "imoveis" && (
        <>
          <RealEstateDealCockpit rows={realEstateDisplayRows} allRows={realEstateRows} selected={selected} onSelect={setSelected} />

          {methodDemoEntry && selectedDrawer && (
            <>
              <section data-testid="method-demo-bridge" style={{ background: C.gold + "10", border: `1px solid ${C.gold}35`, borderLeft: `4px solid ${C.gold}`, borderRadius: 14, padding: "14px 16px" }}>
                <div style={{ color: C.gold, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>
                  Da animação para a tese
                </div>
                <div style={{ color: C.text, fontSize: 14, fontWeight: 800, marginBottom: 5 }}>
                  Agora o método aparece aplicado a uma hipótese real.
                </div>
                <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.6 }}>
                  A ficha abaixo mostra a hipótese, a decisão do radar, o score, as pendências e o aprendizado registrado. O plano fica visível antes de qualquer convicção.
                </div>
              </section>
              {selectedDrawer}
            </>
          )}

          {!methodDemoEntry && selectedDrawer}

          <section data-testid="real-estate-support-panels" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {hasRealEstateStrategyBriefs && (
              <SupportDisclosure title="Briefs por estratégia e território" eyebrow="Busca guiada">
                <RealEstateStrategyTerritoryBriefs report={realEstateStrategyReport} />
              </SupportDisclosure>
            )}

            <SupportDisclosure title="Explorar estratégias" eyebrow="Opcional">
              <RealEstateFrontCards rows={realEstateRows} strategyReport={realEstateStrategyReport} activeKey={realEstateFrontFilter} onSelect={selectRealEstateFront} />
            </SupportDisclosure>

            <SupportDisclosure title="Explorar territórios" eyebrow="Opcional">
              <NeighborhoodCondoRadar rows={realEstateRows} activeKey={neighborhoodFilter} onSelect={selectNeighborhood} />
            </SupportDisclosure>

            <SupportDisclosure title="Adicionar candidato" eyebrow="Opcional">
              <RealEstateImportPanel />
            </SupportDisclosure>

            <SupportDisclosure title="Ver lista completa" eyebrow="Apoio operacional">
              <section style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: "12px 14px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ color: C.gold, fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 5 }}>
                    Candidatos
                  </div>
                  <div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>
                    {activeNeighborhood ? `Candidatos em ${activeNeighborhood.label}` : activeRealEstateFront ? `Candidatos em ${activeRealEstateFront.label}` : "Todos os candidatos imobiliários"}
                  </div>
                  <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 4 }}>
                    {realEstateFrontFilter || neighborhoodFilter
                      ? `${realEstateDisplayRows.length.toLocaleString("pt-BR")} ${realEstateDisplayRows.length === 1 ? "candidato filtrado" : "candidatos filtrados"}`
                      : `${realEstateDisplayRows.length.toLocaleString("pt-BR")} candidatos no radar`}
                  </div>
                </div>
                {(realEstateFrontFilter || neighborhoodFilter) && (
                  <button
                    type="button"
                    aria-label="Limpar filtro imobiliário"
                    onClick={() => {
                      setRealEstateFrontFilter(null);
                      setNeighborhoodFilter(null);
                      setSelected(null);
                    }}
                    style={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 9,
                      color: C.muted,
                      cursor: "pointer",
                      fontFamily: "inherit",
                      fontSize: 11,
                      fontWeight: 800,
                      letterSpacing: "0.04em",
                      padding: "8px 10px",
                      textTransform: "uppercase",
                    }}
                  >
                    Limpar filtro
                  </button>
                )}
              </section>
              <ThesesTable rows={realEstateDisplayRows} selected={selected} onSelect={setSelected} decisionHeader="Decisão" compactRealEstateTable={compactRealEstateTable} />
            </SupportDisclosure>
          </section>
        </>
      )}

      {view === "historico" && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14, alignItems: "start" }}>
            <ThesesTable rows={tableRows} selected={selected} onSelect={setSelected} decisionHeader={decisionHeader} compactRealEstateTable={compactRealEstateTable} />
            {selectedDrawer}
          </div>

          <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
              <h2 style={{ color: C.text, fontSize: 15, fontWeight: 700, margin: 0 }}>Fichas expandidas</h2>
              <span style={{ color: C.muted, fontSize: 11 }}>As 2 primeiras teses da seleção atual</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {fichaRows.map((thesis) => <ThesisFicha key={`ficha-${thesis.id}`} thesis={thesis} />)}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
