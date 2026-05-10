import { useMemo, useState } from "react";
import { Badge, C, KPICard, PatrickJane, alpha, mono, withAlpha } from "../components";

const PORTAL_FALLBACK = Object.freeze({
  id: "#1786",
  title: "Portal Cantareira",
  sourceUrl: "https://www.siteleiloes.com.br/item/559/detalhes",
  auctionPrice: 233000,
  radarEntryTarget: 137308,
  assessment: 233000,
  maxPurchasePrice: 147860,
  score: 83,
  confidence: 51,
  holding: "7 meses",
  cashOut: 78941,
  debtAtSale: 111576,
  breakEven: 206326,
  targetSale: 226086,
  baseSale: 190000,
  optimisticSale: 205000,
  competitorMin: 175000,
  competitorMid: 189000,
  competitorMax: 190000,
  baseProfitAfterTax: -16326,
  fixedIncomeGain: 5300,
  p0: [
    "Confirmar ocupação antes de qualquer proposta.",
    "Validar matrícula, condomínio e débitos do edital.",
    "Checar custo total de aquisição e financiamento por 7 parcelas.",
  ],
});

const REAL_ESTATE_DEMO_CASES = Object.freeze([
  {
    id: "#PER-01",
    title: "Rua Turiassú, 362 · Perdizes",
    role: "Caso principal · house flipping",
    strategy: "House flipping",
    sourceUrl: "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-apartamento-r-turiassu-com-90-80m-com-vaga-de-garagem-sao-paulo-sp-imovel-2762843",
    area: "90,80 m² · 1 vaga",
    floor: "3º andar · apto 31",
    bedrooms: "2 dorms. a validar",
    bathrooms: "1 banheiro a validar",
    parking: "1 vaga",
    building: "Edifício Turiassú",
    firstAuctionDate: "07/05/2026 16:15",
    secondAuctionDate: "29/05/2026 16:15",
    temporalStatus: "2ª praça futura",
    temporalType: "info",
    firstAuction: 409318.94,
    secondAuction: 245591.36,
    comparator: 589900,
    saleBase: 589900,
    auctioneerFee: 12280,
    acquisitionCosts: 22000,
    renovationCosts: 45000,
    carryingCosts: 18000,
    sellingCosts: 35400,
    totalCost: 378271,
    netProfit: 176229,
    roiPct: 46.6,
    fixedIncomeGain: 24500,
    fixedIncomePct: 6.5,
    thesisPremium: 151729,
    score: 86,
    confidence: 58,
    color: C.gold,
    icon: "🔥",
    iconLabel: "Tocha / farol",
    iconBasis: "Turiassú remete à ideia de tocha, fogueira ou farol.",
    decision: "Investigar na 2ª praça",
    whyRadar: "Bairro-alvo, metragem vendável, vaga e 2ª praça muito abaixo de comparável no mesmo endereço.",
    photos: [
      {
        label: "Fachada e entrada",
        src: "/assets/demo/turiassu-spy-og.jpg",
        source: "Fonte pública do leilão",
        note: "Imagem disponível nas páginas agregadoras do leilão. Confirma a fachada/entrada da Rua Turiassú, 362.",
      },
      {
        label: "Interior do apto 31",
        src: null,
        source: "Foto não publicada",
        placeholderTitle: "Imagem interna pendente",
        note: "A fonte pública não divulgou imagem interna. Antes de proposta, pedir fotos, visitação ou evidência do estado interno.",
      },
    ],
    p0: ["ocupação", "matrícula", "débitos", "comparável real"],
    p0Actions: [
      { title: "Ocupação", action: "Ligar para leiloeiro/administradora e checar fotos, edital e visitação. Se ocupado, estimar prazo e custo de imissão na posse." },
      { title: "Matrícula", action: "Baixar matrícula atualizada no cartório de registro de imóveis e procurar ônus, penhoras, usufruto, indisponibilidade ou divergência de área/vaga." },
      { title: "Débitos", action: "Solicitar declaração de condomínio, IPTU e taxas. Separar o que fica com arrematante do que sub-roga no preço, conforme edital." },
      { title: "Comparável real", action: "Confirmar 3 anúncios/vendas similares no mesmo prédio ou raio curto, com metragem, vaga, andar e estado interno equivalentes." },
    ],
    quote: "Agora sim existe uma pergunta boa. O desconto sobreviveu ao primeiro filtro. Ainda não é compra. É investigação.",
  },
  {
    id: "#PER-02",
    title: "Av. Francisco Matarazzo, 43 · Perdizes",
    role: "Radar futuro · calendário de decisão",
    strategy: "Arbitragem de leilão",
    sourceUrl: "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apartamento-66m-perdizes/1245000",
    area: "66 m²",
    firstAuctionDate: "24/07/2026 14:00",
    secondAuctionDate: "13/08/2026 14:00",
    temporalStatus: "2ª praça futura",
    temporalType: "info",
    firstAuction: 486891.15,
    secondAuction: 292134.69,
    comparator: 490000,
    score: 78,
    confidence: 44,
    color: C.sky,
    icon: "⚙",
    iconLabel: "Indústria",
    iconBasis: "Matarazzo remete ao ciclo industrial paulista.",
    decision: "Aguardar data crítica",
    whyRadar: "A 2ª praça futura cria um ponto objetivo para reabrir análise sem gastar diligência antes da hora.",
    p0: ["comparáveis 66 m²", "vaga", "edital", "liquidez"],
    quote: "Hoje é só calendário. Em agosto, se o preço cair como previsto, a pergunta fica séria.",
  },
  {
    id: "#PER-03",
    title: "Rua Caiubí, 91 · Perdizes",
    role: "Premium · flipping institucional",
    strategy: "Flipping premium",
    sourceUrl: "https://leilaoninja.com/imovel/apartamento-com-4-dormitorios-2-suites-e-3-vagas-em-perdizes",
    area: "212 m² · 3 vagas",
    firstAuctionDate: "17/04/2026 15:00",
    secondAuctionDate: "11/05/2026 15:00",
    temporalStatus: "2ª praça hoje ou amanhã",
    temporalType: "warning",
    firstAuction: 2238000,
    secondAuction: 1343000,
    comparator: 1900000,
    score: 74,
    confidence: 38,
    color: C.purple,
    icon: "🌿",
    iconLabel: "Mata verde",
    iconBasis: "Caiubí carrega referência indígena associada à mata/natureza.",
    decision: "Só com diligência forte",
    whyRadar: "Ticket institucional, metragem rara e possível reposicionamento, mas qualquer passivo pequeno vira número grande.",
    p0: ["desocupação", "parcelamento", "débitos", "comparáveis premium"],
    quote: "O tamanho impressiona. Mas tamanho não é tese. A tese só aparece se o passivo for menor que a margem.",
  },
  {
    id: "#PER-04",
    title: "Rua Aimberê, 466 · Perdizes",
    role: "Histórico · treino do método",
    strategy: "Simulação histórica",
    sourceUrl: "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apartamento-vaga-de-garagem-6261m-perdizes-sao-paulosp/1151875",
    area: "62,61 m² · vaga",
    firstAuctionDate: "20/03/2026 17:33",
    secondAuctionDate: "27/04/2026 17:33",
    temporalStatus: "2ª praça já passou",
    temporalType: "neutral",
    firstAuction: 709865.4,
    secondAuction: 425919.24,
    comparator: 620000,
    score: 69,
    confidence: 62,
    color: C.teal,
    icon: "🪶",
    iconLabel: "Memória indígena",
    iconBasis: "Aimberê remete a referência indígena; aqui vira símbolo de memória e calibração.",
    decision: "Usar para calibrar",
    whyRadar: "Leilão já passou, mas tem dados claros para treinar preço teto, custo total e regra de descarte.",
    p0: ["preço de saída", "custos", "prazo", "benchmark"],
    quote: "Nem todo caso precisa virar compra. Alguns pagam melhor como aula.",
  },
  {
    id: "#PER-05",
    title: "Cardoso de Almeida, 1165 · Perdizes",
    role: "Caso não · passivo vence CEP",
    strategy: "Filtro de risco",
    sourceUrl: "https://www.portalzuk.com.br/imovel/sp/sao-paulo/perdizes/rua-cardoso-de-almeida-1165/35788-223050",
    area: "103,29 m²",
    firstAuctionDate: "31/03/2026 15:50",
    secondAuctionDate: "22/04/2026 15:50",
    temporalStatus: "2ª praça já passou",
    temporalType: "neutral",
    firstAuction: 1282689.75,
    secondAuction: 769613.85,
    comparator: 980000,
    score: 52,
    confidence: 70,
    color: C.coral,
    icon: "⚖",
    iconLabel: "Filtro jurídico",
    iconBasis: "Cardoso de Almeida remete a trajetória jurídica e pública.",
    decision: "Descartar ou travar",
    whyRadar: "O endereço é bom, mas ocupação, condomínio, IPTU e pagamento à vista podem consumir a margem.",
    p0: ["ocupação", "condomínio", "IPTU", "à vista"],
    quote: "O endereço é bom. A conta, nem tanto. O radar não compra CEP.",
  },
  {
    id: "#API-01",
    title: "Edifício Stella · Apinajés, 930",
    role: "Didático · regra de 2ª praça",
    strategy: "Leilão compacto",
    sourceUrl: "https://www.projudleiloes.com.br/preview/b9a9dcab-20e3-48b4-8ff2-8da9cde0d3c6.pdf",
    area: "33,13 m² · vaga indeterminada",
    firstAuctionDate: "05/12/2022 a 08/12/2022",
    secondAuctionDate: "23/01/2023 10:30",
    temporalStatus: "histórico / precisa checar fonte",
    temporalType: "neutral",
    firstAuction: 322000,
    secondAuction: 225400,
    comparator: 399000,
    score: 66,
    confidence: 48,
    color: C.amber,
    icon: "✦",
    iconLabel: "Stella / estrela",
    iconBasis: "Stella significa estrela; aqui vira símbolo de caso didático.",
    decision: "Diligência decide",
    whyRadar: "A 2ª praça abre a porta matemática, mas ocupação e custos jurídicos seguram a decisão.",
    p0: ["ocupação", "ônus", "custos", "liquidez compacta"],
    quote: "A segunda praça abriu a porta. A ocupação ainda está segurando a maçaneta.",
  },
  {
    id: "#API-02",
    title: "Perdizes Best Place · Apinajés, 789",
    role: "Armadilha · desconto com passivo",
    strategy: "Bloqueio de tese",
    sourceUrl: "https://sp.mgfimoveis.com.br/apartamento-em-leilao-perdizes-sao-paulo-sp-venda-sp-sao-paulo-303289924",
    area: "Perdizes · alto padrão",
    firstAuctionDate: "não confirmado",
    secondAuctionDate: "28/08/2023 15:30",
    temporalStatus: "arrematado/vendido",
    temporalType: "danger",
    firstAuction: 864357.42,
    secondAuction: 537391.8,
    comparator: 850000,
    score: 39,
    confidence: 82,
    color: C.coral,
    icon: "⚠",
    iconLabel: "Armadilha",
    iconBasis: "Best Place é tratado como anti-tese: nome bonito, passivo dominante.",
    decision: "Não avançar",
    whyRadar: "Débitos, ocupação, sem visitação e pagamento à vista transformam desconto aparente em risco dominante.",
    p0: ["débito alto", "ocupação", "sem visita", "à vista"],
    quote: "Quando o passivo é maior que a oportunidade, o desconto é só maquiagem.",
  },
]);

