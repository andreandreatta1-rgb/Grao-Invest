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

function flagValue(...values) {
  for (const value of values) {
    if (value === undefined || value === null || value === "") continue;
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value !== 0;
    const text = searchText(value);
    if (["1", "true", "sim", "yes", "on", "validado", "esclarecido"].includes(text)) return true;
    if (["0", "false", "nao", "no", "off", "pendente"].includes(text)) return false;
  }
  return undefined;
}

function isAuctionLikeCandidate(row, candidate, analysis, sourceUrl) {
  const text = searchText([
    row?.asset,
    row?.operation,
    row?.hypothesis,
    row?.sourceUrl,
    row?.source_url,
    sourceUrl,
    candidate?.origin,
    candidate?.source,
    candidate?.strategy,
    candidate?.property_type,
    analysis?.structured_operation,
    analysis?.structuredOperation,
  ]);
  return includesAny(text, AUCTION_MARKERS) || includesAny(text, ["banco do brasil", "licitacao", "judicial", "extrajudicial"]);
}

function approvedPossessionPlanFor(row, candidate, analysis) {
  const planText = searchText([
    candidate?.legal_plan,
    candidate?.legalPlan,
    candidate?.eviction_plan,
    candidate?.evictionPlan,
    candidate?.possession_plan,
    candidate?.possessionPlan,
    analysis?.legal_plan,
    analysis?.legalPlan,
    analysis?.eviction_plan,
    analysis?.evictionPlan,
    analysis?.possession_plan,
    analysis?.possessionPlan,
    row?.legal_plan,
    row?.legalPlan,
    row?.eviction_plan,
    row?.evictionPlan,
  ]);
  return includesAny(planText, ["acordo de desocupacao", "desocupacao acordada", "imissao planejada", "plano juridico aprovado", "posse planejada"]);
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

const TARGET_NEIGHBORHOODS = [
  { key: "pinheiros", label: "Pinheiros", terms: ["pinheiros", "mourato coelho", "mateus grou", "padre carvalho"] },
  { key: "perdizes", label: "Perdizes", terms: ["perdizes", "turiassu", "turiaçu", "cardoso de almeida", "caiubi"] },
  { key: "itaim-bibi", label: "Itaim Bibi", terms: ["itaim bibi", "itaim"] },
  { key: "campo-belo", label: "Campo Belo", terms: ["campo belo", "joao de sousa dias", "vieira de morais"] },
  { key: "paraiso", label: "Paraiso", terms: ["paraiso", "abilio soares", "rafael de barros", "fausto ferraz"] },
];

const RADAR_SECTION_IDS = new Set(["visao-geral", "modelo", "garimpo", "candidatos"]);

function targetNeighborhoodForText(value) {
  const text = searchText(value);
  return TARGET_NEIGHBORHOODS.find((target) => target.terms.some((term) => text.includes(term))) || null;
}

function normalizedRadarSection(section) {
  const value = String(section || "").trim();
  return RADAR_SECTION_IDS.has(value) ? value : "";
}

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

function localDemandLabel(risk) {
  const value = String(risk || "").toLowerCase();
  if (value === "critico" || value === "critical") return "Demanda local critica";
  if (value === "alto" || value === "high") return "Demanda local alta";
  if (value === "medio" || value === "medium") return "Demanda local a validar";
  if (value === "baixo" || value === "low") return "Demanda local ok";
  return "";
}

function localDemandBadgeType(risk) {
  const value = String(risk || "").toLowerCase();
  if (value === "critico" || value === "critical") return "danger";
  if (value === "alto" || value === "high") return "warning";
  return "info";
}

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return "R$ --";
  return `R$ ${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

function wordsForComparison(value) {
  return searchText(value)
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

function cleanStreetCandidate(value) {
  return compactText(value)
    .replace(/\b\d+(?:[.,]\d+)?\s*m(?:2|²)?\b/gi, " ")
    .replace(/\b\d+\s*q\b/gi, " ")
    .replace(/\b(?:apto|apartamento|casa|vila|kitnet|studio|flat)\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function titleAddressFromText(source, city, neighborhood) {
  const segments = cleanAssetTitle(source)
    .split(/[\/|]/)
    .map((item) => compactText(item))
    .filter(Boolean);
  if (segments.length < 2) return "";

  const cityWords = wordsForComparison(city);
  const neighborhoodWords = wordsForComparison(neighborhood);
  return segments.slice(1).find((segment) => {
    const normalized = searchText(segment);
    if (!normalized) return false;
    if (cityWords.some((word) => normalized === word) || neighborhoodWords.some((word) => normalized === word)) return false;
    return /(?:\brua\b|\br\.\b|\bavenida\b|\bav\.\b|\balameda\b|\bcasa\b|\bapto\b|\bapartamento\b|,\s*\d+)/i.test(segment);
  }) || "";
}

function streetFromText(source, city, neighborhood) {
  const text = cleanAssetTitle(source);
  if (!text) return "";

  const prefixedStreet = text.match(/\b(Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Estrada|Rodovia|Largo|Praca|Praça)\s+([^,;|]+?)(?=\s+\d+(?:[.,]\d+)?\s*m(?:2|²)?\b|\s+\d+\s*q\b|$)/i);
  if (prefixedStreet) {
    const streetName = cleanStreetCandidate(prefixedStreet[2]);
    return streetName ? `${prefixedStreet[1].replace(/^R\.$/i, "Rua").replace(/^Av\.$/i, "Av.")} ${streetName}` : "";
  }

  const stopWords = new Set([
    "real",
    "target",
    "frazao",
    "itau",
    "leilao",
    "caixa",
    "apartamento",
    "apto",
    "casa",
    "vila",
    "kitnet",
    "studio",
    "flat",
    "predio",
    "condominio",
    ...wordsForComparison(city),
    ...wordsForComparison(neighborhood),
  ]);
  const cleaned = text
    .replace(/^REAL\s+TARGET\s*[-–—]\s*/i, "")
    .replace(/^TARGET\s*[-–—]\s*/i, "")
    .replace(/\b\d+(?:[.,]\d+)?\s*m(?:2|²)?\b/gi, " ")
    .replace(/\b\d+\s*q\b/gi, " ")
    .replace(/[-–—|]/g, " ");
  const inferred = cleaned
    .split(/\s+/)
    .filter((word) => {
      const normalized = wordsForComparison(word)[0] || "";
      return normalized && !stopWords.has(normalized) && !/^\d+$/.test(normalized);
    })
    .join(" ")
    .trim();

  return inferred.length >= 4 ? inferred : "";
}

function operationalCandidateTitle({ row, candidate, entry, saleBase, fallbackTitle, targetNeighborhood }) {
  const city = firstText(candidate.city, candidate.cidade, candidate.municipality, candidate.municipio, "Cidade a validar");
  const neighborhood = firstText(candidate.neighborhood, candidate.neighborhoods, candidate.bairro, candidate.district, targetNeighborhood?.label, "Bairro a validar");
  const addressText = firstText(candidate.street, candidate.street_name, candidate.streetName, candidate.rua, candidate.address, candidate.endereco);
  const titleText = firstText(row?.asset, row?.action, row?.name, candidate.title, fallbackTitle);
  const street = firstText(
    compactText(addressText),
    titleAddressFromText(titleText, city, neighborhood),
    streetFromText(titleText, city, neighborhood),
    "Rua a validar",
  );
  return `${city} / ${neighborhood} / ${street} / Entrada ${money(entry)} / Saida ${money(saleBase || row?.targetPrice || row?.currentPrice || entry)}`;
}

function numericIdentifier(value) {
  const text = String(value || "").trim();
  return /^\d+$/.test(text) ? text : "";
}

function candidateIdentifierNumber(row, index) {
  const explicit = numericIdentifier(firstText(
    row?.identifierNumber,
    row?.historicalIdentifier,
    row?.historical_identifier,
    row?.thesisNumber,
    row?.thesis_number,
    row?.candidateNumber,
    row?.candidate_number,
  ));
  if (explicit) return explicit;

  const rowId = numericIdentifier(row?.id);
  if (rowId) return rowId;

  const thesisMatches = String(row?.thesisId || row?.thesis_id || "").match(/\d+/g);
  if (thesisMatches?.length) return thesisMatches[thesisMatches.length - 1];

  return String(index + 1).padStart(2, "0");
}

function shortText(value, size = 48) {
  const text = compactText(value);
  if (text.length <= size) return text;
  return `${text.slice(0, size - 1).trim()}…`;
}

function formatDate(value) {
  let date = value ? new Date(value) : null;
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    date = new Date(year, month - 1, day);
  }
  if (!date || Number.isNaN(date.getTime())) return "entrada no radar";
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

function isOpenRealEstateRow(row) {
  if (row?.isOpen === false) return false;
  const status = String(`${row?.statusGroup || ""} ${row?.status || ""}`).toLowerCase();
  if (status.includes("hist") || status.includes("fechad") || status.includes("descart")) return false;
  return status.includes("go-live") || status.includes("abert") || status.includes("pendenc") || status.includes("analise") || status.includes("análise") || status.includes("observ") || status.includes("monitor") || row?.isOpen === true;
}

function canonicalRealEstateId(row) {
  const value = String(row?.thesisId || row?.id || "").trim();
  if (/^IM-[A-Z0-9-]+$/i.test(value)) return value.toUpperCase();
  return value.match(/^\d+$/)?.[0] || "";
}

function canonicalRealEstateRows(data) {
  const thesisRows = asArray(data?.thesisRows).filter(isRealEstateFront);
  const candidateRows = asArray(data?.realEstateCandidates).filter(isRealEstateFront);
  const seen = new Set();
  return [...candidateRows, ...thesisRows].filter((row) => {
    const candidateId = canonicalRealEstateId(row);
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
  const credentialFileHint = firstText(validation.credential_file_hint, validation.credentialFileHint);
  const userAction = firstText(validation.user_action, validation.userAction);
  if (status === "valid") return { status, reason, label: "Fonte validada", type: "success" };
  if (status === "expired" || status === "unavailable") return { status, reason, label: "Fonte indisponível", type: "danger" };
  if (status === "access_required") return { status, reason, label: "Acesso necessario", type: "warning", credentialFileHint, userAction };
  if (status === "ambiguous") return { status, reason, label: "Fonte manual", type: "warning" };
  return { status, reason, label: "Fonte a validar", type: "warning" };
}

function sourceUrlFor(row) {
  const candidate = candidateFor(row);
  return firstText(row?.sourceUrl, row?.source_url, candidate.source_url, candidate.sourceUrl, "#");
}

function saleComparablesForRow(row, analysis, candidate, valuationEvidence) {
  const entries = [
    ...asArray(row?.saleComparables),
    ...asArray(row?.sale_comparables),
    ...asArray(row?.comparables),
    ...asArray(analysis?.saleComparables),
    ...asArray(analysis?.sale_comparables),
    ...asArray(analysis?.comparables),
    ...asArray(candidate?.saleComparables),
    ...asArray(candidate?.sale_comparables),
    ...asArray(candidate?.comparables),
    ...asArray(valuationEvidence?.saleComparables),
    ...asArray(valuationEvidence?.sale_comparables),
    ...asArray(valuationEvidence?.comparables),
  ].filter((entry) => entry && typeof entry === "object");

  const seen = new Set();
  return entries.filter((entry) => {
    const key = [
      entry.source_url || entry.sourceUrl || entry.url || entry.href || "",
      entry.price || entry.asking_price || entry.askingPrice || entry.sale_price || entry.salePrice || entry.value || "",
      entry.source || entry.origin || "",
    ].join("|");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function isGenericSourceUrl(value) {
  const text = searchText(value);
  if (!text) return false;
  if (text.includes("leilao-de-imovel/") && !text.includes("/imovel/")) return true;
  if (text.includes("/leiloes/") && includesAny(text, TARGET_NEIGHBORHOODS.map((item) => item.key))) return true;
  return false;
}

function scenarioFor(analysis, key) {
  return analysis?.scenarios?.[key] || analysis?.scenario?.[key] || {};
}

function explicitOccupiedWithoutPlan(row, candidate, analysis) {
  const occupancyText = searchText([
    candidate.occupancy_status,
    candidate.occupancyStatus,
    candidate.ocupacao,
    analysis.occupancy_status,
    analysis.occupancyStatus,
    row?.occupancy_status,
    row?.occupancyStatus,
  ]);
  if (!occupancyText || occupancyText.includes("desocup")) return false;
  if (!occupancyText.includes("ocupad")) return false;

  const planText = searchText([
    candidate.legal_plan,
    candidate.legalPlan,
    candidate.eviction_plan,
    candidate.evictionPlan,
    analysis.legal_plan,
    analysis.legalPlan,
    analysis.eviction_plan,
    analysis.evictionPlan,
    row?.legal_plan,
    row?.legalPlan,
  ]);
  return !includesAny(planText, ["acordo de desocupacao", "desocupacao acordada", "imissao planejada", "plano juridico aprovado"]);
}

function legalOwnershipBlockersFor(row, candidate, analysis, sourceValidation) {
  const reading = analysis?.listing_reading || analysis?.listingReading || candidate?.listing_reading || candidate?.listingReading || {};
  const pendingItems = asArray(analysis?.pending_items || analysis?.pendingItems)
    .map((item) => compactText([item?.title, item?.action, item?.detail, item?.key]));
  const text = searchText([
    row?.asset,
    row?.title,
    row?.operation,
    row?.hypothesis,
    row?.learning_note,
    row?.sourceUrl,
    row?.source_url,
    candidate.title,
    candidate.strategy,
    candidate.property_type,
    candidate.propertyType,
    candidate.local_demand_notes,
    candidate.localDemandNotes,
    candidate.notes,
    candidate.source_validation_reason,
    candidate.sourceValidationReason,
    analysis?.structured_operation,
    analysis?.structuredOperation,
    analysis?.next_action,
    analysis?.nextAction,
    sourceValidation?.reason,
    reading.legal_ownership_blockers,
    reading.legalOwnershipBlockers,
    pendingItems,
  ]);

  const blockers = [];
  if (reading.rights_over_asset || reading.rightsOverAsset || /\bdireitos?\s+sobre\b|\bdireitos?\s+aquisitivos?\b|\bcessao\s+(?:de|do|dos)\s+direitos\b/.test(text)) {
    blockers.push("direitos sobre");
  }
  if (
    reading.fractional_interest
    || reading.fractionalInterest
    || /\b(parte\s+ideal|quota|quotas|cota|cotas|quinh[aã]o)\b|\bfracao\s+ideal(?:\s+de\s+[1-9]\d\s*%)?\b|\bfracao\s+(?:de|do|da|comercial)\b/.test(text)
  ) {
    blockers.push("fracao ideal");
  }
  if (reading.bare_ownership || reading.bareOwnership || /\bnua\s+propriedade\b/.test(text)) {
    blockers.push("nua propriedade");
  }
  return [...new Set(blockers)];
}

function officialDocumentationBlockersFor(row, candidate, analysis, sourceUrl) {
  if (!isAuctionLikeCandidate(row, candidate, analysis, sourceUrl)) return [];
  const pendingText = searchText(
    asArray(analysis?.pending_items || analysis?.pendingItems)
      .map((item) => compactText([item?.key, item?.title, item?.action, item?.detail]))
  );
  const hasEdital = flagValue(
    candidate?.has_edital,
    candidate?.hasEdital,
    analysis?.has_edital,
    analysis?.hasEdital,
    row?.has_edital,
    row?.hasEdital,
  );
  const hasRegistration = flagValue(
    candidate?.has_registration,
    candidate?.hasRegistration,
    analysis?.has_registration,
    analysis?.hasRegistration,
    row?.has_registration,
    row?.hasRegistration,
  );
  const blockers = [];
  if (hasEdital === false || pendingText.includes("buscar edital oficial") || /\bedital\b/.test(pendingText)) {
    blockers.push("sem edital oficial");
  }
  if (hasRegistration === false || pendingText.includes("matricula") || pendingText.includes("registration")) {
    blockers.push("sem matricula atualizada");
  }
  return [...new Set(blockers)];
}

function debtCostBlockersFor(row, candidate, analysis, sourceUrl) {
  if (!isAuctionLikeCandidate(row, candidate, analysis, sourceUrl)) return [];
  const reading = analysis?.listing_reading || analysis?.listingReading || candidate?.listing_reading || candidate?.listingReading || {};
  const pendingText = searchText(
    asArray(analysis?.pending_items || analysis?.pendingItems)
      .map((item) => compactText([item?.key, item?.title, item?.action, item?.detail]))
  );
  const condoKnown = flagValue(
    candidate?.condo_debt_known,
    candidate?.condoDebtKnown,
    analysis?.condo_debt_known,
    analysis?.condoDebtKnown,
    row?.condo_debt_known,
    row?.condoDebtKnown,
  );
  const iptuKnown = flagValue(
    candidate?.iptu_debt_known,
    candidate?.iptuDebtKnown,
    analysis?.iptu_debt_known,
    analysis?.iptuDebtKnown,
    row?.iptu_debt_known,
    row?.iptuDebtKnown,
  );
  const blockers = [];
  const hasAmbiguousDebtResponsibility = Boolean(
    reading.debt_responsibility_ambiguous
    || reading.debtResponsibilityAmbiguous
  ) || pendingText.includes("debt_responsibility_ambiguous")
    || pendingText.includes("responsabilidade por debitos")
    || pendingText.includes("debitos ambigua");
  if (hasAmbiguousDebtResponsibility) {
    blockers.push("responsabilidade por debitos ambigua");
  }
  if (
    condoKnown === false
    || iptuKnown === false
    || pendingText.includes("debt_total")
    || pendingText.includes("custo total de debitos")
  ) {
    blockers.push("debitos sem custo total");
  }
  return [...new Set(blockers)];
}

function possessionBlockersFor(row, candidate, analysis) {
  const reading = analysis?.listing_reading || analysis?.listingReading || candidate?.listing_reading || candidate?.listingReading || {};
  const pendingText = searchText(
    asArray(analysis?.pending_items || analysis?.pendingItems)
      .map((item) => compactText([item?.key, item?.title, item?.action, item?.detail]))
  );
  const text = searchText([
    row?.operation,
    row?.hypothesis,
    row?.learning_note,
    candidate?.strategy,
    candidate?.notes,
    candidate?.local_demand_notes,
    analysis?.next_action,
    analysis?.nextAction,
    pendingText,
  ]);
  const buyerEvictionRisk = Boolean(reading.buyer_responsible_for_eviction || reading.buyerResponsibleForEviction)
    || text.includes("desocupacao por conta")
    || text.includes("eviction_risk");
  if (buyerEvictionRisk && !approvedPossessionPlanFor(row, candidate, analysis)) {
    return ["desocupacao sem plano"];
  }
  return [];
}

function fiduciaryAuctionNullityBlockersFor(row, candidate, analysis, sourceValidation) {
  const reading = analysis?.listing_reading || analysis?.listingReading || candidate?.listing_reading || candidate?.listingReading || {};
  const pendingText = searchText(
    asArray(analysis?.pending_items || analysis?.pendingItems)
      .map((item) => compactText([item?.key, item?.title, item?.action, item?.detail]))
  );
  const text = searchText([
    row?.asset,
    row?.operation,
    row?.hypothesis,
    row?.learning_note,
    row?.sourceUrl,
    row?.source_url,
    candidate?.strategy,
    candidate?.notes,
    candidate?.source_validation_reason,
    candidate?.sourceValidationReason,
    analysis?.next_action,
    analysis?.nextAction,
    sourceValidation?.reason,
    pendingText,
  ]);
  const hasNullityAction = Boolean(
    reading.fiduciary_auction_nullity_action
    || reading.fiduciaryAuctionNullityAction
  ) || text.includes("fiduciary_auction_nullity_action")
    || (
      includesAny(text, [
        "acao declaratoria de nulidade",
        "acao anulatoria",
        "anulacao do leilao",
        "anulacao de leilao",
        "nulidade da consolidacao",
        "nulidade dos leiloes",
        "nulidade do leilao",
        "suspensao do leilao",
      ])
      && includesAny(text, [
        "consolidacao",
        "propriedade fiduciaria",
        "leilao extrajudicial",
        "leiloes extrajudiciais",
      ])
    );
  return hasNullityAction ? ["acao judicial ataca consolidacao/leilao"] : [];
}

function sourcePaymentBlockersFor(row, candidate, analysis, sourceValidation) {
  const reading = analysis?.listing_reading || analysis?.listingReading || candidate?.listing_reading || candidate?.listingReading || {};
  const pendingText = searchText(
    asArray(analysis?.pending_items || analysis?.pendingItems)
      .map((item) => compactText([item?.key, item?.title, item?.action, item?.detail]))
  );
  const text = searchText([
    row?.operation,
    row?.hypothesis,
    row?.sourceUrl,
    row?.source_url,
    candidate?.source_validation_reason,
    candidate?.sourceValidationReason,
    analysis?.next_action,
    analysis?.nextAction,
    sourceValidation?.reason,
    pendingText,
  ]);
  const hasSuspiciousPayment = Boolean(reading.suspicious_payment_instruction || reading.suspiciousPaymentInstruction)
    || text.includes("source_payment_risk")
    || (
      includesAny(text, ["pix", "boleto", "conta"])
      && includesAny(text, ["terceiro", "fora do edital", "diverge", "divergente", "nao oficial", "site falso"])
    );
  return hasSuspiciousPayment ? ["fonte/pagamento nao oficial"] : [];
}

function financingBlockersFor(row, candidate, analysis, sourceUrl) {
  if (!isAuctionLikeCandidate(row, candidate, analysis, sourceUrl)) return [];
  const pendingText = searchText(
    asArray(analysis?.pending_items || analysis?.pendingItems)
      .map((item) => compactText([item?.key, item?.title, item?.action, item?.detail]))
  );
  const text = searchText([
    row?.operation,
    row?.hypothesis,
    candidate?.strategy,
    candidate?.notes,
    analysis?.next_action,
    analysis?.nextAction,
    pendingText,
  ]);
  const financingValidated = flagValue(
    candidate?.financing_validated,
    candidate?.financingValidated,
    analysis?.financing_validated,
    analysis?.financingValidated,
    row?.financing_validated,
    row?.financingValidated,
  );
  const financingRequired = flagValue(
    candidate?.financing_required,
    candidate?.financingRequired,
    candidate?.depends_on_financing,
    candidate?.dependsOnFinancing,
    analysis?.financing_required,
    analysis?.financingRequired,
  );
  const hasFinancingDependency = financingRequired === true
    || text.includes("financing_dependency")
    || includesAny(text, ["fgts", "financiamento", "financiar", "entrada baixa", "minha casa minha vida", "mcmv"]);
  return hasFinancingDependency && financingValidated !== true ? ["financiamento/FGTS nao comprovado"] : [];
}

function qualificationForLiveCandidate({ analysis, candidate, ceiling, confidence, entry, localDemandRisk, p0Count, roiPct, row, score, sourceValidation, sourceUrl, valuationCount }) {
  const reasons = [];
  const watchReasons = [];
  const demandRisk = String(localDemandRisk || "").toLowerCase();
  const sourceStatus = String(sourceValidation?.status || "").toLowerCase();
  const conservative = scenarioFor(analysis, "conservative");
  const conservativeProfit = firstFiniteNumber(conservative.net_profit, conservative.netProfit);
  const hasConservativeLoss = Number.isFinite(conservativeProfit) && conservativeProfit < 0;
  const hasGenericSource = isGenericSourceUrl(sourceUrl);
  const hasOccupiedUnit = explicitOccupiedWithoutPlan(row, candidate, analysis);
  const isAboveCeiling = Boolean(ceiling && entry && entry > ceiling);
  const legalOwnershipBlockers = legalOwnershipBlockersFor(row, candidate, analysis, sourceValidation);
  const officialDocumentationBlockers = officialDocumentationBlockersFor(row, candidate, analysis, sourceUrl);
  const debtCostBlockers = debtCostBlockersFor(row, candidate, analysis, sourceUrl);
  const possessionBlockers = possessionBlockersFor(row, candidate, analysis);
  const fiduciaryNullityBlockers = fiduciaryAuctionNullityBlockersFor(row, candidate, analysis, sourceValidation);
  const sourcePaymentBlockers = sourcePaymentBlockersFor(row, candidate, analysis, sourceValidation);
  const financingBlockers = financingBlockersFor(row, candidate, analysis, sourceUrl);

  if (sourceStatus === "expired" || sourceStatus === "unavailable") reasons.push("fonte indisponivel");
  reasons.push(...legalOwnershipBlockers);
  reasons.push(...officialDocumentationBlockers);
  reasons.push(...debtCostBlockers);
  reasons.push(...possessionBlockers);
  reasons.push(...fiduciaryNullityBlockers);
  reasons.push(...sourcePaymentBlockers);
  reasons.push(...financingBlockers);
  if (hasGenericSource) reasons.push("fonte generica");
  if (hasOccupiedUnit) reasons.push("imovel ocupado");
  if (isAboveCeiling) reasons.push("entrada acima do Teto Halley");
  if (valuationCount <= 0) reasons.push("sem 3 comparaveis");
  if (demandRisk === "alto" || demandRisk === "high") reasons.push("demanda local alta");
  if (demandRisk === "critico" || demandRisk === "critical") reasons.push("demanda local critica");
  if (hasConservativeLoss && score < 66) reasons.push("cenario conservador negativo");

  if (!reasons.length && sourceStatus && sourceStatus !== "valid") watchReasons.push("fonte manual");
  if (!reasons.length && valuationCount > 0 && valuationCount < 3) watchReasons.push("menos de 3 comparaveis");
  if (!reasons.length && p0Count > 0) watchReasons.push(`${p0Count} P0 aberto${p0Count > 1 ? "s" : ""}`);
  if (!reasons.length && confidence < 45) watchReasons.push("confianca baixa");
  if (!reasons.length && roiPct > 0 && roiPct < 15) watchReasons.push("margem base estreita");

  const canAdvance = !reasons.length
    && sourceStatus === "valid"
    && valuationCount >= 3
    && p0Count === 0
    && confidence >= 45
    && roiPct >= 15
    && !hasConservativeLoss;

  if (reasons.length) {
    return {
      key: "blocked",
      label: "Bloqueado por prova",
      shortLabel: "Bloqueado",
      type: "danger",
      color: C.coral,
      reasons,
    };
  }

  if (canAdvance) {
    return {
      key: "advance",
      label: "Avancar agora",
      shortLabel: "Avancar",
      type: "success",
      color: C.green,
      reasons: ["fonte, teto, saida e P0 dentro da regra"],
    };
  }

  return {
    key: "watchlist",
    label: "Watchlist",
    shortLabel: "Watchlist",
    type: "warning",
    color: C.gold,
    reasons: watchReasons.length ? watchReasons : ["prova incompleta para proposta"],
  };
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

function inferredSourcingProfile({ analysis, candidate, p0Count, renovationCosts, roiPct, row, saleBase, sourceValidation, sourceUrl, strategy, valuationCount }) {
  const signals = [];
  const gaps = [];
  let score = 0;
  const text = searchText([
    row?.asset,
    row?.operation,
    row?.hypothesis,
    sourceUrl,
    candidate?.origin,
    candidate?.strategy,
    candidate?.notes,
    analysis?.summary,
    analysis?.next_action,
    analysis?.nextAction,
  ]);

  function addSignal(label, points) {
    if (signals.includes(label)) return;
    signals.push(label);
    score += points;
  }

  function addGap(label) {
    if (!gaps.includes(label)) gaps.push(label);
  }

  if (String(sourceValidation?.status || "").toLowerCase() === "valid") {
    addSignal("fonte oficial individual", 15);
  } else {
    addGap("fonte oficial individual");
  }

  if (includesAny(text, ["cauda longa", "leiloeiro regional", "regional oficial", "pouca concorrencia"])) {
    addSignal("canal pouco concorrido", 10);
  }

  if (valuationCount >= 3) {
    addSignal("desconto validado por comparaveis", 20);
  } else {
    addGap("comparaveis de saida");
  }

  if (saleBase > 0 || roiPct > 0 || includesAny(text, ["revenda", "vender", "saida", "alugar", "locacao", "plano b"])) {
    addSignal("saida clara", 15);
  } else {
    addGap("plano de saida");
  }

  if (strategy || isAuctionLikeCandidate(row, candidate, analysis, sourceUrl) || includesAny(text, ["compra direta", "venda direta"])) {
    addSignal("modalidade classificada", 10);
  } else {
    addGap("modalidade");
  }

  if (renovationCosts > 0 && includesAny(text, ["reforma", "house flipping", "retrofit", " hf"])) {
    addSignal("reforma precificavel", 15);
  }

  if (!score) return { score: 0, tier: "a_calcular", signals, gaps };

  if (p0Count > 0) {
    return {
      score: Math.min(score, 45),
      tier: "bloqueado_por_p0",
      signals,
      gaps,
      recommendation: "Resolver P0 antes de usar como padrao positivo de busca.",
    };
  }

  return {
    score: Math.min(score, 100),
    tier: score >= 80 ? "garimpo_qualificado" : score >= 60 ? "garimpo_em_prova" : "baixo_prioridade",
    signals,
    gaps,
  };
}

function liveStoryFromRow(row, index) {
  const analysis = analysisFor(row);
  const candidate = candidateFor(row);
  const valuationEvidence = analysis.valuation_evidence || analysis.valuationEvidence || candidate.valuation_evidence || candidate.valuationEvidence || {};
  const assetFirstDiligence = analysis.asset_first_diligence || analysis.assetFirstDiligence || candidate.asset_first_diligence || candidate.assetFirstDiligence || {};
  const localDemandEvidence = analysis.local_demand_evidence || analysis.localDemandEvidence || candidate.local_demand_evidence || candidate.localDemandEvidence || {};
  const localDemandRisk = firstText(localDemandEvidence.risk_level, localDemandEvidence.riskLevel, candidate.local_demand_risk, candidate.localDemandRisk);
  const localDemandStatus = firstText(localDemandEvidence.status_label, localDemandEvidence.statusLabel, localDemandLabel(localDemandRisk));
  const localDemandBadge = localDemandLabel(localDemandRisk);
  const commercialTerms = analysis.commercial_terms || analysis.commercialTerms || candidate.commercial_terms || candidate.commercialTerms || {};
  const rawSourcing = analysis.sourcing || analysis.sourcing_profile || analysis.sourcingProfile || candidate.sourcing || candidate.sourcing_profile || candidate.sourcingProfile || {};
  const rawSourcingScore = Math.round(firstNumber(rawSourcing.score, rawSourcing.sourcing_score, rawSourcing.sourcingScore));
  const score = Math.round(firstNumber(analysis.score, row?.score, 58));
  const confidence = Math.round(firstNumber(analysis.confidence, row?.confidence, 42));
  const p0Items = p0ItemsFor(row);
  const p0Count = p0Items.filter((item) => String(item?.priority || "").toUpperCase() === "P0").length;
  const isOpen = isOpenRealEstateRow(row);
  const statusLabel = firstText(row?.statusGroup, row?.status, isOpen ? "em análise" : "encerrado");
  const decision = isOpen
    ? firstText(analysis.suggested_status, analysis.suggestedStatus, analysis.next_action, analysis.nextAction, row?.outcome, row?.direction, "Investigar")
    : firstText(row?.outcome, row?.exitRule, row?.status, analysis.suggested_status, analysis.suggestedStatus, "Encerrado");
  const entry = firstNumber(row?.entryPrice, row?.currentPrice, analysis.ask_price, analysis.entry_price, candidate.asking_price, candidate.askingPrice, candidate.price, candidate.ask_price);
  const ceiling = firstNumber(analysis.max_purchase_price, analysis.maxPurchasePrice, row?.stopPrice, entry);
  const saleBase = firstNumber(
    analysis.scenarios?.base?.sale_price,
    analysis.scenarios?.base?.salePrice,
    analysis.target_sale_price,
    analysis.targetSalePrice,
    row?.targetPrice,
    row?.currentPrice,
  );
  const renovationCosts = firstNumber(analysis.renovation_budget, analysis.renovationBudget, candidate.renovation_budget, candidate.renovationBudget, candidate.reform_budget, Math.round(saleBase * 0.06));
  const acquisitionCosts = firstNumber(analysis.acquisition_costs, analysis.acquisitionCosts, candidate.acquisition_costs, candidate.acquisitionCosts, candidate.transaction_costs, candidate.transactionCosts, analysis.transaction_costs, Math.round(entry * 0.08));
  const carryingMonths = firstNumber(candidate.carrying_months, candidate.carryingMonths, analysis.carrying_months, analysis.carryingMonths);
  const monthlyCarryingCost = firstNumber(candidate.monthly_carrying_cost, candidate.monthlyCarryingCost, analysis.monthly_carrying_cost, analysis.monthlyCarryingCost);
  const carryingCosts = firstNumber(analysis.carrying_costs, analysis.carryingCosts, candidate.carrying_costs, candidate.carryingCosts, carryingMonths && monthlyCarryingCost ? carryingMonths * monthlyCarryingCost : 0, Math.round(entry * 0.04));
  const sellingPct = firstNumber(candidate.selling_commission_pct, candidate.sellingCommissionPct, analysis.selling_commission_pct, analysis.sellingCommissionPct, 6);
  const sellingCosts = firstNumber(analysis.selling_costs, analysis.sellingCosts, candidate.selling_costs, candidate.sellingCosts, Math.round(saleBase * sellingPct / 100));
  const hasAuctioneerFee = [
    analysis.auctioneer_fee,
    analysis.auctioneerFee,
    candidate.auctioneer_fee,
    candidate.auctioneerFee,
  ].some((value) => Number.isFinite(Number(value)));
  const hasExplicitAcquisitionCosts = [
    analysis.acquisition_costs,
    analysis.acquisitionCosts,
    candidate.acquisition_costs,
    candidate.acquisitionCosts,
    candidate.transaction_costs,
    candidate.transactionCosts,
    analysis.transaction_costs,
  ].some((value) => Number.isFinite(Number(value)));
  const auctioneerFee = hasAuctioneerFee
    ? firstFiniteNumber(analysis.auctioneer_fee, analysis.auctioneerFee, candidate.auctioneer_fee, candidate.auctioneerFee)
    : !hasExplicitAcquisitionCosts && strategyFor(row).includes("Leilão") ? Math.round(entry * 0.05) : 0;
  const totalCost = entry + auctioneerFee + acquisitionCosts + renovationCosts + carryingCosts + sellingCosts;
  const netProfit = firstFiniteNumber(analysis.scenarios?.base?.net_profit, analysis.scenarios?.base?.netProfit, saleBase - totalCost);
  const roiPct = firstFiniteNumber(analysis.scenarios?.base?.roi_pct, analysis.scenarios?.base?.roiPct, analysis.target_roi_pct, row?.expectedPct);
  const saleComparables = saleComparablesForRow(row, analysis, candidate, valuationEvidence);
  const valuationCount = firstNumber(valuationEvidence.sale_comparables_count, valuationEvidence.saleComparablesCount, candidate.sale_comparables_count, candidate.saleComparablesCount, saleComparables.length);
  const saleProofStatus = localDemandRisk === "critico" || localDemandRisk === "critical"
    ? "bloqueada por demanda local"
    : valuationCount > 0
      ? `${valuationCount} comparável${valuationCount > 1 ? "is" : ""} de anúncio`
      : "parcialmente comprovada";
  const saleNextEvidence = firstText(localDemandEvidence.required_action, localDemandEvidence.requiredAction)
    || (valuationCount >= 3
      ? "venda recente ou proposta firme"
      : `buscar ${Math.max(0, 3 - valuationCount)} comparável${3 - valuationCount === 1 ? "" : "is"} adicional${3 - valuationCount === 1 ? "" : "is"}`);
  const baseColor = colorForStory(score, decision);
  const title = cleanAssetTitle(firstText(row?.asset, row?.action, row?.name, `Candidato imobiliário ${index + 1}`));
  const nextAction = firstText(analysis.next_action, analysis.nextAction, row?.exitRule, row?.invalidation, "Diligência aberta");
  const strategy = strategyFor(row);
  const strategyIcon = iconForStrategy(strategy);
  const identifier = String(row?.thesisId || row?.id || `IM-ABERTO-${index + 1}`);
  const sourceValidation = sourceValidationFor(row);
  const sourceUrl = sourceUrlFor(row);
  const qualification = isOpen
    ? qualificationForLiveCandidate({
      analysis,
      candidate,
      ceiling,
      confidence,
      entry,
      localDemandRisk,
      p0Count,
      roiPct,
      row,
      score,
      sourceValidation,
      sourceUrl,
      valuationCount,
    })
    : null;
  const color = qualification?.color || baseColor;
  const targetNeighborhood = targetNeighborhoodForText([
    candidate.neighborhood,
    candidate.neighborhoods,
    candidate.district,
    candidate.address,
    candidate.notes,
    row?.asset,
    row?.action,
    row?.operation,
    row?.structure,
    row?.hypothesis,
    row?.sourceUrl,
    row?.source_url,
  ].map(compactText).join(" "));
  const displayTitle = operationalCandidateTitle({ row, candidate, entry, saleBase, fallbackTitle: title, targetNeighborhood });
  const sourcing = rawSourcingScore > 0
    ? rawSourcing
    : inferredSourcingProfile({
      analysis,
      candidate,
      p0Count,
      renovationCosts,
      roiPct,
      row,
      saleBase,
      sourceValidation,
      sourceUrl,
      strategy,
      valuationCount,
    });
  const sourcingScore = Math.round(firstNumber(sourcing.score, sourcing.sourcing_score, sourcing.sourcingScore));
  const sourcingTier = firstText(sourcing.tier, sourcing.status);
  const sourcingSignals = asArray(sourcing.signals || sourcing.positive_signals || sourcing.positiveSignals).map(compactText).filter(Boolean);
  const sourcingGaps = asArray(sourcing.gaps || sourcing.negative_signals || sourcing.negativeSignals).map(compactText).filter(Boolean);
  const sourcingLabel = sourcingTier === "bloqueado_por_p0" ? "Garimpo bloqueado" : "Garimpo";

  return {
    id: identifier.startsWith("#") ? identifier : `#${identifier}`,
    title,
    displayTitle,
    identifierNumber: candidateIdentifierNumber(row, index),
    neighborhood: firstText(candidate.neighborhood, candidate.neighborhoods, targetNeighborhood?.label),
    targetNeighborhood: targetNeighborhood?.label || "",
    targetNeighborhoodKey: targetNeighborhood?.key || "",
    role: isOpen ? `Caso real aberto · ${statusLabel}` : `Caso real encerrado · ${firstText(row?.outcome, row?.status, statusLabel)}`,
    strategy,
    propertyType: firstText(candidate.property_type, candidate.propertyType, row?.propertyType, row?.property_type),
    sourceUrl,
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
    purchasePrice: entry,
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
    valuationEvidence,
    localDemandEvidence,
    localDemandRisk,
    localDemandStatus,
    localDemandBadge,
    localDemandBadgeType: localDemandBadgeType(localDemandRisk),
    commercialTerms,
    assetFirstDiligence,
    sourcing,
    sourcingScore,
    sourcingTier,
    sourcingSignals,
    sourcingGaps,
    saleProofStatus,
    saleNextEvidence,
    saleCaveat: firstText(localDemandEvidence.caveat, valuationEvidence.caveat),
    saleComparables,
    saleComparablesCount: valuationCount,
    score,
    confidence,
    color,
    icon: strategyIcon.icon,
    iconLabel: strategyIcon.label,
    iconBasis: `${strategyIcon.basis} Importado dos casos imobiliários canônicos da app.`,
    decision: shortText(qualification?.label || decision, 30),
    decisionTier: qualification?.key || (isOpen ? "watchlist" : "closed"),
    decisionReasons: qualification?.reasons || [],
    decisionType: qualification?.type || (isOpen ? "warning" : "neutral"),
    whyRadar: [
      qualification ? `${qualification.label}: ${qualification.reasons.join("; ")}.` : "",
      sourcingScore > 0 ? `${sourcingLabel} ${sourcingScore}/100${sourcingSignals.length ? `: ${sourcingSignals.slice(0, 3).join(", ")}.` : "."}` : "",
      firstText(row?.hypothesis, analysis.summary, row?.operation, "Caso real no radar imobiliário aguardando leitura de evidência."),
    ].filter(Boolean).join(" "),
    p0: p0Items.map((item) => compactText(item?.title || item?.action)).filter(Boolean),
    p0Actions: p0Items.map((item) => ({
      title: compactText(item?.title || item?.key || "Diligência"),
      action: compactText(item?.action || item?.detail || nextAction),
      validationRoute: asArray(item?.validation_route || item?.validationRoute).map(compactText).filter(Boolean),
      validationExitCriteria: compactText(item?.validation_exit_criteria || item?.validationExitCriteria),
      requiresUserAccess: Boolean(item?.requires_user_access || item?.requiresUserAccess),
    })),
    quote: firstText(row?.janeMessage, analysis.jane_message, row?.learning, isOpen ? "Ainda não é compra. É candidato vivo enquanto a prova melhora a confiança." : "O descarte também é produto: ele ensina preço teto, P0 e limite de risco."),
    firstPriceLabel: "Preço entrada",
    firstPriceNote: "preço observado",
    secondPriceLabel: "Teto Halley",
    secondPriceNote: "limite disciplinado",
    salePriceLabel: "Saída base",
    salePriceNote: valuationCount > 0 ? "comparável anunciado" : "venda a validar",
    purchaseCostLabel: "Preço do lote",
    firstStepTitle: "Entrou no radar",
    firstStepText: `A ${money(entry)}, o candidato entrou porque ${firstText(row?.hypothesis, "há assimetria inicial para testar")}.`,
    secondStepTitle: "Teto e saída criam a pergunta",
    secondStepText: `O teto disciplinado está em ${money(ceiling || entry)} e a saída base em ${money(saleBase)}. A decisão agora depende das provas abertas.`,
    isLiveCandidate: isOpen,
    isRealCandidate: true,
    canDiscard: Boolean(row?.canDiscard || row?.canDiscardRealEstateCandidate || candidate.canDiscard || candidate.can_discard),
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
  if (item?.decisionTier === "advance") return "avancar";
  if (item?.decisionTier === "watchlist") return "watchlist";
  if (item?.decisionTier === "blocked") return "bloqueado";
  const decision = String(item.decision || "").toLowerCase();
  if (decision.includes("descartar") || decision.includes("não avançar") || decision.includes("recusar") || decision.includes("bloquear")) return "bloqueado";
  if (decision.includes("calibrar")) return "aprendizado";
  if (decision.includes("aguardar") || decision.includes("monitorar")) return "monitorar";
  return "investigar";
}

