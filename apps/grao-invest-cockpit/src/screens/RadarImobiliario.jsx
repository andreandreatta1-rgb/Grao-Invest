import { useMemo, useState } from "react";
import { Badge, C, KPICard, PatrickJane, alpha, mono, withAlpha } from "../components";
import { discardRealEstateCandidate } from "../data/cockpitHalleyApi";
import { PerdizesCasePortfolio, REAL_ESTATE_DEMO_CASES } from "./JornadaTese.jsx";

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function isRealEstateFront(row) {
  const front = String(row?.front || "").toLowerCase();
  return front.includes("im") || front.includes("real_estate");
}

function cleanAssetTitle(value) {
  return String(value || "").replace(/^REAL\s*[-–—]\s*/i, "").trim();
}

function compactText(value) {
  if (Array.isArray(value)) return value.filter(Boolean).join("; ");
  if (value && typeof value === "object") return Object.values(value).filter(Boolean).join("; ");
  return String(value || "").trim();
}

function firstText(...values) {
  for (const value of values) {
    const text = compactText(value);
    if (text) return text;
  }
  return "";
}

function searchText(value) {
  return compactText(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function includesAny(text, markers) {
  return markers.some((marker) => text.includes(marker));
}

const AUCTION_MARKERS = [
  "arremat",
  "caixa",
  "leilao",
  "leiloes",
  "leeilon",
  "portalzuk",
  "projud",
  "siteleiloes",
  "venda-imoveis.caixa",
  "zuk",
];

const DIRECT_MARKERS = [
  "chaves na mao",
  "chavesnamao",
  "direcional",
  "floraimoveis",
  "imovelweb",
  "lelloimoveis",
  "olx",
  "quintoandar",
  "vivareal",
  "zapimoveis",
];

function firstNumber(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number) && number > 0) return number;
  }
  return 0;
}