const SOURCE_RADAR_ITEMS = Object.freeze([
  {
    source: "B3 · PETR4",
    icon: "B3",
    channel: "Preço, volume, volatilidade e eventos corporativos",
    signal: "Stop técnico, faixa de preço e liquidez diária entraram em observação.",
    stage: "Tese aberta",
    stageType: "open",
    proof: "Padrão técnico + regra de saída + monitoramento do risco.",
    color: C.sky,
  },
  {
    source: "Cripto · BTCUSDT",
    icon: "₿",
    channel: "Exchange, fluxo, tendência e correlação com risco global",
    signal: "Padrão histórico mapeado; timing ainda depende de confirmação de preço.",
    stage: "Em validação",
    stageType: "warning",
    proof: "Backtest, drawdown e aderência ao regime atual.",
    color: C.purple,
  },
  {
    source: "Macro · Selic",
    icon: "%",
    channel: "Bacen, Focus, curva DI e custo de oportunidade",
    signal: "Queda de juros muda o terreno para bolsa, cripto, financiamento e imóveis.",
    stage: "Sinal detectado",
    stageType: "info",
    proof: "Impacto no benchmark de renda fixa e no preço teto das teses.",
    color: C.teal,
  },
  {
    source: "CVM · Fato relevante",
    icon: "FR",
    channel: "Comunicados oficiais, resultados e eventos de companhia",
    signal: "Evento corporativo pode mudar assimetria, risco ou gatilho de tese.",
    stage: "Hipótese formada",
    stageType: "purple",
    proof: "Documento oficial, tese de impacto e regra de invalidação.",
    color: C.gold,
  },
  {
    source: "Prefeitura · Retrofit",
    icon: "RT",
    channel: "Alvarás, obras, bairro, jornal local e sinais urbanos",
    signal: "Prédio antigo ou entorno em transformação entra no radar imobiliário.",
    stage: "Bloqueado por P0",
    stageType: "danger",
    proof: "Confirmar obra, condomínio, matrícula, custo e liquidez da saída.",
    color: C.amber,
  },
  {
    source: "Território · Perdizes",
    icon: "MAP",
    channel: "Oferta concorrente, renda, liquidez, preço/m² e micro-região",
    signal: "O bairro vira tese antes do imóvel: depois o radar procura candidatos.",
    stage: "Aprendizado registrado",
    stageType: "success",
    proof: "Comparáveis, histórico de descarte e score de território.",
    color: C.green,
  },
  {
    source: "Commodities · Petróleo",
    icon: "OIL",
    channel: "Brent, câmbio, geopolítica e impacto setorial",
    signal: "Choque de commodity pode virar hipótese em B3 ou hedge macro.",
    stage: "Sinal detectado",
    stageType: "info",
    proof: "Correlação histórica, evento causal e janela de execução.",
    color: C.coral,
  },
  {
    source: "Câmbio · Dólar",
    icon: "FX",
    channel: "Dólar, juros externos, fluxo e proteção de carteira",
    signal: "Movimento de câmbio altera teses exportadoras, importadoras e cripto.",
    stage: "Hipótese formada",
    stageType: "purple",
    proof: "Cenário, gatilho, impacto esperado e limite de risco.",
    color: C.sky,
  },
]);

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "R$ --";
  return `R$ ${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

function pct(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--%";
  return `${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%`;
}

function numberOr(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function caseEconomics(item) {
  const purchase = numberOr(item.secondAuction || item.firstAuction, 0);
  const saleBase = numberOr(item.saleBase || item.comparator, 0);
  const auctioneerFee = numberOr(item.auctioneerFee, Math.round(purchase * 0.05));
  const acquisitionCosts = numberOr(item.acquisitionCosts, Math.round(purchase * 0.08));
  const renovationCosts = numberOr(item.renovationCosts, Math.round(saleBase * 0.06));
  const carryingCosts = numberOr(item.carryingCosts, Math.round(purchase * 0.04));
  const sellingCosts = numberOr(item.sellingCosts, Math.round(saleBase * 0.06));
  const totalCost = numberOr(
    item.totalCost,
    purchase + auctioneerFee + acquisitionCosts + renovationCosts + carryingCosts + sellingCosts
  );
  const netProfit = numberOr(item.netProfit, saleBase - totalCost);
  const roiPct = numberOr(item.roiPct, totalCost > 0 ? (netProfit / totalCost) * 100 : 0);
  const fixedIncomePct = numberOr(item.fixedIncomePct, 6.5);
  const fixedIncomeGain = numberOr(item.fixedIncomeGain, Math.round(totalCost * (fixedIncomePct / 100)));
  const thesisPremium = numberOr(item.thesisPremium, netProfit - fixedIncomeGain);

  return {
    acquisitionCosts,
    auctioneerFee,
    carryingCosts,
    fixedIncomeGain,
    fixedIncomePct,
    isModeled: !item.totalCost,
    netProfit,
    purchase,
    renovationCosts,
    roiPct,
    saleBase,
    sellingCosts,
    thesisPremium,
    totalCost,
  };
}

function displayCaseId(value) {
  const text = String(value || "").trim();
  if (!text) return PORTAL_FALLBACK.id;
  return text.startsWith("#") ? text : `#${text}`;
}

function cleanAssetTitle(value) {
  const text = String(value || "").replace(/^REAL\s*[-–—]\s*/i, "").trim();
  return text || PORTAL_FALLBACK.title;
}

