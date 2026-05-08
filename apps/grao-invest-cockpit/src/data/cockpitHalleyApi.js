const FEEDS = Object.freeze([
  ["dashboardSummary", "/api/dashboard/summary/1"],
  ["currentMonitor", "/api/theses/current-monitor/latest"],
  ["realEstateCandidates", "/api/real-estate/candidates"],
  ["realEstateStrategyTerritoryCandidates", "/api/real-estate/strategy-territory-candidates"],
]);

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`.trim());
  }
  return response.json();
}

function parseCandidateId(thesisId) {
  const match = String(thesisId || "").match(/IM-RADAR-(\d+)/i);
  return match ? match[1] : null;
}

function parseCurrencyEvidence(value) {
  const normalized = String(value || "")
    .replace(/[^\d,.-]/g, "")
    .replace(/\.(?=\d{3}(?:\D|$))/g, "")
    .replace(",", ".");
  const number = Number(normalized);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function updatePayloadForPending(item, evidence) {
  const key = String(item?.key || "").toLowerCase();
  const text = String(evidence || "").trim();
  const normalizedEvidence = text.toLowerCase();
  const payload = {
    notes: `Pendencia resolvida (${item?.priority || "P"} ${item?.title || key}): ${text}`,
  };

  if (key === "occupancy") {
    payload.occupancy_status = normalizedEvidence.includes("ocupado") && !normalizedEvidence.includes("desocupado")
      ? "ocupado"
      : "desocupado";
  } else if (key === "registration") {
    payload.has_registration = true;
  } else if (key === "edital") {
    payload.has_edital = true;
  } else if (key === "condo_debt") {
    payload.condo_debt_known = true;
  } else if (key === "iptu_debt") {
    payload.iptu_debt_known = true;
  } else if (key === "sale_comparables") {
    payload.sale_comparables_count = 3;
  } else if (key === "rent_comparables") {
    payload.rent_comparables_count = 3;
  } else if (key === "renovation_budget") {
    const budget = parseCurrencyEvidence(text);
    if (budget !== null) payload.renovation_budget = budget;
  } else if (key === "financing") {
    payload.financing_validated = true;
  } else if (key === "plan_b") {
    payload.plan_b = text;
  }

  return payload;
}

export async function resolveRealEstatePending({ thesisId, item, evidence }) {
  const candidateId = parseCandidateId(thesisId);
  if (!candidateId) {
    throw new Error("Nao foi possivel identificar o candidato imobiliario desta tese.");
  }

  const response = await fetch(`/api/real-estate/candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updatePayloadForPending(item, evidence)),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`.trim());
  }
  return response.json();
}

export async function saveRealEstateVisitEvidence({ thesisId, section, evidence }) {
  const candidateId = parseCandidateId(thesisId);
  if (!candidateId) {
    throw new Error("Nao foi possivel identificar o candidato imobiliario desta tese.");
  }

  const response = await fetch(`/api/real-estate/candidates/${candidateId}/visit-evidence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ section, evidence }),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`.trim());
  }
  return response.json();
}

export async function fetchCockpitPayloads() {
  const settled = await Promise.allSettled(FEEDS.map(([, url]) => fetchJson(url)));
  const result = {
    dashboardSummary: null,
    currentMonitor: null,
    realEstateCandidates: null,
    realEstateStrategyTerritoryCandidates: null,
    errors: [],
  };

  settled.forEach((entry, index) => {
    const [feed] = FEEDS[index];
    if (entry.status === "fulfilled") {
      result[feed] = entry.value;
      return;
    }

    result.errors.push({
      feed,
      message: entry.reason instanceof Error ? entry.reason.message : String(entry.reason),
    });
  });

  return result;
}