function firstFiniteNumber(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) return number;
  }
  return 0;
}

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return "R$ --";
  return `R$ ${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

function shortText(value, size = 48) {
  const text = compactText(value);
  if (text.length <= size) return text;
  return `${text.slice(0, size - 1).trim()}…`;
}

function formatDate(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return "entrada no radar";
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

function isOpenRealEstateRow(row) {
  if (row?.isOpen === false) return false;
  const status = String(`${row?.statusGroup || ""} ${row?.status || ""}`).toLowerCase();
  if (status.includes("hist") || status.includes("fechad") || status.includes("descart")) return false;
  return status.includes("go-live") || status.includes("abert") || status.includes("pendenc") || status.includes("analise") || status.includes("análise") || status.includes("observ") || status.includes("monitor") || row?.isOpen === true;
}

function canonicalRealEstateRows(data) {
  const thesisRows = asArray(data?.thesisRows).filter(isRealEstateFront);
  const candidateRows = asArray(data?.realEstateCandidates).filter(isRealEstateFront);
  const seen = new Set();
  return [...candidateRows, ...thesisRows].filter((row) => {
    const candidateId = String(row?.thesisId || row?.id || "").match(/(?:IM-RADAR-)?(\d+)$/i)?.[1];
    const key = candidateId
      ? `im-radar-${candidateId}`
      : String(row?.sourceUrl || row?.source_url || row?.asset || "").toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function analysisFor(row) {
  return row?.realEstateAnalysis || row?.real_estate_analysis || {};
}

function candidateFor(row) {
  const analysis = analysisFor(row);
  return analysis.candidate || analysis.candidate_snapshot || analysis.candidateSnapshot || row?.candidate || {};
}

function sourceValidationFor(row) {
  const analysis = analysisFor(row);
  const candidate = candidateFor(row);
  const validation = analysis.source_validation || analysis.sourceValidation || row?.source_validation || row?.sourceValidation || candidate.source_validation || candidate.sourceValidation || {};
  const status = firstText(
    validation.status,
    row?.source_validation_status,
    row?.sourceValidationStatus,
    candidate.source_validation_status,
    candidate.sourceValidationStatus,
  ).toLowerCase();
  const reason = firstText(
    validation.reason,
    row?.source_validation_reason,
    row?.sourceValidationReason,
    candidate.source_validation_reason,
    candidate.sourceValidationReason,
  );
  if (status === "valid") return { status, reason, label: "Fonte validada", type: "success" };
  if (status === "expired" || status === "unavailable") return { status, reason, label: "Fonte indisponível", type: "danger" };
  if (status === "ambiguous") return { status, reason, label: "Fonte manual", type: "warning" };
  return { status, reason, label: "Fonte a validar", type: "warning" };
}

function sourceTextFor(row) {
  const candidate = candidateFor(row);
  return [
    row?.sourceUrl,
    row?.source_url,
    row?.sourceOrigin,
    row?.source_origin,
    row?.origin,
    candidate.source_url,
    candidate.sourceUrl,
    candidate.origin,
  ].map(searchText).join(" ");
}

function strategyTextFor(row) {
  const candidate = candidateFor(row);
  return [
    row?.strategy,
    row?.operation,
    row?.structure,
    row?.hypothesis,
    row?.asset,
    row?.role,
    row?.whyRadar,
    row?.sourceUrl,
    row?.source_url,
    row?.sourceOrigin,
    row?.source_origin,
    row?.origin,
    candidate.strategy,
    candidate.origin,
    candidate.notes,
  ].map(searchText).join(" ");
}

function auctionTextFor(row) {
  const candidate = candidateFor(row);
  return [
    sourceTextFor(row),
    row?.strategy,
    row?.structure,
    row?.sourceOrigin,
    row?.source_origin,
    row?.origin,
    candidate.strategy,
    candidate.origin,
    candidate.source_url,
    candidate.sourceUrl,
    candidate.notes,
  ].map(searchText).join(" ");
}

function stripNegatedRenovation(text) {
  return text
    .replace(/\bsem\s+reforma\b/g, "")
    .replace(/\bsem\s+obra\s+pesada\b/g, "")
    .replace(/\bsem\s+obra\b/g, "");
}

function pendingItemsFor(row) {
  const analysis = analysisFor(row);
  const pending = asArray(analysis.pending_items || analysis.pendingItems);
  if (pending.length) return pending;

  const invalidation = firstText(row?.invalidation, row?.exitRule);
  return invalidation
    ? [{ priority: "P0", title: "Validar regra de invalidação", action: invalidation }]
    : [{ priority: "P0", title: "Confirmar diligência base", action: "Checar fonte, preço, comparáveis, documentação e risco operacional antes de avançar." }];
}

function p0ItemsFor(row) {
  const pending = pendingItemsFor(row);
  const p0 = pending.filter((item) => String(item?.priority || "").toUpperCase() === "P0");
  return p0.length ? p0 : pending.slice(0, 3);
}

function strategyFor(row) {
  const text = strategyTextFor(row);
  const sourceText = sourceTextFor(row);
  const flipText = stripNegatedRenovation(text);
  const nonCashText = text.replace(/\bcaixa\s+necessario\b/g, "");
  const hasAuction = includesAny(auctionTextFor(row), AUCTION_MARKERS)
    || nonCashText.includes("leilao")
    || nonCashText.includes("arremat");
  const hasFlip = (
    flipText.includes("house flipping")
    || flipText.includes(" flip")
    || flipText.includes("retrofit")
    || flipText.includes("reformar")
    || /\breforma\s+(leve|pesada|completa|estrutural|hf)\b/.test(flipText)
  );
  const hasDirect = includesAny(sourceText, DIRECT_MARKERS)
    || text.includes("compra direta")
    || text.includes("venda direta")
    || text.includes("negociacao direta")
    || text.includes("negociacao")
    || text.includes("vendedor");
  const hasResale = text.includes("revenda") || text.includes("venda direta") || text.includes("vender") || text.includes("saida imediata");

  if (hasAuction && hasFlip) return "Leilão + HF";
  if (hasAuction && hasResale) return "Leilão direto e venda";
  if (hasAuction) return "Leilão / Caixa";
  if (hasDirect && hasFlip) return "Compra direta + HF";
  if (hasDirect && hasResale) return "Compra para revenda";
  if (hasFlip) return "House flipping";
  if (text.includes("aluguel") || text.includes("locacao") || text.includes("locação") || text.includes("renda")) return "Renda / plano B";
  if (text.includes("lancamento") || text.includes("lançamento") || text.includes("planta")) return "Lançamento / ciclo longo";
  return "Compra direta";
}

function withTypeIcon(item) {
  const strategyIcon = iconForStrategy(strategyFor(item));
  return {
    ...item,
    icon: strategyIcon.icon,
    iconLabel: strategyIcon.label,
    iconBasis: strategyIcon.basis,
  };
}

function iconForStrategy(strategy) {
  const text = String(strategy || "").toLowerCase();
  if (text.includes("leilão + hf") || text.includes("leilao + hf")) {
    return { icon: "⚖🛠", label: "Leilão + HF", basis: "Origem por leilão, mas a margem depende de reforma, reposicionamento e revenda." };
  }
  if (text.includes("leilão direto") || text.includes("leilao direto")) {
    return { icon: "⚖↗", label: "Leilão direto e venda", basis: "Origem por leilão, com tese de revenda sem obra relevante." };
  }
  if (text.includes("compra direta + hf")) {
    return { icon: "🤝🛠", label: "Compra direta + HF", basis: "Negociação direta seguida de reforma e revenda disciplinada." };
  }
  if (text.includes("compra para revenda")) {
    return { icon: "🏷↗", label: "Compra para revenda", basis: "Compra abaixo do valor provável, sem depender de obra pesada." };
  }
  if (text.includes("leilão") || text.includes("leilao") || text.includes("caixa")) {
    return { icon: "⚖", label: "Leilão / Caixa", basis: "Preço com edital, praça, ocupação, matrícula e débitos como P0." };
  }
  if (text.includes("house flipping") || text.includes("flip")) {
    return { icon: "🛠", label: "House flipping", basis: "Compra, reforma, reposicionamento e venda precisam fechar na mesma conta." };
  }
  if (text.includes("renda") || text.includes("plano b")) {
    return { icon: "🔑", label: "Renda / plano B", basis: "Aluguel e vacância viram proteção se a revenda demorar." };
  }
  if (text.includes("lançamento") || text.includes("lancamento") || text.includes("planta")) {
    return { icon: "🏗", label: "Lançamento", basis: "Prazo de entrega, fluxo de pagamento e liquidez futura comandam a tese." };
  }
  if (text.includes("calibr")) {
    return { icon: "📐", label: "Calibração", basis: "Caso usado para calibrar regra, preço teto, custo e descarte." };
  }
  return { icon: "🤝", label: "Compra direta", basis: "Negociação, desconto real e saída provável precisam aparecer antes da proposta." };
}

function colorForStory(score, decision) {
  const text = String(decision || "").toLowerCase();
  if (text.includes("recusar") || text.includes("descartar") || text.includes("não avançar") || score < 50) return C.coral;
  if (score >= 76) return C.green;
  if (score >= 66) return C.gold;
  return C.amber;
}

function temporalTypeFor(score, p0Count, decision) {
  const text = String(decision || "").toLowerCase();
  if (text.includes("recusar") || text.includes("descartar") || text.includes("não avançar") || score < 50) return "danger";
  if (p0Count > 0 || score < 66) return "warning";
  return "info";
}

function liveStoryFromRow(row, index) {
  const analysis = analysisFor(row);
  const candidate = candidateFor(row);
  const score = Math.round(firstNumber(analysis.score, row?.score, 58));
  const confidence = Math.round(firstNumber(analysis.confidence, row?.confidence, 42));
  const p0Items = p0ItemsFor(row);
  const p0Count = p0Items.filter((item) => String(item?.priority || "").toUpperCase() === "P0").length;
  const isOpen = isOpenRealEstateRow(row);
  const statusLabel = firstText(row?.statusGroup, row?.status, isOpen ? "em análise" : "encerrado");
  const decision = isOpen
    ? firstText(analysis.suggested_status, analysis.suggestedStatus, analysis.next_action, analysis.nextAction, row?.outcome, row?.direction, "Investigar")
    : firstText(row?.outcome, row?.exitRule, row?.status, analysis.suggested_status, analysis.suggestedStatus, "Encerrado");
  const entry = firstNumber(row?.entryPrice, row?.currentPrice, analysis.ask_price, analysis.entry_price, candidate.price, candidate.ask_price);
  const ceiling = firstNumber(analysis.max_purchase_price, analysis.maxPurchasePrice, row?.stopPrice, entry);
  const saleBase = firstNumber(
    analysis.scenarios?.base?.sale_price,
    analysis.scenarios?.base?.salePrice,
    analysis.target_sale_price,
    analysis.targetSalePrice,
    row?.targetPrice,
    row?.currentPrice,
  );
  const renovationCosts = firstNumber(analysis.renovation_budget, analysis.renovationBudget, candidate.renovation_budget, candidate.renovationBudget, candidate.reform_budget);
  const acquisitionCosts = firstNumber(candidate.transaction_costs, candidate.transactionCosts, analysis.transaction_costs, Math.round(entry * 0.08));
  const carryingCosts = firstNumber(analysis.carrying_costs, analysis.carryingCosts, Math.round(entry * 0.04));
  const sellingCosts = firstNumber(analysis.selling_costs, analysis.sellingCosts, Math.round(saleBase * 0.06));
  const auctioneerFee = strategyFor(row).includes("Leilão") ? Math.round(entry * 0.05) : 0;
  const totalCost = firstNumber(analysis.total_cost, analysis.totalCost, entry + auctioneerFee + acquisitionCosts + renovationCosts + carryingCosts + sellingCosts);
  const netProfit = firstFiniteNumber(analysis.scenarios?.base?.net_profit, analysis.scenarios?.base?.netProfit, saleBase - totalCost);
  const roiPct = firstFiniteNumber(analysis.scenarios?.base?.roi_pct, analysis.scenarios?.base?.roiPct, analysis.target_roi_pct, row?.expectedPct);
  const color = colorForStory(score, decision);
  const title = cleanAssetTitle(firstText(row?.asset, row?.name, `Candidato imobiliário ${index + 1}`));
  const nextAction = firstText(analysis.next_action, analysis.nextAction, row?.exitRule, row?.invalidation, "Diligência aberta");
  const strategy = strategyFor(row);
  const strategyIcon = iconForStrategy(strategy);
  const identifier = String(row?.thesisId || row?.id || `IM-ABERTO-${index + 1}`);
  const sourceValidation = sourceValidationFor(row);

  return {
    id: identifier.startsWith("#") ? identifier : `#${identifier}`,
    title,
    role: isOpen ? `Caso real aberto · ${statusLabel}` : `Caso real encerrado · ${firstText(row?.outcome, row?.status, statusLabel)}`,
    strategy,
    sourceUrl: firstText(row?.sourceUrl, row?.source_url, "#"),
    sourceOrigin: firstText(row?.sourceOrigin, row?.source_origin, row?.origin, candidate.origin),
    area: firstText(candidate.area, candidate.private_area, candidate.privateArea, candidate.private_area_m2, candidate.privateAreaM2, "área a validar"),
    floor: firstText(candidate.floor, candidate.andar, "andar a validar"),
    bedrooms: firstText(candidate.bedrooms, candidate.rooms, candidate.quartos, "quartos a validar"),
    bathrooms: firstText(candidate.bathrooms, candidate.banheiros, "banheiros a validar"),
    parking: firstText(candidate.parking, candidate.vagas, candidate.parking_spaces, candidate.parkingSpaces, "vaga a validar"),
    building: firstText(candidate.building, candidate.condominium, title),
    firstAuctionDate: formatDate(row?.openedAt || row?.candidate_date),
    secondAuctionDate: shortText(nextAction, 42),
    firstBadgeLabel: "Radar",
    secondBadgeLabel: "Próx.",
    temporalStatus: isOpen ? (p0Count > 0 ? `${p0Count} P0 aberto${p0Count > 1 ? "s" : ""}` : "Sem P0 aberto") : shortText(firstText(row?.outcome, decision, "Encerrado"), 34),
    temporalType: temporalTypeFor(score, isOpen ? p0Count : 0, decision),
    sourceValidation,
    firstAuction: entry,
    secondAuction: ceiling || entry,
    comparator: saleBase || row?.targetPrice || row?.currentPrice || entry,
    saleBase: saleBase || row?.targetPrice || row?.currentPrice || entry,
    auctioneerFee,
    acquisitionCosts,
    renovationCosts,
    carryingCosts,
    sellingCosts,
    totalCost,
    netProfit,
    roiPct,
    fixedIncomePct: 6.5,
    score,
    confidence,
    color,
    icon: strategyIcon.icon,
    iconLabel: strategyIcon.label,
    iconBasis: `${strategyIcon.basis} Importado dos casos imobiliários canônicos da app.`,
    decision: shortText(decision, 30),
    whyRadar: firstText(row?.hypothesis, analysis.summary, row?.operation, "Caso real no radar imobiliário aguardando leitura de evidência."),
    p0: p0Items.map((item) => compactText(item?.title || item?.action)).filter(Boolean),
    p0Actions: p0Items.map((item) => ({
      title: compactText(item?.title || item?.key || "Diligência"),
      action: compactText(item?.action || item?.detail || nextAction),
    })),
    quote: firstText(row?.janeMessage, analysis.jane_message, row?.learning, isOpen ? "Ainda não é compra. É candidato vivo enquanto a prova melhora a confiança." : "O descarte também é produto: ele ensina preço teto, P0 e limite de risco."),
    firstPriceLabel: "Preço entrada",
    firstPriceNote: "preço observado",
    secondPriceLabel: "Teto Halley",
    secondPriceNote: "limite disciplinado",
    salePriceLabel: "Saída base",
    salePriceNote: "venda a validar",
    purchaseCostLabel: "Preço de entrada",
    firstStepTitle: "Entrou no radar",
    firstStepText: `A ${money(entry)}, o candidato entrou porque ${firstText(row?.hypothesis, "há assimetria inicial para testar")}.`,
    secondStepTitle: "Teto e saída criam a pergunta",
    secondStepText: `O teto disciplinado está em ${money(ceiling || entry)} e a saída base em ${money(saleBase)}. A decisão agora depende das provas abertas.`,
    isLiveCandidate: isOpen,
    isRealCandidate: true,
  };
}