function sectionTitle(eyebrow, title, color = C.gold) {
  return (
    <div>
      <div style={{ color, fontFamily: mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", marginBottom: 7, textTransform: "uppercase" }}>
        {eyebrow}
      </div>
      <h2 style={{ color: C.text, fontSize: 20, lineHeight: 1.15, margin: 0 }}>{title}</h2>
    </div>
  );
}

function Section({ eyebrow, title, color = C.gold, children, style = {}, ...props }) {
  return (
    <section
      {...props}
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        display: "grid",
        gap: 16,
        padding: 18,
        ...style,
      }}
    >
      {sectionTitle(eyebrow, title, color)}
      {children}
    </section>
  );
}

function InsightCard({ label, title, text, color }) {
  return (
    <article style={{ background: C.panel, border: `1px solid ${C.border}`, borderLeft: `3px solid ${color}`, borderRadius: 12, padding: 14 }}>
      <div style={{ color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 8, textTransform: "uppercase" }}>{label}</div>
      <div style={{ color: C.text, fontSize: 14, fontWeight: 800, lineHeight: 1.25, marginBottom: 6 }}>{title}</div>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0 }}>{text}</p>
    </article>
  );
}

function FlowStep({ step, title, text, color }) {
  return (
    <div style={{ alignItems: "start", display: "grid", gap: 11, gridTemplateColumns: "42px minmax(0, 1fr)" }}>
      <div style={{ alignItems: "center", background: withAlpha(color, alpha.subtle), border: `1px solid ${withAlpha(color, alpha.border)}`, borderRadius: "50%", color, display: "flex", fontFamily: mono, fontSize: 12, fontWeight: 900, height: 42, justifyContent: "center", width: 42 }}>
        {step}
      </div>
      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, minHeight: 76, padding: "12px 13px" }}>
        <div style={{ color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.25, marginBottom: 5 }}>{title}</div>
        <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0 }}>{text}</p>
      </div>
    </div>
  );
}

function ComparisonRow({ label, value, detail, color }) {
  return (
    <div style={{ borderBottom: `1px solid ${C.line}`, display: "grid", gap: 10, gridTemplateColumns: "minmax(0, 1fr) 112px", padding: "10px 0" }}>
      <div>
        <div style={{ color: C.text, fontSize: 12, fontWeight: 800 }}>{label}</div>
        <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, marginTop: 3 }}>{detail}</div>
      </div>
      <div style={{ color, fontFamily: mono, fontSize: 14, fontWeight: 900, textAlign: "right", whiteSpace: "nowrap" }}>{value}</div>
    </div>
  );
}