function buildRadarStats(items) {
  const liveItems = items.filter((item) => item.isLiveCandidate);
  const closedItems = items.filter((item) => item.isRealCandidate && !item.isLiveCandidate);
  const buckets = liveItems.reduce(
    (acc, item) => {
      acc[decisionBucket(item)] += 1;
      if (String(item.temporalStatus || "").toLowerCase().includes("futura")) acc.futureSecondRound += 1;
      return acc;
    },
    { aprendizado: 0, avancar: 0, bloqueado: 0, futureSecondRound: 0, investigar: 0, monitorar: 0, watchlist: 0 },
  );

  return {
    ...buckets,
    closedCount: closedItems.length,
    liveCount: liveItems.length,
    realCount: items.filter((item) => item.isRealCandidate).length,
    total: items.length,
    p0Count: liveItems.reduce((sum, item) => sum + (item.p0?.length || 0), 0),
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
          <KPICard label="Fechados/aprendizados" value={stats.closedCount} sub="fora da fila ativa" accent={C.teal} valueColor={C.teal} valueFontSize={22} />
          <KPICard label="P0 abertos" value={stats.p0Count} sub="provas antes de decisão" accent={C.coral} valueColor={C.coral} valueFontSize={22} />
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
  const pendingCount = stats.watchlist + stats.investigar + stats.monitorar;

  return (
    <section
      aria-label="Resumo de decisão do radar"
      style={{
        display: "grid",
        gap: 10,
        gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
      }}
    >
      <RadarSignalCard label="Avancar" title={pluralizeCase(stats.avancar, "candidato pronto", "candidatos prontos")} text="So entra aqui quando fonte, teto, saida, P0 e cenario conservador passam juntos." color={C.green} />
      <RadarSignalCard label="Watchlist" title={pluralizeCase(pendingCount, "candidato com prova pendente", "candidatos com prova pendente")} text="Promissor o suficiente para vigiar, mas ainda sem qualidade para defender proposta." color={C.gold} />
      <RadarSignalCard label="Bloquear" title={pluralizeCase(stats.bloqueado, "caso travado por prova", "casos travados por prova")} text="Fonte generica, ocupacao, teto estourado, demanda fraca ou comparaveis insuficientes derrubam o candidato." color={C.coral} />
      <RadarSignalCard label="Aprender" title={pluralizeCase(stats.closedCount, "caso para calibracao", "casos para calibracao")} text="Historico tambem e ativo: ensina preco teto, custo total e regra de descarte." color={C.sky} />
    </section>
  );
}

function sourceTierLabel(value) {
  const text = compactText(value).replace(/_/g, " ");
  if (!text) return "fonte oficial";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function auctioneerTierBadgeType(value) {
  const tier = compactText(value).toLowerCase();
  if (tier === "cauda_longa") return "purple";
  if (tier === "estabelecido") return "open";
  if (tier === "validar") return "warning";
  return "neutral";
}

function auctioneerOutreachBadge(contact) {
  const status = compactText(contact?.outreachStatus).toLowerCase();
  if (status === "respondido_sem_imoveis") return { label: "Sem imóveis", type: "warning" };
  if (status.startsWith("respondido")) return { label: "Respondido", type: "info" };
  if (status === "enviado") return { label: "E-mail enviado", type: "success" };
  return null;
}

function SignalPill({ children, color = C.sky }) {
  return (
    <span
      style={{
        background: withAlpha(color, "12"),
        border: `1px solid ${withAlpha(color, alpha.border)}`,
        borderRadius: 999,
        color,
        display: "inline-flex",
        fontSize: 10,
        fontWeight: 800,
        lineHeight: 1.35,
        padding: "5px 8px",
      }}
    >
      {children}
    </span>
  );
}

function RadarAuctioneerSourcing({ sourcing }) {
  const directories = asArray(sourcing?.officialDirectories);
  const contacts = asArray(sourcing?.officialContacts);
  const playbook = asArray(sourcing?.outreachPlaybook);
  const lowCompetitionSignals = asArray(sourcing?.scoringModel?.lowCompetitionSignals);
  const qualitySignals = asArray(sourcing?.scoringModel?.qualitySignals);
  const summary = sourcing?.summary ?? {};
  const scopeLabel = asArray(summary.scopeCities).join(" / ");
  const outreachSentCount = summary.outreachSentCount || contacts.filter((contact) => contact.outreachSentAt).length;
  const outreachResponseCount = summary.outreachResponseCount || contacts.filter((contact) => contact.responseReceivedAt).length;
  const outreachPendingResponseCount = summary.outreachPendingResponseCount ?? contacts.filter((contact) => contact.outreachStatus === "enviado").length;
  const outreachNoRealEstateCount = summary.outreachNoRealEstateCount || contacts.filter((contact) => contact.outreachStatus === "respondido_sem_imoveis").length;
  const hasSourcingData = directories.length > 0 || contacts.length > 0 || playbook.length > 0;

  return (
    <section
      data-testid="radar-imobiliario-garimpo"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        display: "grid",
        gap: 16,
        padding: 18,
      }}
    >
      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Radar de leiloeiros · Garimpo estruturado
        </div>
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
          <div>
            <h2 style={{ color: C.text, fontSize: 20, lineHeight: 1.15, margin: 0 }}>
              {hasSourcingData ? "Base propria de leiloeiros oficiais" : "Aguardando diretorios oficiais"}
            </h2>
            <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.65, margin: "8px 0 0" }}>
              {summary.actionability || "Listas oficiais das Juntas Comerciais viram fonte de contato para encontrar leiloeiros regulares, regionais e menos concorridos antes de escolher lotes."}
            </p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: 8 }}>
            <KPICard label="Diretorios" value={summary.officialDirectoryCount || directories.length} sub="fontes oficiais" accent={C.sky} valueColor={C.sky} valueFontSize={20} />
            <KPICard label="Contatos" value={summary.officialContactCount || contacts.length} sub={scopeLabel || "leiloeiros"} accent={C.gold} valueColor={C.gold} valueFontSize={20} />
            <KPICard label="Cauda longa" value={summary.longTailDirectoryCount || directories.filter((item) => item.visibilityTier === "cauda_longa").length} sub="menos obvios" accent={C.purple} valueColor={C.purple} valueFontSize={20} />
            <KPICard label="Com contato" value={summary.contactSourceCount || directories.filter((item) => item.contactPath).length} sub="para mailing" accent={C.green} valueColor={C.green} valueFontSize={20} />
            <KPICard label="Enviados" value={outreachSentCount} sub="primeiro contato" accent={C.green} valueColor={C.green} valueFontSize={20} />
            <KPICard label="Respostas" value={outreachResponseCount} sub={outreachNoRealEstateCount ? `${outreachNoRealEstateCount} sem imóveis` : "retornos"} accent={C.sky} valueColor={C.sky} valueFontSize={20} />
            <KPICard label="Pendentes" value={outreachPendingResponseCount} sub={summary.nextFollowUpAt ? `follow-up ${formatDate(summary.nextFollowUpAt)}` : "sem data"} accent={C.amber} valueColor={C.amber} valueFontSize={20} />
          </div>
        </div>
      </div>

      {!hasSourcingData && (
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, color: C.muted, fontSize: 12, fontWeight: 800, lineHeight: 1.55, padding: 14 }}>
          Este radar fica visivel mesmo quando o feed ainda nao carregou. Quando a API responder, aparecem as Juntas Comerciais, fontes oficiais, roteiro de contato e sinais de baixa concorrencia.
        </div>
      )}

      {contacts.length > 0 && (
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, display: "grid", gap: 12, padding: 14 }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
            <div>
              <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 5, textTransform: "uppercase" }}>
                Leiloeiros SP/Campinas
              </div>
              <div style={{ color: C.text, fontSize: 14, fontWeight: 900 }}>
                {contacts.length} contatos oficiais classificados por concorrencia
              </div>
            </div>
            {scopeLabel && <Badge label={scopeLabel} type="info" />}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 10 }}>
            {contacts.map((contact) => {
              const phones = asArray(contact.phones).join(" | ");
              const outreachBadge = auctioneerOutreachBadge(contact);
              return (
                <article
                  key={contact.id || `${contact.registration}-${contact.name}`}
                  style={{
                    background: C.card,
                    border: `1px solid ${C.border}`,
                    borderTop: `2px solid ${contact.competitionTier === "cauda_longa" ? C.purple : contact.competitionTier === "validar" ? C.amber : C.teal}`,
                    borderRadius: 12,
                    display: "grid",
                    gap: 7,
                    padding: 12,
                  }}
                >
                  <div style={{ display: "flex", gap: 7, alignItems: "center", flexWrap: "wrap" }}>
                    <Badge label={sourceTierLabel(contact.competitionTier)} type={auctioneerTierBadgeType(contact.competitionTier)} />
                    <Badge label={contact.city || "cidade"} type="info" />
                    {outreachBadge && <Badge label={outreachBadge.label} type={outreachBadge.type} />}
                  </div>
                  <div style={{ color: C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.25 }}>{contact.name}</div>
                  <div style={{ color: C.muted, fontFamily: mono, fontSize: 10, lineHeight: 1.45 }}>
                    Matricula {contact.registration || "--"}{contact.neighborhood ? ` - ${contact.neighborhood}` : ""}
                  </div>
                  {(contact.email || phones) && (
                    <div style={{ color: C.text, fontSize: 11, lineHeight: 1.5 }}>
                      {contact.email && <div>{contact.email}</div>}
                      {phones && <div>{phones}</div>}
                    </div>
                  )}
                  {contact.competitionReason && (
                    <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.5, margin: 0 }}>{contact.competitionReason}</p>
                  )}
                  {contact.contactStrategy && (
                    <p style={{ color: C.green, fontSize: 11, fontWeight: 800, lineHeight: 1.45, margin: 0 }}>{contact.contactStrategy}</p>
                  )}
                  {contact.outreachStatus && (
                    <p style={{ color: C.gold, fontSize: 11, fontWeight: 800, lineHeight: 1.45, margin: 0 }}>
                      Contato: {sourceTierLabel(contact.outreachStatus)}
                      {contact.outreachSentAt ? ` em ${formatDate(contact.outreachSentAt)}` : ""}
                      {contact.responseReceivedAt ? ` - resposta ${formatDate(contact.responseReceivedAt)}` : ""}
                      {contact.nextFollowUpAt ? ` - follow-up ${formatDate(contact.nextFollowUpAt)}` : ""}
                    </p>
                  )}
                  {contact.responseSummary && (
                    <p style={{ color: C.coral, fontSize: 11, fontWeight: 800, lineHeight: 1.45, margin: 0 }}>{contact.responseSummary}</p>
                  )}
                </article>
              );
            })}
          </div>
        </div>
      )}

      {directories.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 10 }}>
          {directories.slice(0, 6).map((directory) => (
            <article
              key={directory.id || `${directory.uf}-${directory.sourceName}`}
              style={{
                background: C.panel,
                border: `1px solid ${C.border}`,
                borderTop: `2px solid ${directory.visibilityTier === "cauda_longa" ? C.purple : C.sky}`,
                borderRadius: 12,
                display: "grid",
                gap: 8,
                padding: 13,
              }}
            >
              <div style={{ display: "flex", gap: 7, alignItems: "center", flexWrap: "wrap" }}>
                <Badge label={directory.uf || "UF"} type="info" />
                <Badge label={sourceTierLabel(directory.visibilityTier)} type={directory.visibilityTier === "cauda_longa" ? "purple" : "open"} />
              </div>
              <div style={{ color: C.text, fontSize: 14, fontWeight: 900, lineHeight: 1.25 }}>{directory.sourceName}</div>
              <p style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, margin: 0 }}>{directory.contactPath}</p>
              <p style={{ color: C.text, fontSize: 11, lineHeight: 1.55, margin: 0 }}>{directory.contactStrategy}</p>
              {directory.qualityFilter?.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {directory.qualityFilter.slice(0, 3).map((item) => (
                    <SignalPill key={item} color={C.green}>{item}</SignalPill>
                  ))}
                </div>
              )}
              {directory.sourceUrl && (
                <a
                  href={directory.sourceUrl}
                  rel="noreferrer"
                  style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, textDecoration: "none", textTransform: "uppercase" }}
                  target="_blank"
                >
                  Abrir fonte oficial
                </a>
              )}
            </article>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        {playbook.length > 0 && (
          <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 14 }}>
            <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 10, textTransform: "uppercase" }}>
              Roteiro de contato
            </div>
            <div style={{ display: "grid", gap: 9 }}>
              {playbook.slice(0, 4).map((step, index) => (
                <div key={step.id || `${step.stage}-${index}`} style={{ display: "grid", gap: 5, gridTemplateColumns: "34px minmax(0, 1fr)" }}>
                  <div style={{ color: C.purple, fontFamily: mono, fontSize: 10, fontWeight: 900 }}>{String(index + 1).padStart(2, "0")}</div>
                  <div>
                    <div style={{ color: C.text, fontSize: 12, fontWeight: 900 }}>{sourceTierLabel(step.stage)}</div>
                    <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 3 }}>{step.action}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(lowCompetitionSignals.length > 0 || qualitySignals.length > 0) && (
          <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 14 }}>
            <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.1em", marginBottom: 10, textTransform: "uppercase" }}>
              Modelo de score
            </div>
            <div style={{ display: "grid", gap: 10 }}>
              <div>
                <div style={{ color: C.text, fontSize: 12, fontWeight: 900, marginBottom: 7 }}>Sinais de baixa concorrencia</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {lowCompetitionSignals.map((signal) => <SignalPill key={signal} color={C.purple}>{signal}</SignalPill>)}
                </div>
              </div>
              <div>
                <div style={{ color: C.text, fontSize: 12, fontWeight: 900, marginBottom: 7 }}>Sinais de qualidade</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {qualitySignals.map((signal) => <SignalPill key={signal} color={C.green}>{signal}</SignalPill>)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function TargetNeighborhoodRadar({ stories }) {
  const targetStories = asArray(stories).filter((item) => item.isLiveCandidate && item.targetNeighborhoodKey);
  const [activeKey, setActiveKey] = useState("all");
  const activeTarget = TARGET_NEIGHBORHOODS.find((target) => target.key === activeKey);
  const filteredStories = activeTarget
    ? targetStories.filter((item) => item.targetNeighborhoodKey === activeTarget.key)
    : targetStories;
  const summaryLabel = activeTarget
    ? `${filteredStories.length} candidato${filteredStories.length === 1 ? "" : "s"} neste bairro`
    : `${targetStories.length} candidato${targetStories.length === 1 ? "" : "s"}-alvo`;

  return (
    <section
      data-testid="radar-imobiliario-bairros-alvo"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        display: "grid",
        gap: 14,
        padding: 18,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Bairros-alvo para amanha
          </div>
          <h2 style={{ color: C.text, fontSize: 20, lineHeight: 1.15, margin: "7px 0 0" }}>
            Pinheiros, Perdizes, Itaim Bibi, Campo Belo e Paraiso em uma fila propria
          </h2>
          <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.6, margin: "8px 0 0", maxWidth: 760 }}>
            Esta visao separa os leads publicados ontem da carteira geral. A leitura aqui e simples: bairro, candidato, P0, fonte e proximo passo antes de abrir proposta.
          </p>
        </div>
        <Badge label={summaryLabel} type={targetStories.length ? "warning" : "neutral"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
        <button
          aria-pressed={activeKey === "all"}
          onClick={() => setActiveKey("all")}
          style={{
            background: activeKey === "all" ? withAlpha(C.gold, "18") : C.panel,
            border: `1px solid ${activeKey === "all" ? withAlpha(C.gold, "55") : C.border}`,
            borderRadius: 10,
            color: activeKey === "all" ? C.gold : C.text,
            cursor: "pointer",
            fontFamily: "inherit",
            padding: 11,
            textAlign: "left",
          }}
          type="button"
        >
          <span style={{ display: "block", fontSize: 12, fontWeight: 900 }}>Todos</span>
          <span style={{ color: C.muted, display: "block", fontFamily: mono, fontSize: 10, fontWeight: 800, marginTop: 5 }}>{targetStories.length} candidatos</span>
        </button>
        {TARGET_NEIGHBORHOODS.map((target) => {
          const items = targetStories.filter((item) => item.targetNeighborhoodKey === target.key);
          const p0Count = items.reduce((sum, item) => sum + (item.p0?.length || 0), 0);
          const active = activeKey === target.key;
          return (
            <button
              key={target.key}
              aria-pressed={active}
              onClick={() => setActiveKey(target.key)}
              style={{
                background: active ? withAlpha(C.gold, "18") : C.panel,
                border: `1px solid ${active ? withAlpha(C.gold, "55") : C.border}`,
                borderRadius: 10,
                color: active ? C.gold : C.text,
                cursor: "pointer",
                fontFamily: "inherit",
                padding: 11,
                textAlign: "left",
              }}
              type="button"
            >
              <span style={{ display: "block", fontSize: 12, fontWeight: 900 }}>{target.label}</span>
              <span style={{ color: C.muted, display: "block", fontFamily: mono, fontSize: 10, fontWeight: 800, marginTop: 5 }}>
                {items.length} cand. / {p0Count} P0
              </span>
            </button>
          );
        })}
      </div>

      {filteredStories.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 10 }}>
          {filteredStories.map((item) => (
            <article
              key={item.id}
              style={{
                background: C.panel,
                border: `1px solid ${C.border}`,
                borderLeft: `3px solid ${item.color || C.gold}`,
                borderRadius: 12,
                display: "grid",
                gap: 9,
                padding: 13,
              }}
            >
              <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                <Badge label={item.targetNeighborhood} type="info" />
                <Badge label={item.sourceValidation?.label || "Fonte a validar"} type={item.sourceValidation?.type || "warning"} />
                <Badge label={`${item.score}/100`} type={item.score >= 70 ? "success" : "warning"} />
              </div>
              <div style={{ color: C.text, fontSize: 14, fontWeight: 950, lineHeight: 1.25 }}>{item.displayTitle || item.title}</div>
              <div style={{ color: C.gold, fontSize: 11, fontWeight: 850, lineHeight: 1.45 }}>
                {item.strategy} | {item.sourceOrigin || "fonte a validar"}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 7 }}>
                <div style={{ background: C.bg + "72", border: `1px solid ${C.border}`, borderRadius: 9, padding: 8 }}>
                  <div style={{ color: C.muted, fontSize: 9, fontWeight: 900, textTransform: "uppercase" }}>Entrada</div>
                  <div style={{ color: C.text, fontFamily: mono, fontSize: 11, fontWeight: 900, marginTop: 4 }}>{money(item.purchasePrice)}</div>
                </div>
                <div style={{ background: C.bg + "72", border: `1px solid ${C.border}`, borderRadius: 9, padding: 8 }}>
                  <div style={{ color: C.muted, fontSize: 9, fontWeight: 900, textTransform: "uppercase" }}>Teto</div>
                  <div style={{ color: C.text, fontFamily: mono, fontSize: 11, fontWeight: 900, marginTop: 4 }}>{money(item.secondAuction)}</div>
                </div>
                <div style={{ background: C.bg + "72", border: `1px solid ${C.border}`, borderRadius: 9, padding: 8 }}>
                  <div style={{ color: C.muted, fontSize: 9, fontWeight: 900, textTransform: "uppercase" }}>P0</div>
                  <div style={{ color: item.p0?.length ? C.coral : C.green, fontFamily: mono, fontSize: 11, fontWeight: 900, marginTop: 4 }}>{item.p0?.length || 0}</div>
                </div>
              </div>
              <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>
                Proximo passo: <span style={{ color: C.text, fontWeight: 800 }}>{item.p0Actions?.[0]?.title || item.decision}</span>
              </div>
              {item.sourceValidation?.status === "access_required" && (
                <div style={{ background: C.gold + "12", border: `1px solid ${C.gold}35`, borderRadius: 10, color: C.muted, fontSize: 11, lineHeight: 1.5, padding: "8px 9px" }}>
                  Acesso: <span style={{ color: C.text, fontWeight: 800 }}>{item.sourceValidation.userAction || item.sourceValidation.reason || "Cadastrar/login no leiloeiro para continuar."}</span>
                  {item.sourceValidation.credentialFileHint && (
                    <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 850, marginTop: 4 }}>
                      Arquivo: {item.sourceValidation.credentialFileHint}
                    </div>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, color: C.muted, fontSize: 12, fontWeight: 800, lineHeight: 1.55, padding: 14 }}>
          Nenhum candidato aberto nos bairros-alvo neste snapshot. Use Atualizar radar quando novos leads forem publicados.
        </div>
      )}
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