function radarStoriesForData(data) {
  const realStories = canonicalRealEstateRows(data)
    .map(liveStoryFromRow);
  const liveStories = realStories.filter((item) => item.isLiveCandidate);
  const closedStories = realStories.filter((item) => !item.isLiveCandidate);

  if (realStories.length) {
    return {
      closedStories,
      demoStories: [],
      items: realStories,
      liveStories,
      realStories,
      usingRealStories: true,
    };
  }

  const demoStories = REAL_ESTATE_DEMO_CASES.map(withTypeIcon);
  return {
    demoStories,
    closedStories: [],
    items: demoStories,
    liveStories: [],
    realStories: [],
    usingRealStories: false,
  };
}

function decisionBucket(item) {
  const decision = String(item.decision || "").toLowerCase();
  if (decision.includes("descartar") || decision.includes("não avançar") || decision.includes("recusar") || decision.includes("bloquear")) return "bloqueado";
  if (decision.includes("calibrar")) return "aprendizado";
  if (decision.includes("aguardar") || decision.includes("monitorar")) return "monitorar";
  return "investigar";
}

function buildRadarStats(items) {
  const buckets = items.reduce(
    (acc, item) => {
      acc[decisionBucket(item)] += 1;
      if (String(item.temporalStatus || "").toLowerCase().includes("futura")) acc.futureSecondRound += 1;
      return acc;
    },
    { aprendizado: 0, bloqueado: 0, futureSecondRound: 0, investigar: 0, monitorar: 0 },
  );

  return {
    ...buckets,
    closedCount: items.filter((item) => item.isRealCandidate && !item.isLiveCandidate).length,
    liveCount: items.filter((item) => item.isLiveCandidate).length,
    realCount: items.filter((item) => item.isRealCandidate).length,
    total: items.length,
    p0Count: items.reduce((sum, item) => sum + (item.p0?.length || 0), 0),
  };
}