function EvidencePill({ label, value, note, color }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${withAlpha(color, alpha.border)}`, borderLeft: `3px solid ${color}`, borderRadius: 12, padding: "11px 12px" }}>
      <div style={{ color, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 6, textTransform: "uppercase" }}>{label}</div>
      <div style={{ color: C.text, fontFamily: mono, fontSize: 17, fontWeight: 900, whiteSpace: "nowrap" }}>{value}</div>
      <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.45, marginTop: 5 }}>{note}</div>
    </div>
  );
}

function ThesisIcon({ item, isOpen, size = 44 }) {
  return (
    <span
      aria-hidden="true"
      title={item.iconLabel}
      style={{
        alignItems: "center",
        background: isOpen ? withAlpha(item.color, "22") : C.card,
        border: `1px solid ${withAlpha(item.color, isOpen ? "55" : alpha.border)}`,
        borderRadius: "50%",
        boxShadow: isOpen ? `0 0 18px ${withAlpha(item.color, "28")}` : "none",
        color: item.color,
        display: "inline-flex",
        flexShrink: 0,
        fontSize: Math.round(size * 0.43),
        height: size,
        justifyContent: "center",
        lineHeight: 1,
        width: size,
      }}
    >
      {item.icon || "•"}
    </span>
  );
}

function IconBasis({ item }) {
  if (!item.iconLabel && !item.iconBasis) return null;

  return (
    <div style={{ alignItems: "center", background: withAlpha(item.color, "10"), border: `1px solid ${withAlpha(item.color, alpha.border)}`, borderRadius: 999, color: C.muted, display: "inline-flex", fontSize: 10, gap: 7, lineHeight: 1.4, padding: "5px 9px", width: "fit-content" }}>
      <span style={{ color: item.color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>{item.iconLabel}</span>
      <span>{item.iconBasis}</span>
    </div>
  );
}

function realEstateCandidateFromData(data) {
  const rows = Array.isArray(data?.thesisRows) ? data.thesisRows : [];
  const realEstateRows = rows.filter((row) => row?.frente === "Imóveis" || row?.front === "Imóveis" || row?.front === "imoveis");
  const portalRows = realEstateRows.filter((row) => String(row?.ativo || row?.asset || row?.action || "").toLowerCase().includes("portal"));
  const portal = portalRows.find((row) => Number(row?.currentPrice || row?.current_price_brl || 0) >= 230000) || portalRows[0];
  const selected = portal || realEstateRows.find((row) => row?.realEstateAnalysis || row?.real_estate_analysis) || null;
  const analysis = selected?.realEstateAnalysis || selected?.real_estate_analysis || {};

  if (!selected) return PORTAL_FALLBACK;

  return {
    ...PORTAL_FALLBACK,
    id: selected.id || selected.thesisId || selected.thesis_id || PORTAL_FALLBACK.id,
    title: selected.ativo || selected.asset || selected.action || PORTAL_FALLBACK.title,
    sourceUrl: selected.sourceUrl || selected.source_url || PORTAL_FALLBACK.sourceUrl,
    auctionPrice: selected.currentPrice || selected.current_price_brl || PORTAL_FALLBACK.auctionPrice,
    radarEntryTarget: selected.entrada || selected.entryPrice || selected.entry_price_brl || PORTAL_FALLBACK.radarEntryTarget,
    assessment: selected.currentPrice || selected.current_price_brl || PORTAL_FALLBACK.assessment,
    maxPurchasePrice: analysis.max_purchase_price || analysis.maxPurchasePrice || PORTAL_FALLBACK.maxPurchasePrice,
    score: Number(analysis.score ?? selected.score ?? PORTAL_FALLBACK.score),
    confidence: Number(analysis.confidence ?? selected.confidence ?? PORTAL_FALLBACK.confidence),
    p0: Array.isArray(analysis.pending_items)
      ? analysis.pending_items.filter((item) => item?.priority === "P0").map((item) => item.title || item.action).filter(Boolean)
      : PORTAL_FALLBACK.p0,
  };
}

function Hero({ thesis }) {
  return (
    <section style={{ background: `linear-gradient(135deg, ${C.card}, ${C.panel})`, border: `1px solid ${C.border}`, borderRadius: 16, display: "grid", gap: 18, gridTemplateColumns: "minmax(0, 1.05fr) minmax(320px, 0.95fr)", padding: 20 }}>
      <div style={{ display: "grid", gap: 16 }}>
        <div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.12em", marginBottom: 9, textTransform: "uppercase" }}>
            Jornada da Tese
          </div>
          <h1 style={{ color: C.text, fontSize: 34, letterSpacing: "-0.03em", lineHeight: 1.02, margin: 0 }}>
            IA investigadora de teses
          </h1>
          <p style={{ color: C.muted, fontSize: 14, lineHeight: 1.65, margin: "12px 0 0", maxWidth: 760 }}>
            O Grão observa o mundo real, combina sinais macro como Selic, mercado, território e evidências públicas, transforma ruído em hipótese testável e simula antes de arriscar capital.
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Badge label="Radar contínuo" type="info" />
          <Badge label="Método científico" type="purple" />
          <Badge label="P0 antes de convicção" type="warning" />
          <Badge label="Aprendizado proprietário" type="success" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          <KPICard label="Caso guia" value={displayCaseId(thesis.id)} sub={cleanAssetTitle(thesis.title)} accent={C.gold} valueColor={C.gold} valueFontSize={21} />
          <KPICard label="Score inicial" value={`${thesis.score}/100`} sub="qualidade do candidato" accent={C.amber} valueColor={C.amber} valueFontSize={21} />
          <KPICard label="Confiança" value={`${thesis.confidence}/100`} sub="provas já confirmadas" accent={C.sky} valueColor={C.sky} valueFontSize={21} />
        </div>
      </div>
      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "grid", gap: 14, padding: 16 }}>
        <PatrickJane
          screen="metodo"
          state="observing"
          message="A história boa não começa com compra. Começa com uma pergunta simples: por que este sinal merece tempo, capital e risco?"
          imageHeight={150}
          imageWidth={190}
          imageBorderColor={C.gold + "45"}
          imageStyle={{ objectFit: "cover", objectPosition: "center center" }}
          style={{ alignItems: "flex-start" }}
          contentStyle={{ paddingTop: 2 }}
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
          {[
            ["Investidor", "Disciplina antes de entusiasmo", C.gold],
            ["Produto", "Fonte, método e decisão", C.teal],
            ["Regra", "P0 resolvido antes de avançar", C.coral],
          ].map(([label, value, color]) => (
            <div key={label} style={{ background: C.card, border: `1px solid ${C.border}`, borderLeft: `2px solid ${color}`, borderRadius: 10, padding: "9px 10px" }}>
              <div style={{ color, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.08em", marginBottom: 5, textTransform: "uppercase" }}>{label}</div>
              <div style={{ color: C.text, fontSize: 11, fontWeight: 800, lineHeight: 1.35 }}>{value}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function InvestorLens() {
  return (
    <Section eyebrow="Olhar do investidor" title="O que precisa ficar óbvio em 3 minutos" color={C.teal}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 10 }}>
        {[
          ["01", "Fonte", "De onde veio o sinal e se é verificável.", C.sky],
          ["02", "Tese", "Por que isso virou hipótese, não palpite.", C.gold],
          ["03", "Prova", "O que foi validado e o que ainda bloqueia.", C.teal],
          ["04", "Capital", "Quanto entra, quanto pode sair e contra qual benchmark compete.", C.amber],
          ["05", "Memória", "O que o laboratório aprende para repetir ou evitar.", C.purple],
        ].map(([step, title, text, color]) => (
          <InsightCard key={step} label={step} title={title} text={text} color={color} />
        ))}
      </div>
    </Section>
  );
}

function RadarPermanent() {
  return (
    <Section eyebrow="Radar permanente" title="A IA observa o mundo real antes de abrir uma tese" color={C.sky}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
        <InsightCard label="Macro" title="Selic muda o terreno" color={C.sky} text="Se o ciclo de juros continua caindo, o Halley reavalia apetite por bolsa, cripto, financiamento imobiliário e custo de oportunidade em renda fixa." />
        <InsightCard label="Mercado" title="Preço conversa com padrão" color={C.teal} text="Ticks, faixas, volume e comportamento recente apontam onde há padrão suficiente para formular hipótese testável." />
        <InsightCard label="Território" title="Imóvel depende do entorno" color={C.purple} text="Bairro, liquidez, comparáveis, reforma do condomínio, oferta concorrente e preço teto entram no score antes de qualquer proposta." />
      </div>
    </Section>
  );
}

function SourceRadarCard({ item }) {
  return (
    <article style={{ background: C.panel, borderBottom: `1px solid ${withAlpha(item.color, alpha.border)}`, borderLeft: `1px solid ${withAlpha(item.color, alpha.border)}`, borderRight: `1px solid ${withAlpha(item.color, alpha.border)}`, borderTop: `2px solid ${item.color}`, borderRadius: 14, display: "grid", gap: 10, minHeight: 210, overflow: "hidden", padding: 14, position: "relative" }}>
      <div style={{ background: `radial-gradient(circle at top right, ${withAlpha(item.color, alpha.glow)}, transparent 70%)`, height: 92, position: "absolute", right: 0, top: 0, width: 110 }} />
      <div style={{ alignItems: "flex-start", display: "flex", gap: 11, justifyContent: "space-between", position: "relative" }}>
        <div style={{ alignItems: "center", background: withAlpha(item.color, "12"), border: `1px solid ${withAlpha(item.color, alpha.border)}`, borderRadius: 12, color: item.color, display: "flex", flexShrink: 0, fontFamily: mono, fontSize: 10, fontWeight: 900, height: 42, justifyContent: "center", letterSpacing: "0.04em", width: 42 }}>
          {item.icon}
        </div>
        <Badge label={item.stage} type={item.stageType} />
      </div>
      <div style={{ position: "relative" }}>
        <div style={{ color: item.color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 6, textTransform: "uppercase" }}>{item.source}</div>
        <div style={{ color: C.text, fontSize: 14, fontWeight: 900, lineHeight: 1.25 }}>{item.channel}</div>
      </div>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.55, margin: 0, position: "relative" }}>{item.signal}</p>
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderLeft: `3px solid ${item.color}`, borderRadius: 10, marginTop: "auto", padding: "9px 10px", position: "relative" }}>
        <div style={{ color: C.muted, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.08em", marginBottom: 5, textTransform: "uppercase" }}>O que prova</div>
        <div style={{ color: C.text, fontSize: 11, fontWeight: 800, lineHeight: 1.45 }}>{item.proof}</div>
      </div>
    </article>
  );
}

function SourceRadar() {
  return (
    <Section data-testid="source-radar" eyebrow="Radar de fontes" title="O radar não olha só ativos. Ele olha fontes." color={C.gold}>
      <div style={{ background: withAlpha(C.gold, "08"), border: `1px solid ${withAlpha(C.gold, alpha.border)}`, borderRadius: 13, display: "grid", gap: 10, gridTemplateColumns: "minmax(0, 1.3fr) minmax(280px, 0.7fr)", padding: 14 }}>
        <p style={{ color: C.text, fontSize: 14, fontWeight: 800, lineHeight: 1.55, margin: 0 }}>
          Representatividade importa: B3, cripto e leilão são só três manifestações do mesmo método. O Halley observa mercado financeiro, macro, fontes públicas, território e sinais alternativos; depois separa o que é ruído, sinal, hipótese, tese ou descarte.
        </p>
        <div style={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 7, justifyContent: "flex-end" }}>
          <Badge label="Sinal detectado" type="info" />
          <Badge label="Hipótese formada" type="purple" />
          <Badge label="Em validação" type="warning" />
          <Badge label="Tese aberta" type="open" />
          <Badge label="Bloqueado por P0" type="danger" />
          <Badge label="Aprendizado registrado" type="success" />
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
        {SOURCE_RADAR_ITEMS.map((item) => <SourceRadarCard key={item.source} item={item} />)}
      </div>
    </Section>
  );
}

function SimulationLoop() {
  return (
    <Section eyebrow="Simulação também ensina" title="Não precisamos aprender só quando perdemos dinheiro" color={C.purple}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
        <InsightCard label="Histórico" title="Voltar no tempo" color={C.gold} text="A tese é testada contra ciclos passados para saber se o padrão resistiu fora do caso bonito." />
        <InsightCard label="Presente" title="Paper antes do capital" color={C.teal} text="Quando a tese ainda não merece execução, ela entra em acompanhamento simulado para medir aderência, ruído e timing." />
        <InsightCard label="Memória" title="Aprendizado proprietário" color={C.green} text="Cada acerto fortalece critérios. Cada falha vira regra: o que confirmar, o que evitar e o que exigir antes do próximo go-live." />
      </div>
    </Section>
  );
}

function StoryMetric({ label, value, note, color }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${withAlpha(color, alpha.border)}`, borderTop: `2px solid ${color}`, borderRadius: 12, padding: 12 }}>
      <div style={{ color: C.muted, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 6, textTransform: "uppercase" }}>{label}</div>
      <div style={{ color, fontFamily: mono, fontSize: 18, fontWeight: 900, whiteSpace: "nowrap" }}>{value}</div>
      <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.45, marginTop: 5 }}>{note}</div>
    </div>
  );
}

function statusBadgeType(type) {
  if (type === "danger") return "danger";
  if (type === "warning") return "warning";
  if (type === "info") return "info";
  return "neutral";
}