function isTargetNeighborhoodStory(story) {
  return Boolean(
    story?.targetNeighborhoodKey
    || String(story?.id || "").includes("IM-RADAR-TARGET-")
    || String(story?.title || "").includes("REAL TARGET -"),
  );
}

const DECISION_QUEUE_LANES = [
  {
    color: C.green,
    dataTestId: "radar-imobiliario-avancar",
    intro: "So fica aqui o que ja passa em fonte individual, teto, demanda de saida, comparaveis, P0 e cenario conservador.",
    key: "advance",
    label: "Avancar agora",
    title: "Avancar agora",
  },
  {
    color: C.gold,
    dataTestId: "radar-imobiliario-watchlist",
    intro: "Casos com bairro ou preco interessantes, mas ainda sem prova suficiente para defender capital.",
    key: "watchlist",
    label: "Watchlist",
    title: "Watchlist de prova",
  },
  {
    color: C.coral,
    dataTestId: "radar-imobiliario-bloqueados",
    intro: "Casos vivos no feed, mas bloqueados para proposta enquanto a prova essencial nao aparecer.",
    key: "blocked",
    label: "Bloqueado por prova",
    title: "Bloqueado por prova",
  },
];

function prioritizeActiveCandidateStories(stories) {
  return asArray(stories)
    .map((story, index) => ({ story, index }))
    .sort((left, right) => {
      const leftPriority = isTargetNeighborhoodStory(left.story) ? 0 : 1;
      const rightPriority = isTargetNeighborhoodStory(right.story) ? 0 : 1;
      if (leftPriority !== rightPriority) return leftPriority - rightPriority;
      const leftSourcingScore = Number(left.story?.sourcingScore || left.story?.sourcing?.score || 0);
      const rightSourcingScore = Number(right.story?.sourcingScore || right.story?.sourcing?.score || 0);
      if (leftSourcingScore !== rightSourcingScore) return rightSourcingScore - leftSourcingScore;
      const leftScore = Number(left.story?.score || 0);
      const rightScore = Number(right.story?.score || 0);
      if (leftScore !== rightScore) return rightScore - leftScore;
      return left.index - right.index;
    })
    .map(({ story }) => story);
}