function RadarSignalCard({ label, title, text, color }) {
  return (
    <article
      style={{
        background: C.panel,
        border: `1px solid ${C.border}`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 12,
        display: "grid",
        gap: 7,
        padding: 14,
      }}
    >
      <div style={{ color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>
        {label}
      </div>
      <div style={{ color: C.text, fontSize: 14, fontWeight: 900, lineHeight: 1.25 }}>{title}</div>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0 }}>{text}</p>
    </article>
  );
}

function RadarHero({ stats }) {
  return (
    <section
      data-testid="radar-imobiliario-hero"
      style={{
        background: `linear-gradient(135deg, ${C.card}, ${C.panel})`,
        border: `1px solid ${C.border}`,
        borderRadius: 16,
        display: "grid",
        gap: 18,
        gridTemplateColumns: "minmax(0, 1.05fr) minmax(320px, 0.95fr)",
        padding: 20,
      }}
    >
      <div style={{ display: "grid", gap: 16 }}>
        <div>
          <h1 style={{ color: C.text, fontSize: 34, letterSpacing: 0, lineHeight: 1.02, margin: 0 }}>
            RADAR IMOBILIÁRIO
          </h1>
          <p style={{ color: C.muted, fontSize: 14, lineHeight: 1.65, margin: "12px 0 0", maxWidth: 780 }}>
            Uma área própria para acompanhar bairros, prédios em reforma, novos leilões, novas 2ª praças e candidatos que entram, melhoram, travam ou saem do radar. O foco é contar a jornada da tese: o que vimos, por que virou hipótese, qual P0 bloqueia e qual decisão o método recomenda.
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Badge label="Bairro antes do endereço" type="info" />
          <Badge label="P0 antes de lance" type="warning" />
          <Badge label="Score com evidência" type="purple" />
          <Badge label="Fonte pública" type="success" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
          <KPICard label={stats.realCount ? "Casos reais" : "Histórias no radar"} value={stats.total} sub={stats.realCount ? "canônicos da app" : "cards de tese"} accent={C.purple} valueColor={C.purple} valueFontSize={22} />
          <KPICard label="Candidatos abertos" value={stats.liveCount} sub={stats.realCount ? "reais da app" : "vindos da app"} accent={C.gold} valueColor={C.gold} valueFontSize={22} />
          <KPICard label="Investigar/monitorar" value={stats.investigar + stats.monitorar} sub="ainda vivos" accent={C.teal} valueColor={C.teal} valueFontSize={22} />
          <KPICard label="P0 mapeados" value={stats.p0Count} sub="provas antes de decisão" accent={C.coral} valueColor={C.coral} valueFontSize={22} />
        </div>
      </div>

      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "grid", gap: 14, padding: 16 }}>
        <PatrickJane
          screen="metodo"
          state="observing"
          message="O radar não compra CEP. Ele pergunta se preço, território, saída e pendências sobrevivem juntos. Quando não sobrevivem, o melhor resultado é um não rápido."
          imageHeight={150}
          imageWidth={190}
          imageBorderColor={withAlpha(C.purple, "55")}
          imageStyle={{ objectFit: "cover", objectPosition: "center center" }}
          style={{ alignItems: "flex-start" }}
          contentStyle={{ paddingTop: 2 }}
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
          <RadarSignalCard label="Entrada" title="Sinal verificável" text="Leilão, compra direta, bairro ou prédio com fonte rastreável." color={C.sky} />
          <RadarSignalCard label="Teste" title="Conta antes da convicção" text="Preço, custos, saída provável, renda fixa e prazo competem na mesma régua." color={C.gold} />
          <RadarSignalCard label="Saída" title="Decisão explícita" text="Investigar, monitorar, travar, descartar ou usar como aprendizado." color={C.green} />
        </div>
      </div>
    </section>
  );
}