function CompetitorMap({ item }) {
  const economics = caseEconomics(item);
  const reference = economics.saleBase || item.comparator || item.secondAuction || item.firstAuction;
  const competitors = [
    { label: "Candidato", price: economics.purchase, x: 49, y: 52, color: C.gold, note: item.secondAuctionDate ? "2ª praça" : "entrada" },
    { label: "Ref. venda 01", price: reference, x: 68, y: 36, color: C.teal, note: "comparável base" },
    { label: "Ref. venda 02", price: Math.round(reference * 1.05), x: 30, y: 42, color: C.sky, note: "faixa alta" },
    { label: "Ref. venda 03", price: Math.round(reference * 0.94), x: 58, y: 70, color: C.purple, note: "faixa baixa" },
  ];

  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
      <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", gap: 10, padding: "12px 14px 0" }}>
        <div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 4, textTransform: "uppercase" }}>Mapa de concorrentes</div>
          <div style={{ color: C.text, fontSize: 14, fontWeight: 800 }}>{item.title} · saída a validar</div>
        </div>
        <Badge label="referências a validar" type="warning" />
      </div>
      <div style={{ height: 230, margin: 14, position: "relative", borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden", background: `linear-gradient(135deg, ${C.faint}, ${C.card})` }}>
        <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${withAlpha(C.sky, "10")} 1px, transparent 1px), linear-gradient(90deg, ${withAlpha(C.sky, "10")} 1px, transparent 1px)`, backgroundSize: "42px 42px" }} />
        <div style={{ background: withAlpha(C.green, "15"), border: `1px solid ${withAlpha(C.green, alpha.border)}`, borderRadius: 999, height: 122, left: "30%", position: "absolute", top: "22%", transform: "rotate(-14deg)", width: 360 }} />
        <div style={{ background: withAlpha(C.sky, "15"), height: 10, left: "-4%", position: "absolute", top: "48%", transform: "rotate(-9deg)", width: "110%" }} />
        <div style={{ background: withAlpha(C.gold, "16"), height: 8, left: "15%", position: "absolute", top: "12%", transform: "rotate(37deg)", width: "72%" }} />
        <div style={{ color: withAlpha(C.text, "55"), fontFamily: mono, fontSize: 9, fontWeight: 800, left: "7%", position: "absolute", top: "50%", transform: "rotate(-9deg)" }}>Eixo do candidato</div>
        <div style={{ color: withAlpha(C.text, "45"), fontFamily: mono, fontSize: 9, fontWeight: 800, left: "54%", position: "absolute", top: "23%", transform: "rotate(37deg)" }}>Bairro-alvo</div>
        {competitors.map((pin) => (
          <div key={pin.label} style={{ left: `${pin.x}%`, position: "absolute", top: `${pin.y}%`, transform: "translate(-50%, -50%)" }}>
            <div style={{ alignItems: "center", background: pin.color, border: `2px solid ${C.bg}`, borderRadius: "50% 50% 50% 0", boxShadow: `0 0 18px ${withAlpha(pin.color, "55")}`, display: "flex", height: 30, justifyContent: "center", transform: "rotate(-45deg)", width: 30 }}>
              <span style={{ color: C.bg, fontFamily: mono, fontSize: 10, fontWeight: 900, transform: "rotate(45deg)" }}>{pin.label === "Candidato" ? "T" : "R"}</span>
            </div>
            <div style={{ background: C.card, border: `1px solid ${withAlpha(pin.color, alpha.border)}`, borderRadius: 8, marginTop: 5, minWidth: 98, padding: "5px 7px" }}>
              <div style={{ color: pin.color, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.06em", textTransform: "uppercase" }}>{pin.label}</div>
              <div style={{ color: C.text, fontFamily: mono, fontSize: 11, fontWeight: 900 }}>{money(pin.price)}</div>
              <div style={{ color: C.muted, fontSize: 9 }}>{pin.note}</div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "0 14px 13px" }}>
        O mapa não aprova a tese sozinho. Ele mostra quem disputaria a venda: se a referência de venda não for realista, o score cai antes de gastar capital.
        {economics.isModeled ? " Nos casos sem comparáveis comprovados, os pontos são uma faixa preliminar para orientar a diligência." : ""}
      </div>
    </div>
  );
}

function PropertyFact({ label, value, color = C.gold }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderLeft: `3px solid ${color}`, borderRadius: 10, padding: "9px 10px" }}>
      <div style={{ color: C.muted, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 5, textTransform: "uppercase" }}>{label}</div>
      <div style={{ color: C.text, fontSize: 12, fontWeight: 900, lineHeight: 1.25 }}>{value}</div>
    </div>
  );
}

function valueOrPending(value, fallback = "a validar") {
  return value || fallback;
}

function p0ActionFor(label) {
  const text = String(label || "").toLowerCase();
  if (text.includes("ocup") || text.includes("desocup") || text.includes("visita")) {
    return "Confirmar ocupação, possibilidade de visita, fotos atuais e custo/prazo de imissão na posse com leiloeiro, administradora ou fonte oficial.";
  }
  if (text.includes("matr") || text.includes("ônus") || text.includes("penhora")) {
    return "Baixar matrícula atualizada e checar ônus, penhoras, indisponibilidade, usufruto, divergência de área e vínculo da vaga.";
  }
  if (text.includes("déb") || text.includes("cond") || text.includes("iptu") || text.includes("taxa")) {
    return "Solicitar/consultar condomínio, IPTU e taxas; separar valores sub-rogados no preço dos custos que ficariam com o arrematante.";
  }
  if (text.includes("compar") || text.includes("liquidez") || text.includes("benchmark") || text.includes("saída")) {
    return "Validar anúncios e vendas semelhantes no mesmo prédio ou raio curto, com metragem, vaga, andar, estado interno e tempo de anúncio comparáveis.";
  }
  if (text.includes("parcel") || text.includes("financ") || text.includes("à vista")) {
    return "Confirmar regra de pagamento no edital: à vista, parcelamento, financiamento, caução, prazo e impacto no caixa necessário.";
  }
  return "Transformar este ponto em evidência: abrir fonte, coletar documento ou falar com responsável antes de elevar a tese para execução.";
}

function detailItem(item) {
  return {
    ...item,
    building: item.building || item.title,
    floor: item.floor || "andar a validar",
    bedrooms: item.bedrooms || "quartos a validar",
    bathrooms: item.bathrooms || "banheiros a validar",
    parking: item.parking || (String(item.area || "").toLowerCase().includes("vaga") ? "vaga informada" : "vaga a validar"),
    p0Actions: item.p0Actions?.length
      ? item.p0Actions
      : (item.p0 || []).map((title) => ({ title, action: p0ActionFor(title) })),
    photos: item.photos?.length
      ? item.photos
      : [
          {
            label: "Fachada / fonte visual",
            src: null,
            source: "foto a validar",
            placeholderTitle: "Foto da fachada pendente",
            note: "A fonte ainda precisa ser aberta ou anexada. Não usar imagem genérica para defender a tese.",
          },
          {
            label: "Interior / estado do imóvel",
            src: null,
            source: "prova pendente",
            placeholderTitle: "Imagem interna pendente",
            note: "Sem imagem interna, reforma e ocupação continuam como incertezas econômicas relevantes.",
          },
        ],
  };
}

function PropertySnapshot({ item }) {
  const property = detailItem(item);
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "grid", gap: 12, padding: 16 }}>
      <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Ficha do imóvel</div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 900 }}>{property.building} · o ativo antes da tese</div>
        </div>
        <Badge label="dados a validar no edital" type="warning" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 8 }}>
        <PropertyFact label="Área" value={valueOrPending(property.area)} color={C.sky} />
        <PropertyFact label="Andar" value={property.floor} color={C.gold} />
        <PropertyFact label="Quartos" value={property.bedrooms} color={C.purple} />
        <PropertyFact label="Banheiros" value={property.bathrooms} color={C.teal} />
        <PropertyFact label="Vagas" value={property.parking} color={C.amber} />
        <PropertyFact label="Estratégia" value={valueOrPending(property.strategy)} color={C.green} />
      </div>
      <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0 }}>
        A metragem e a vaga criam a hipótese de saída; quartos, banheiros, estado interno e ocupação ainda precisam ser confirmados antes de transformar o desconto em decisão.
      </p>
    </div>
  );
}

function PhotoEvidenceCard({ photo, color }) {
  const hasImage = Boolean(photo.src);
  return (
    <figure style={{ background: C.card, border: `1px solid ${withAlpha(color, alpha.border)}`, borderRadius: 13, margin: 0, overflow: "hidden" }}>
      <div style={{ alignItems: "center", background: hasImage ? C.faint : `linear-gradient(135deg, ${withAlpha(color, "13")}, ${C.panel})`, display: "flex", height: 188, justifyContent: "center", overflow: "hidden", position: "relative" }}>
        {hasImage ? (
          <img src={photo.src} alt={photo.label} style={{ display: "block", height: "100%", objectFit: "cover", objectPosition: "center", width: "100%" }} />
        ) : (
          <div style={{ alignItems: "center", display: "grid", gap: 8, justifyItems: "center", padding: 18, textAlign: "center" }}>
            <div style={{ alignItems: "center", border: `1px solid ${withAlpha(color, alpha.border)}`, borderRadius: "50%", color, display: "flex", fontFamily: mono, fontSize: 24, fontWeight: 900, height: 54, justifyContent: "center", width: 54 }}>
              ?
            </div>
            <div style={{ color: C.text, fontSize: 13, fontWeight: 900 }}>{photo.placeholderTitle || "Imagem pendente"}</div>
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, maxWidth: 240 }}>Não vamos preencher com imagem genérica: este ponto vira diligência P0.</div>
          </div>
        )}
        <div style={{ background: withAlpha(C.bg, "82"), border: `1px solid ${withAlpha(color, alpha.border)}`, borderRadius: 999, color, fontFamily: mono, fontSize: 8, fontWeight: 900, left: 10, letterSpacing: "0.08em", padding: "5px 8px", position: "absolute", textTransform: "uppercase", top: 10 }}>
          {photo.source}
        </div>
      </div>
      <figcaption style={{ display: "grid", gap: 5, padding: "11px 12px" }}>
        <div style={{ color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>{photo.label}</div>
        <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>{photo.note}</div>
      </figcaption>
    </figure>
  );
}

function PropertyPhotoGallery({ item }) {
  const property = detailItem(item);
  const photos = property.photos;
  const hasAnyImage = photos.some((photo) => photo.src);

  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "grid", gap: 12, padding: 16 }}>
      <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div>
          <div style={{ color: C.sky, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Evidência visual do imóvel</div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 900 }}>{hasAnyImage ? "Fotos disponíveis e lacunas visuais" : "Fotos ainda são prova aberta"}</div>
        </div>
        <Badge label="não usar imagem genérica" type="warning" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
        {photos.map((photo, index) => (
          <PhotoEvidenceCard key={photo.label} photo={photo} color={index === 0 ? C.sky : C.coral} />
        ))}
      </div>
      <div style={{ background: withAlpha(C.gold, "10"), border: `1px solid ${withAlpha(C.gold, alpha.border)}`, borderRadius: 12, color: C.text, fontSize: 12, fontWeight: 800, lineHeight: 1.55, padding: "10px 12px" }}>
        Leitura para a demo: foto ajuda a materializar o caso, mas não prova valor de saída. Se fachada, interior ou ocupação não forem confirmados, a tese fica aberta ou bloqueada.
      </div>
    </div>
  );
}

function P0Diligence({ item }) {
  const property = detailItem(item);
  const actions = property.p0Actions;
  return (
    <div style={{ background: withAlpha(C.coral, "08"), border: `1px solid ${withAlpha(C.coral, alpha.border)}`, borderRadius: 14, display: "grid", gap: 12, padding: 16 }}>
      <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div>
          <div style={{ color: C.coral, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Pendências P0 · bloqueiam decisão</div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 900 }}>O que a app ainda não conseguiu confirmar</div>
        </div>
        <Badge label={`${actions.length} P0 abertas`} type="danger" />
      </div>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0 }}>
        Enquanto estes pontos não forem comprovados, a tese não vira compra. A tela mostra o próximo passo prático para transformar dúvida em evidência.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
        {actions.map((pending, index) => (
          <div key={pending.title} style={{ background: C.card, border: `1px solid ${withAlpha(C.coral, alpha.border)}`, borderLeft: `3px solid ${C.coral}`, borderRadius: 12, padding: 12 }}>
            <div style={{ color: C.coral, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>P0-{index + 1} · {pending.title}</div>
            <div style={{ color: C.text, fontSize: 12, fontWeight: 800, lineHeight: 1.45, marginBottom: 5 }}>Como confirmar</div>
            <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0 }}>{pending.action}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CostLine({ label, value, color = C.text }) {
  return (
    <div style={{ borderBottom: `1px solid ${C.line}`, display: "grid", gap: 10, gridTemplateColumns: "minmax(0, 1fr) 118px", padding: "8px 0" }}>
      <div style={{ color: C.muted, fontSize: 11, fontWeight: 700 }}>{label}</div>
      <div style={{ color, fontFamily: mono, fontSize: 12, fontWeight: 900, textAlign: "right", whiteSpace: "nowrap" }}>{money(value)}</div>
    </div>
  );
}

function FinancialOutcome({ item }) {
  const economics = caseEconomics(item);
  const resultColor = economics.netProfit >= 0 ? C.green : C.coral;
  const premiumColor = economics.thesisPremium >= 0 ? C.green : C.coral;

  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "grid", gap: 14, padding: 16 }}>
      <div>
        <div style={{ color: C.green, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Resultado simulado vs renda fixa</div>
        <div style={{ color: C.text, fontSize: 15, fontWeight: 900 }}>A saída precisa pagar custo, tempo e risco operacional</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 12 }}>
        <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: 13 }}>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 8, textTransform: "uppercase" }}>Custo final estimado</div>
          <CostLine label="Lance 2ª praça" value={economics.purchase} color={C.gold} />
          <CostLine label="Comissão leiloeiro" value={economics.auctioneerFee} />
          <CostLine label="ITBI, registro e documentação" value={economics.acquisitionCosts} />
          <CostLine label="Reforma / regularização" value={economics.renovationCosts} />
          <CostLine label="Carregamento até venda" value={economics.carryingCosts} />
          <CostLine label="Venda: comissão e custos" value={economics.sellingCosts} />
          <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", marginTop: 10 }}>
            <span style={{ color: C.text, fontSize: 12, fontWeight: 900 }}>Total econômico</span>
            <span style={{ color: C.amber, fontFamily: mono, fontSize: 17, fontWeight: 900 }}>{money(economics.totalCost)}</span>
          </div>
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          <StoryMetric label="Venda base" value={money(economics.saleBase)} note="referência de venda a validar" color={C.teal} />
          <StoryMetric label="Lucro líquido" value={money(economics.netProfit)} note="após custos estimados" color={resultColor} />
          <StoryMetric label="ROI estimado" value={`${economics.roiPct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`} note="sobre custo final estimado" color={C.gold} />
          <StoryMetric label="Renda fixa estimada" value={money(economics.fixedIncomeGain)} note={`${economics.fixedIncomePct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% no mesmo prazo`} color={C.sky} />
        </div>
      </div>
      <div style={{ background: withAlpha(premiumColor, "10"), border: `1px solid ${withAlpha(premiumColor, alpha.border)}`, borderRadius: 12, color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.55, padding: "11px 12px" }}>
        Leitura da tese: se as premissas forem confirmadas, o prêmio estimado sobre renda fixa é de {money(economics.thesisPremium)}.
        {economics.isModeled ? " Este é um modelo preliminar para equalizar a comparação entre candidatos; os P0 ainda podem mudar a conta." : ""}
        {" "}Se a referência de venda cair ou os P0 aumentarem o custo, a tese volta para observação ou descarte.
      </div>
    </div>
  );
}

function CandidateScreeningNumbers({ item }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, display: "grid", gap: 12, padding: 16 }}>
      <div>
        <div style={{ color: item.color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Números da triagem</div>
        <div style={{ color: C.text, fontSize: 15, fontWeight: 900 }}>O que já dá para medir antes da diligência pesada</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
        <KPICard label="1ª praça" value={money(item.firstAuction)} sub={item.firstAuctionDate} accent={C.sky} valueColor={C.sky} valueFontSize={18} />
        <KPICard label="2ª praça" value={money(item.secondAuction)} sub={item.secondAuctionDate} accent={item.color} valueColor={item.color} valueFontSize={18} />
        <KPICard label="Referência venda" value={money(item.comparator)} sub="saída a validar" accent={C.teal} valueColor={C.teal} valueFontSize={18} />
        <KPICard label="Score / confiança" value={`${item.score}/${item.confidence}`} sub="potencial vs prova" accent={C.gold} valueColor={C.gold} valueFontSize={18} />
      </div>
      <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0 }}>
        Estes números não autorizam compra sozinhos. Eles dizem se vale abrir diligência: preço, saída possível, qualidade do candidato e quanto da tese já está comprovado.
      </p>
    </div>
  );
}

function ExitDemand({ item }) {
  return (
    <div style={{ background: withAlpha(C.teal, "08"), border: `1px solid ${withAlpha(C.teal, alpha.border)}`, borderRadius: 14, display: "grid", gap: 12, padding: 16 }}>
      <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div>
          <div style={{ color: C.teal, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>Demanda de saída</div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 900 }}>Preço de referência é hipótese, venda realizada é prova</div>
        </div>
        <Badge label="parcial / a validar" type="warning" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
        <PropertyFact label="Referência usada" value={money(item.comparator)} color={C.teal} />
        <PropertyFact label="Status da prova" value="parcialmente comprovada" color={C.amber} />
        <PropertyFact label="Próxima evidência" value="venda recente ou corretor" color={C.sky} />
      </div>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: 0 }}>
        A pergunta não é “existe anúncio?”. É: existe comprador real nessa faixa, neste prédio ou raio curto, com metragem e estado comparáveis? Se não houver resposta, a tese continua aberta.
      </p>
    </div>
  );
}

function CaseNarrative({ item }) {
  const economics = caseEconomics(item);

  return (
    <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(360px, 0.9fr) minmax(0, 1.1fr)" }}>
      <div style={{ background: `linear-gradient(135deg, ${withAlpha(item.color, "13")}, ${C.panel})`, border: `1px solid ${withAlpha(item.color, alpha.border)}`, borderRadius: 14, display: "grid", gap: 14, padding: 16 }}>
        <div>
          <div style={{ color: item.color, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.11em", marginBottom: 8, textTransform: "uppercase" }}>{item.role}</div>
          <h3 style={{ color: C.text, fontSize: 23, lineHeight: 1.08, margin: 0 }}>{item.strategy} · por que virou candidato</h3>
          <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.65, margin: "10px 0 0" }}>
            {item.whyRadar} A leitura não é “comprar porque caiu”; é descobrir se preço, território, saída e pendências P0 sobrevivem juntos.
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Badge label={item.temporalStatus} type={statusBadgeType(item.temporalType)} />
          <Badge label={`1ª: ${item.firstAuctionDate}`} type="neutral" />
          <Badge label={`2ª: ${item.secondAuctionDate}`} type="info" />
          {economics.isModeled && <Badge label="financeiro preliminar" type="warning" />}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
          <StoryMetric label="1ª praça" value={money(item.firstAuction)} note="observa, não decide" color={C.sky} />
          <StoryMetric label="2ª praça" value={money(item.secondAuction)} note="gatilho de investigação" color={item.color} />
          <StoryMetric label="Referência de venda" value={money(economics.saleBase)} note="saída a validar" color={C.teal} />
          <StoryMetric label="Score" value={`${item.score}/100`} note={`confiança ${item.confidence}/100`} color={C.amber} />
        </div>
        <div style={{ background: withAlpha(C.coral, "10"), border: `1px solid ${withAlpha(C.coral, alpha.border)}`, borderRadius: 12, padding: 12 }}>
          <div style={{ color: C.coral, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 7, textTransform: "uppercase" }}>P0 antes de qualquer lance</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
            {item.p0.map((label) => <Badge key={label} label={label} type="danger" />)}
          </div>
        </div>
        <CompetitorMap item={item} />
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        <FlowStep step="1" color={C.sky} title="Território antes da unidade" text="O bairro e o entorno entram primeiro: liquidez, renda, metragem vendável, vaga, tipologia e demanda de usuário final." />
        <FlowStep step="2" color={C.amber} title="1ª praça observa, não compra" text={`A ${money(item.firstAuction)}, o radar registra o sinal e evita gastar diligência pesada antes de existir margem.`} />
        <FlowStep step="3" color={item.color} title="2ª praça cria a pergunta" text={`A ${money(item.secondAuction)}, contra referência de ${money(economics.saleBase)}, o caso merece investigação. Ainda não é compra: é tese candidata.`} />
        <FlowStep step="4" color={C.coral} title="A diligência ainda manda" text="Ocupação, matrícula, débitos, forma de pagamento e comparável real decidem se a tese sobe, espera, simula ou morre cedo." />
        <div style={{ background: withAlpha(C.green, "10"), border: `1px solid ${withAlpha(C.green, alpha.border)}`, borderRadius: 12, color: C.text, fontSize: 13, fontWeight: 800, lineHeight: 1.5, padding: 14 }}>
          Patrick Jane: “{item.quote}”
        </div>
      </div>
    </div>
  );
}

function CaseDetailPackage({ item }) {
  return (
    <>
      <IconBasis item={item} />
      <CaseNarrative item={item} />
      <PropertySnapshot item={item} />
      <PropertyPhotoGallery item={item} />
      <CandidateScreeningNumbers item={item} />
      <ExitDemand item={item} />

      <div style={{ display: "grid", gap: 7 }}>
        <div style={{ color: C.muted, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>P0 / prova antes de convicção</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {item.p0.map((label) => <Badge key={label} label={label} type={item.color === C.coral ? "danger" : "warning"} />)}
        </div>
      </div>
      <P0Diligence item={item} />
      <FinancialOutcome item={item} />

      <a href={item.sourceUrl} target="_blank" rel="noreferrer" style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.07em", textDecoration: "none", textTransform: "uppercase" }}>
        Abrir fonte
      </a>
    </>
  );
}

function CaseStoryCard({ item, isOpen, onToggle }) {
  return (
    <article style={{ background: C.panel, borderBottom: `1px solid ${isOpen ? withAlpha(item.color, alpha.border) : C.border}`, borderLeft: `1px solid ${isOpen ? withAlpha(item.color, alpha.border) : C.border}`, borderRight: `1px solid ${isOpen ? withAlpha(item.color, alpha.border) : C.border}`, borderTop: `2px solid ${item.color}`, borderRadius: 14, display: "grid", gap: 12, gridColumn: isOpen ? "1 / -1" : "auto", padding: 15, position: "relative", overflow: "hidden" }}>
      <div style={{ background: `radial-gradient(circle at top right, ${withAlpha(item.color, alpha.glow)}, transparent 72%)`, height: 95, position: "absolute", right: 0, top: 0, width: 120 }} />
      <div style={{ position: "relative" }}>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-label={`${isOpen ? "Fechar" : "Abrir"} ${item.title}`}
          onClick={onToggle}
          style={{
            alignItems: "flex-start",
            background: "transparent",
            border: 0,
            cursor: "pointer",
            display: "flex",
            gap: 10,
            justifyContent: "space-between",
            padding: 0,
            textAlign: "left",
            width: "100%",
          }}
        >
          <div style={{ alignItems: "flex-start", display: "flex", gap: 12, minWidth: 0 }}>
            <ThesisIcon item={item} isOpen={isOpen} />
            <div>
            <div style={{ color: item.color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.09em", marginBottom: 6, textTransform: "uppercase" }}>{item.id} · {item.role}</div>
            <h3 style={{ color: C.text, fontSize: 16, lineHeight: 1.2, margin: 0 }}>{item.title}</h3>
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45, marginTop: 7 }}>
              {item.strategy} · score {item.score}/100 · confiança {item.confidence}/100
            </div>
            <div style={{ color: item.color, fontFamily: mono, fontSize: 8, fontWeight: 900, letterSpacing: "0.08em", marginTop: 7, textTransform: "uppercase" }}>
              {item.iconLabel}
            </div>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
            <Badge label={item.temporalStatus} type={statusBadgeType(item.temporalType)} />
            <Badge label={item.decision} type={item.color === C.coral ? "danger" : "info"} />
            <span style={{ color: item.color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase", whiteSpace: "nowrap" }}>
              {isOpen ? "Fechar" : "Abrir"}
            </span>
          </div>
        </button>
        <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: "10px 0 0" }}>{item.whyRadar}</p>
      </div>

      {isOpen && (
        <CaseDetailPackage item={item} />
      )}
    </article>
  );
}

function PerdizesCasePortfolio() {
  const [openCaseId, setOpenCaseId] = useState(null);

  return (
    <Section data-testid="perdizes-case-portfolio" eyebrow="Radar Perdizes" title="Sete histórias para mostrar que o método não depende de um único imóvel" color={C.purple}>
      <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.65, margin: 0 }}>
        Cada card nasce contraído para preservar foco. Abra um por vez para ver a ficha, números, P0, comentário do laboratório e fonte.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
        {REAL_ESTATE_DEMO_CASES.map((item) => (
          <CaseStoryCard
            key={item.id}
            item={item}
            isOpen={openCaseId === item.id}
            onToggle={() => setOpenCaseId((current) => (current === item.id ? null : item.id))}
          />
        ))}
      </div>
    </Section>
  );
}

function PortalStory({ thesis }) {
  const p0Text = thesis.p0.length ? thesis.p0.join(" ") : PORTAL_FALLBACK.p0.join(" ");

  return (
    <Section data-testid="portal-cantareira-story" eyebrow="Caso real guiado" title={`${cleanAssetTitle(thesis.title)}: a saída decide a entrada`} color={C.gold}>
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(360px, 0.95fr) minmax(0, 1.05fr)" }}>
        <div style={{ display: "grid", gap: 12 }}>
          <figure style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, margin: 0, overflow: "hidden" }}>
            <img src="/assets/demo/siteleiloes-portal-cantareira.png" alt="Fonte pública do Portal Cantareira" style={{ display: "block", height: 220, objectFit: "cover", objectPosition: "top", width: "100%" }} />
            <figcaption style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "10px 12px" }}>
              Evidência visual de origem pública. Os números operacionais abaixo vêm do feed oficial da tese e da análise interna do radar.
            </figcaption>
          </figure>
          <figure style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, margin: 0, overflow: "hidden" }}>
            <img src="/assets/demo/portal-cantareira-map.png" alt="Mapa com candidato e concorrentes da região" style={{ display: "block", height: 220, objectFit: "cover", width: "100%" }} />
            <figcaption style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "10px 12px" }}>
              O mapa responde à pergunta que importa na saída: contra quais imóveis este candidato competirá quando for vendido?
            </figcaption>
          </figure>
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <FlowStep step="1" color={C.sky} title="Entrou no radar, mas não virou compra" text={`A fonte pública mostra lance inicial de ${money(thesis.auctionPrice)}. Nesse preço, não há tese de compra: o número apenas aciona o radar para monitorar queda, edital e saída.`} />
          <FlowStep step="2" color={C.gold} title="A 2ª praça vira só um gatilho" text={`Não gastamos diligência ativa agora. O radar apenas deixa um alerta passivo: se uma 2ª praça ou nova rodada aparecer perto de ${money(thesis.radarEntryTarget)}, e abaixo do teto de ${money(thesis.maxPurchasePrice)}, a tese pode ser reaberta.`} />
          <FlowStep step="3" color={C.coral} title="P0 segura a mão" text={p0Text} />
          <FlowStep step="4" color={C.green} title="Conclusão: descartar agora" text={`Os concorrentes estão entre ${money(PORTAL_FALLBACK.competitorMin)} e ${money(PORTAL_FALLBACK.competitorMax)}. Com venda base de ${money(PORTAL_FALLBACK.baseSale)}, o custo final não paga o risco. A história boa aqui é o "não" rápido.`} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
        <KPICard label="Lance inicial" value={money(thesis.auctionPrice)} sub="preço do edital, não entrada" accent={C.sky} valueColor={C.sky} valueFontSize={20} />
        <KPICard label="Gatilho futuro" value={money(thesis.radarEntryTarget)} sub="alerta passivo, não tese ativa" accent={C.gold} valueColor={C.gold} valueFontSize={20} />
        <KPICard label="Teto de compra" value={money(thesis.maxPurchasePrice)} sub="limite disciplinado" accent={C.amber} valueColor={C.amber} valueFontSize={20} />
        <KPICard label="Venda base" value={money(PORTAL_FALLBACK.baseSale)} sub="ancorada nos concorrentes" accent={C.teal} valueColor={C.teal} valueFontSize={20} />
      </div>

      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, display: "grid", gap: 12, padding: 16 }}>
        <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Reconciliação dos números
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 10 }}>
          <EvidencePill label="Edital" value={money(thesis.auctionPrice)} note="Preço público observado. Nesse nível, não compramos." color={C.sky} />
          <EvidencePill label="Gatilho futuro" value={money(thesis.radarEntryTarget)} note="Não gera trabalho agora; apenas reabre análise se aparecer em 2ª praça ou nova rodada." color={C.gold} />
          <EvidencePill label="Teto Halley" value={money(thesis.maxPurchasePrice)} note="Limite máximo para não depender de venda irrealista." color={C.amber} />
          <EvidencePill label="Concorrentes" value={`${money(PORTAL_FALLBACK.competitorMin)}-${money(PORTAL_FALLBACK.competitorMax).replace("R$ ", "")}`} note="Faixa dos imóveis que disputam a saída." color={C.purple} />
          <EvidencePill label="Saída base" value={money(PORTAL_FALLBACK.baseSale)} note="Preço provável de revenda usado na conta disciplinada." color={C.teal} />
        </div>
        <div style={{ background: withAlpha(C.coral, "10"), border: `1px solid ${withAlpha(C.coral, alpha.border)}`, borderRadius: 10, color: C.text, fontSize: 12, fontWeight: 800, lineHeight: 1.55, padding: "10px 12px" }}>
          Decisão do radar: descartar agora. Não usar R$ 233k como venda base sem prova; não gastar diligência ativa enquanto a saída realista não paga o custo final. A 2ª praça fica apenas como gatilho automático de reavaliação.
        </div>
      </div>

      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, display: "grid", gap: 14, gridTemplateColumns: "minmax(0, 1fr) minmax(280px, 0.82fr)", padding: 16 }}>
        <div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 8, textTransform: "uppercase" }}>
            Comparação de capital
          </div>
          <ComparisonRow label="Lucro líquido na venda base" value={money(PORTAL_FALLBACK.baseProfitAfterTax)} color={PORTAL_FALLBACK.baseProfitAfterTax >= 0 ? C.green : C.coral} detail={`Com saída a ${money(PORTAL_FALLBACK.baseSale)}, depois de custos, comissão, impostos estimados, financiamento e liquidação da dívida.`} />
          <ComparisonRow label="Renda fixa no mesmo prazo" value={money(PORTAL_FALLBACK.fixedIncomeGain)} color={C.gold} detail="Benchmark simples para responder se o risco operacional está sendo pago." />
          <ComparisonRow label="Ponto de equilíbrio" value={money(PORTAL_FALLBACK.breakEven)} color={C.amber} detail="Preço mínimo estimado para não transformar desconto aparente em prejuízo líquido." />
        </div>
        <div style={{ background: withAlpha(C.green, "10"), border: `1px solid ${withAlpha(C.green, alpha.border)}`, borderRadius: 12, padding: 14 }}>
          <div style={{ color: C.green, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 8, textTransform: "uppercase" }}>
            O aprendizado do caso
          </div>
          <p style={{ color: C.text, fontSize: 14, fontWeight: 800, lineHeight: 1.35, margin: 0 }}>
            O melhor produto aqui é economizar tempo: descartar cedo e deixar só um alerta.
          </p>
          <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, margin: "8px 0 0" }}>
            O moat da app é acumular aprendizado proprietário: fontes que funcionam, P0 que bloqueiam, bairros que sustentam preço e simulações que evitam convicção cara. Nesse caso, o radar não manda perseguir a 2ª praça; ele registra a condição mínima para um eventual retorno.
          </p>
          <a href={thesis.sourceUrl} target="_blank" rel="noreferrer" style={{ color: C.gold, display: "inline-flex", fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.07em", marginTop: 12, textDecoration: "none", textTransform: "uppercase" }}>
            Abrir fonte do imóvel
          </a>
        </div>
      </div>
    </Section>
  );
}

function MethodBridge() {
  return (
    <Section eyebrow="Como isso vira produto" title="A jornada que o investidor precisa reconhecer" color={C.green}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 10 }}>
        {[
          ["Observar", "Mundo real, Selic, mercado, território e fontes públicas.", C.sky],
          ["Formular", "Transformar sinal em hipótese com entrada, saída e invalidação.", C.gold],
          ["Testar", "Histórico, simulação, paper e evidências antes do capital.", C.purple],
          ["Decidir", "Avançar, esperar, descartar ou pedir nova prova.", C.amber],
          ["Aprender", "Registrar o que fortalece, o que falha e como melhorar o próximo ciclo.", C.green],
        ].map(([title, text, color], index) => (
          <article key={title} style={{ background: C.panel, border: `1px solid ${C.border}`, borderTop: `2px solid ${color}`, borderRadius: 12, padding: 13, position: "relative", overflow: "hidden" }}>
            <div style={{ background: `radial-gradient(circle at top right, ${withAlpha(color, alpha.glow)}, transparent 70%)`, height: 70, position: "absolute", right: 0, top: 0, width: 70 }} />
            <div style={{ color, fontFamily: mono, fontSize: 10, fontWeight: 900, marginBottom: 7 }}>{String(index + 1).padStart(2, "0")}</div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 800, marginBottom: 6 }}>{title}</div>
            <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0 }}>{text}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}

export default function JornadaTese({ data }) {
  const guideCase = useMemo(() => {
    const main = REAL_ESTATE_DEMO_CASES[0];
    return {
      id: main.id,
      title: main.title,
      score: main.score,
      confidence: main.confidence,
      p0: main.p0,
    };
  }, []);
  const totalTheses = Number(data?.scientificSummary?.testedTheses) || 0;
  const approval = Number(data?.scientificSummary?.validatedPct) || 0;

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 18, minHeight: 640, padding: "24px 28px 40px" }}>
      <Hero thesis={guideCase} />
      <InvestorLens />
      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
        <KPICard label="Teses na memória" value={totalTheses ? totalTheses.toLocaleString("pt-BR") : "--"} sub="base para simular" accent={C.sky} valueColor={C.sky} />
        <KPICard label="Taxa histórica" value={approval ? pct(approval) : "--%"} sub="não substitui prova da tese" accent={C.teal} valueColor={C.teal} />
        <KPICard label="P0 do caso" value={String(guideCase.p0.length)} sub="bloqueiam decisão" accent={C.coral} valueColor={C.coral} />
        <KPICard label="Benchmark" value="RF" sub="capital compete com renda fixa" accent={C.gold} valueColor={C.gold} />
      </section>
      <RadarPermanent />
      <SourceRadar />
      <SimulationLoop />
      <PerdizesCasePortfolio />
      <MethodBridge />
    </main>
  );
}