function storiesByDecisionLane(stories) {
  return DECISION_QUEUE_LANES.map((lane) => ({
    ...lane,
    items: prioritizeActiveCandidateStories(stories.filter((story) => story.decisionTier === lane.key)),
  }));
}

function RadarDecisionQueue({ closedCount = 0, discardingId, liveStories, onDiscard }) {
  const lanes = storiesByDecisionLane(asArray(liveStories));
  const allItems = lanes.flatMap((lane) => lane.items);
  const total = allItems.length;
  const activeLabel = pluralizeCase(total, "candidato real aberto", "candidatos reais abertos");
  const closedLabel = pluralizeCase(closedCount, "caso real encerrado", "casos reais encerrados");

  if (!total) return null;

  return (
    <section
      data-testid="radar-imobiliario-abertos"
      style={{
        display: "grid",
        gap: 14,
      }}
    >
      <div
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 14,
          display: "grid",
          gap: 12,
          padding: 16,
        }}
      >
        <div>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Mesa de decisao
          </div>
          <h2 style={{ color: C.text, fontSize: 20, lineHeight: 1.15, margin: "7px 0 0" }}>
            Fila ativa - {activeLabel}
          </h2>
          <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.65, margin: "8px 0 0" }}>
            As tres raias abaixo somam so os abertos ({activeLabel}). {closedCount > 0 ? `${closedLabel} ficam fora desta mesa e aparecem em Fechados/aprendizados.` : "Nao ha encerrados fora desta mesa agora."}
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 8 }}>
          {lanes.map((lane) => (
            <div
              key={lane.key}
              style={{
                background: C.panel,
                border: `1px solid ${withAlpha(lane.color, alpha.border)}`,
                borderLeft: `3px solid ${lane.color}`,
                borderRadius: 10,
                padding: 11,
              }}
            >
              <div style={{ color: lane.color, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                {lane.label}
              </div>
              <div style={{ color: C.text, fontSize: 18, fontWeight: 950, marginTop: 5 }}>
                {lane.items.length}
              </div>
            </div>
          ))}
        </div>
      </div>

      {lanes
        .filter((lane) => lane.items.length > 0)
        .map((lane) => (
          <PerdizesCasePortfolio
            key={lane.key}
            color={lane.color}
            dataTestId={lane.dataTestId}
            eyebrow={lane.label}
            intro={lane.intro}
            discardingId={discardingId}
            items={lane.items}
            onDiscard={onDiscard}
            prominentIdentifier
            title={`${lane.title} - ${pluralizeCase(lane.items.length, "candidato real", "candidatos reais")}`}
          />
        ))}
    </section>
  );
}