function RadarOperatingModel() {
  const steps = [
    ["01", "Bairros e cidades", "Perdizes, Apinajés e Campinas entram como territórios de teste: liquidez, renda, metragem vendável, vaga e demanda de saída.", C.sky],
    ["02", "Prédios e reforma", "A app registra área, andar, vaga, estado visual, fotos ausentes e custo provável antes de romantizar o desconto.", C.amber],
    ["03", "Leilões e 2ª praça", "Datas futuras viram alerta. Datas passadas viram aprendizado. O calendário decide quando gastar diligência pesada.", C.purple],
    ["04", "Score e decisão", "O candidato melhora quando prova aparece, piora quando P0 cresce e sai do radar quando a saída não paga o risco.", C.teal],
  ];

  return (
    <section
      data-testid="radar-imobiliario-modelo"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        display: "grid",
        gap: 16,
        padding: 18,
      }}
    >
      <div>
        <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 7, textTransform: "uppercase" }}>
          Modelo operacional
        </div>
        <h2 style={{ color: C.text, fontSize: 20, lineHeight: 1.15, margin: 0 }}>
          A mesa imobiliária agora nasce separada da Jornada da Tese
        </h2>
      </div>
      <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.65, margin: 0 }}>
        A Jornada continua explicando o método geral. Esta área vira o cockpit do investidor imobiliário: histórias compactas, uma ficha aberta por vez, evidência visual, P0, números de triagem, saída esperada e aprendizado acumulado.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 10 }}>
        {steps.map(([step, title, text, color]) => (
          <article key={step} style={{ background: C.panel, border: `1px solid ${C.border}`, borderTop: `2px solid ${color}`, borderRadius: 12, padding: 13, position: "relative", overflow: "hidden" }}>
            <div style={{ background: `radial-gradient(circle at top right, ${withAlpha(color, alpha.glow)}, transparent 70%)`, height: 70, position: "absolute", right: 0, top: 0, width: 70 }} />
            <div style={{ color, fontFamily: mono, fontSize: 10, fontWeight: 900, marginBottom: 7, position: "relative" }}>{step}</div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 900, lineHeight: 1.25, marginBottom: 6, position: "relative" }}>{title}</div>
            <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0, position: "relative" }}>{text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function RadarDecisionStrip({ stats }) {
  return (
    <section
      aria-label="Resumo de decisão do radar"
      style={{
        display: "grid",
        gap: 10,
        gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
      }}
    >
      <RadarSignalCard label="Avançar" title={`${stats.investigar} candidatos pedem investigação`} text="São casos em que preço e território já justificam abrir prova, mas ainda sem compra automática." color={C.green} />
      <RadarSignalCard label="Monitorar" title={`${stats.monitorar} candidato no calendário`} text="A data crítica ainda não chegou; a app preserva foco e evita diligência cedo demais." color={C.gold} />
      <RadarSignalCard label="Aprender" title={`${stats.aprendizado} caso para calibração`} text="Histórico também é ativo: ensina preço teto, custo total e regra de descarte." color={C.sky} />
      <RadarSignalCard label="Bloquear" title={`${stats.bloqueado} casos fora do radar ativo`} text="Quando passivo, ocupação ou saída dominam a margem, o radar registra o não." color={C.coral} />
    </section>
  );
}

function StrategyIconLegend() {
  const items = [
    iconForStrategy("Leilão / Caixa"),
    iconForStrategy("Leilão direto e venda"),
    iconForStrategy("Leilão + HF"),
    iconForStrategy("Compra direta"),
    iconForStrategy("Compra para revenda"),
    iconForStrategy("Compra direta + HF"),
    iconForStrategy("Renda / plano B"),
    iconForStrategy("Lançamento"),
    iconForStrategy("Calibração"),
  ];

  return (
    <section
      aria-label="Legenda de tipos do radar imobiliário"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        display: "grid",
        gap: 12,
        padding: 16,
      }}
    >
      <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
        Ícones por tipo de tese
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
        {items.map((item) => (
          <div key={item.label} style={{ alignItems: "center", background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, display: "grid", gap: 10, gridTemplateColumns: "44px minmax(0, 1fr)", padding: 11 }}>
            <div style={{ alignItems: "center", background: C.card, border: `1px solid ${withAlpha(C.gold, alpha.border)}`, borderRadius: "50%", color: C.gold, display: "flex", fontSize: 16, height: 44, justifyContent: "center", letterSpacing: 0, lineHeight: 1, width: 44 }}>
              {item.icon}
            </div>
            <div>
              <div style={{ color: C.text, fontSize: 12, fontWeight: 900 }}>{item.label}</div>
              <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.4, marginTop: 3 }}>{item.basis}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function pluralizeCase(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function RadarRealStoryPortfolio({ closedStories, discardingId, liveStories, onDiscard, portfolioIntro, portfolioTitle }) {
  return (
    <section
      data-testid="radar-imobiliario-portfolio"
      style={{
        display: "grid",
        gap: 18,
      }}
    >
      <div
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 14,
          display: "grid",
          gap: 8,
          padding: 16,
        }}
      >
        <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Carteira real
        </div>
        <h2 style={{ color: C.text, fontSize: 20, lineHeight: 1.15, margin: 0 }}>{portfolioTitle}</h2>
        <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.65, margin: 0 }}>{portfolioIntro}</p>
      </div>

      {liveStories.length > 0 && (
        <PerdizesCasePortfolio
          color={C.green}
          dataTestId="radar-imobiliario-abertos"
          eyebrow="Abertos"
          intro="Candidatos ainda vivos. Aqui ficam os casos que pedem P0, fonte, ocupação, matrícula, comparáveis ou decisão antes de qualquer proposta."
          discardingId={discardingId}
          items={liveStories}
          onDiscard={onDiscard}
          title={`Abertos - ${pluralizeCase(liveStories.length, "candidato real", "candidatos reais")}`}
        />
      )}

      {closedStories.length > 0 && (
        <PerdizesCasePortfolio
          color={C.coral}
          dataTestId="radar-imobiliario-fechados"
          eyebrow="Fechados / aprendizados"
          intro="Casos que saíram do radar ativo. Eles continuam visíveis porque explicam preço teto, P0, descarte, erro evitado e aprendizado para a próxima triagem."
          items={closedStories}
          title={`Fechados - ${pluralizeCase(closedStories.length, "caso real encerrado", "casos reais encerrados")}`}
        />
      )}
    </section>
  );
}