function RadarRealStoryPortfolio({ closedStories, discardingId, liveStories, onDiscard, portfolioIntro, portfolioTitle }) {
  const prioritizedLiveStories = prioritizeActiveCandidateStories(liveStories);
  const numberedLiveStories = prioritizedLiveStories.map((story, index) => ({
    ...story,
    identifierNumber: story.identifierNumber || String(index + 1).padStart(2, "0"),
  }));
  const numberedClosedStories = closedStories.map((story, index) => ({
    ...story,
    identifierNumber: story.identifierNumber || String(prioritizedLiveStories.length + index + 1).padStart(2, "0"),
  }));

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
        <RadarDecisionQueue
          closedCount={numberedClosedStories.length}
          discardingId={discardingId}
          liveStories={numberedLiveStories}
          onDiscard={onDiscard}
        />
      )}

      {closedStories.length > 0 && (
        <PerdizesCasePortfolio
          color={C.coral}
          dataTestId="radar-imobiliario-fechados"
          eyebrow="Fechados / aprendizados"
          intro="Casos que saíram do radar ativo. Eles continuam visíveis porque explicam preço teto, P0, descarte, erro evitado e aprendizado para a próxima triagem."
          items={numberedClosedStories}
          prominentIdentifier
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

export default function RadarImobiliario({ data, onRefresh, section = "" }) {
  const [discardError, setDiscardError] = useState("");
  const [discardingId, setDiscardingId] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { closedStories, items, liveStories, usingRealStories } = useMemo(() => radarStoriesForData(data), [data]);
  const auctioneerSourcing = data?.realEstateStrategyTerritoryCandidates?.auctioneerSourcing;
  const activeSection = normalizedRadarSection(section) || "visao-geral";
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
      {activeSection === "candidatos" && discardError && (
        <section style={{ background: withAlpha(C.coral, "10"), border: `1px solid ${withAlpha(C.coral, alpha.border)}`, borderRadius: 12, color: C.coral, fontSize: 12, fontWeight: 800, lineHeight: 1.5, padding: "10px 12px" }}>
          Falha ao descartar candidato: {discardError}
        </section>
      )}
      {activeSection === "visao-geral" && (
      <section id="radar-imobiliario-visao-geral" data-section-id="visao-geral" data-testid="radar-imobiliario-visao-geral" style={{ display: "flex", flexDirection: "column", gap: 18, scrollMarginTop: 18 }}>
        <RadarHero stats={stats} />
      <RadarRefreshBar isRefreshing={isRefreshing} onRefresh={handleRefresh} stats={stats} />
      <TargetNeighborhoodRadar stories={items} />
      </section>
      )}
      {activeSection === "modelo" && (
      <section id="radar-imobiliario-modelo" data-section-id="modelo" style={{ display: "flex", flexDirection: "column", gap: 18, scrollMarginTop: 18 }}>
        <RadarOperatingModel />
      </section>
      )}
      {activeSection === "garimpo" && (
      <section id="radar-imobiliario-garimpo" data-section-id="garimpo" style={{ display: "flex", flexDirection: "column", gap: 18, scrollMarginTop: 18 }}>
        <RadarAuctioneerSourcing sourcing={auctioneerSourcing} />
      </section>
      )}
      {activeSection === "candidatos" && (
      <section id="radar-imobiliario-candidatos" data-section-id="candidatos" style={{ display: "flex", flexDirection: "column", gap: 18, scrollMarginTop: 18 }}>
      <RadarRefreshBar isRefreshing={isRefreshing} onRefresh={handleRefresh} stats={stats} />
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
        prominentIdentifier
        title={portfolioTitle}
      />
      )}
      </section>
      )}
    </main>
  );
}