function RadarRefreshBar({ isRefreshing, onRefresh, stats }) {
  if (typeof onRefresh !== "function") return null;

  return (
    <section
      aria-label="Atualização do radar imobiliário"
      style={{
        alignItems: "center",
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        display: "flex",
        gap: 12,
        justifyContent: "space-between",
        padding: "12px 14px",
        flexWrap: "wrap",
      }}
    >
      <div>
        <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Feed imobiliário
        </div>
        <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.55, marginTop: 4 }}>
          {stats.realCount ? `${stats.realCount} casos reais carregados agora` : "Sem caso real carregado no snapshot atual"}
        </div>
      </div>
      <button
        aria-label="Atualizar radar"
        disabled={isRefreshing}
        onClick={onRefresh}
        style={{
          background: isRefreshing ? C.panel : withAlpha(C.gold, 0.12),
          border: `1px solid ${withAlpha(C.gold, isRefreshing ? 0.18 : 0.38)}`,
          borderRadius: 9,
          color: isRefreshing ? C.muted : C.gold,
          cursor: isRefreshing ? "wait" : "pointer",
          fontFamily: mono,
          fontSize: 10,
          fontWeight: 900,
          letterSpacing: "0.08em",
          padding: "9px 11px",
          textTransform: "uppercase",
        }}
        type="button"
      >
        {isRefreshing ? "Atualizando" : "Atualizar radar"}
      </button>
    </section>
  );
}

export default function RadarImobiliario({ data, onRefresh }) {
  const [discardError, setDiscardError] = useState("");
  const [discardingId, setDiscardingId] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { closedStories, items, liveStories, usingRealStories } = useMemo(() => radarStoriesForData(data), [data]);
  const stats = useMemo(() => buildRadarStats(items), [items]);
  const closedStoriesCount = Math.max(0, items.length - liveStories.length);
  const openLabel = `${liveStories.length} ${liveStories.length === 1 ? "aberto" : "abertos"}`;
  const closedLabel = `${closedStoriesCount} ${closedStoriesCount === 1 ? "encerrado" : "encerrados"}`;
  const portfolioTitle = liveStories.length
    ? `${items.length} casos reais no radar (${openLabel} / ${closedLabel})`
    : usingRealStories
      ? `${items.length} casos reais no radar (${openLabel} / ${closedLabel})`
    : "Oito histórias para mostrar que o método não depende de um único imóvel";
  const portfolioIntro = liveStories.length
    ? "A partir de agora, esta carteira mostra somente casos reais/canônicos da app: candidatos abertos primeiro, depois descartes e aprendizados reais. Abra um por vez para ver ficha, números, P0, comentário do laboratório e fonte."
    : usingRealStories
      ? "Esta carteira mostra somente casos reais/canônicos da app. Como não há aberto agora, os encerrados viram memória operacional: score, motivo do descarte, P0 e aprendizado."
    : "Cada card nasce contraído para preservar foco. Há leilão, compra direta e renda urbana: abra um por vez para ver ficha, números, P0, comentário do laboratório e fonte.";

  async function handleRefresh() {
    if (typeof onRefresh !== "function" || isRefreshing) return;
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleDiscard(item) {
    if (discardingId) return;
    const defaultReason = `Descartado manualmente pelo investidor: ${item.title} nao faz sentido manter no radar aberto.`;
    const reason = window.prompt("Motivo para descartar este candidato do radar aberto:", defaultReason);
    if (reason === null) return;
    const cleanedReason = String(reason || "").trim() || defaultReason;
    setDiscardError("");
    setDiscardingId(item.id);
    try {
      await discardRealEstateCandidate({ thesisId: item.id, reason: cleanedReason });
      if (typeof onRefresh === "function") {
        await onRefresh();
      }
    } catch (error) {
      setDiscardError(error instanceof Error ? error.message : String(error));
    } finally {
      setDiscardingId("");
    }
  }

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 18, minHeight: 640, padding: "24px 28px 40px" }}>
      <RadarHero stats={stats} />
      {discardError && (
        <section style={{ background: withAlpha(C.coral, "10"), border: `1px solid ${withAlpha(C.coral, alpha.border)}`, borderRadius: 12, color: C.coral, fontSize: 12, fontWeight: 800, lineHeight: 1.5, padding: "10px 12px" }}>
          Falha ao descartar candidato: {discardError}
        </section>
      )}
      <RadarRefreshBar isRefreshing={isRefreshing} onRefresh={handleRefresh} stats={stats} />
      <RadarOperatingModel />
      <StrategyIconLegend />
      <RadarDecisionStrip stats={stats} />
      {usingRealStories ? (
        <RadarRealStoryPortfolio
          closedStories={closedStories}
          discardingId={discardingId}
          liveStories={liveStories}
          onDiscard={handleDiscard}
          portfolioIntro={portfolioIntro}
          portfolioTitle={portfolioTitle}
        />
      ) : (
      <PerdizesCasePortfolio
        dataTestId="radar-imobiliario-portfolio"
        eyebrow="Radar imobiliário"
        intro={portfolioIntro}
        items={items}
        title={portfolioTitle}
      />
      )}
    </main>
  );
}
