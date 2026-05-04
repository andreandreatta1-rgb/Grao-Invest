import type { SpecificMicrotrade, TheseEnvelope } from "@/types/domain";
import { buildLabSections } from "./lab-groups";

export type LabCandidateSuggestion = {
  thesis: TheseEnvelope;
  source: "queued" | "active";
  score: number;
  priority: "alta" | "media" | "baixa";
  expectedTimeLabel: string;
  triggerReason: string;
  nextStepLabel: string;
  triggerPressurePct: number;
};

export function buildLabCandidateSuggestions(items: TheseEnvelope[], now = Date.now()): LabCandidateSuggestion[] {
  const sections = buildLabSections(items, now);
  const source: LabCandidateSuggestion["source"] = sections.queued.length > 0 ? "queued" : "active";
  const pool = source === "queued" ? sections.queued : sections.activeNow;

  return pool
    .map((thesis) => buildCandidateSuggestion(thesis, source, now))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

function buildCandidateSuggestion(
  thesis: TheseEnvelope,
  source: LabCandidateSuggestion["source"],
  now: number,
): LabCandidateSuggestion {
  const spec = thesis.specific as Partial<SpecificMicrotrade>;
  const triggerPressurePct = clamp(Math.round(spec.trigger_pressure_pct ?? 0), 0, 100);
  const confidencePct = clamp(Math.round(thesis.confidence_pct), 0, 100);
  const completionPct = clamp(Math.round(thesis.completion.completion_pct), 0, 100);
  const freshnessBonus =
    thesis.data_quality.freshness_status === "fresh"
      ? 10
      : thesis.data_quality.freshness_status === "partial"
        ? 5
        : thesis.data_quality.freshness_status === "stale"
          ? 0
          : -8;
  const statusBonus =
    thesis.status === "confirmando"
      ? 12
      : thesis.status === "monitorando"
        ? 8
        : thesis.status === "preparando"
          ? 4
          : 0;

  const score = clamp(
    Math.round((triggerPressurePct * 0.42) + (confidencePct * 0.3) + (completionPct * 0.12) + freshnessBonus + statusBonus),
    0,
    100,
  );

  return {
    thesis,
    source,
    score,
    priority: score >= 75 ? "alta" : score >= 50 ? "media" : "baixa",
    expectedTimeLabel: buildExpectedTimeLabel(spec, now),
    triggerReason: buildTriggerReason(thesis, spec),
    nextStepLabel: buildNextStepLabel(thesis),
    triggerPressurePct,
  };
}

function buildExpectedTimeLabel(spec: Partial<SpecificMicrotrade>, now: number) {
  const expiresAt = spec.expires_at ? new Date(spec.expires_at).getTime() : Number.NaN;
  if (Number.isFinite(expiresAt) && expiresAt > now) {
    const mins = Math.max(1, Math.round((expiresAt - now) / 60_000));
    return `${mins} min`;
  }
  if (typeof spec.window_min === "number" && Number.isFinite(spec.window_min) && spec.window_min > 0) {
    return `${Math.round(spec.window_min)} min`;
  }
  return "sem janela";
}

function buildTriggerReason(thesis: TheseEnvelope, spec: Partial<SpecificMicrotrade>) {
  const summary = cleanText(spec.short_thesis_summary);
  if (summary) return summary;
  const evidence = cleanText(spec.evidences?.[0]);
  if (evidence) return evidence;
  return cleanText(thesis.suggested_action) || cleanText(thesis.hypothesis) || "Aguardando novo gatilho";
}

function buildNextStepLabel(thesis: TheseEnvelope) {
  if (thesis.status === "confirmando") return "Confirmar gatilho";
  if (thesis.status === "preparando") return "Preparar entrada";
  return "Rearmar leitura";
}

function cleanText(value?: string) {
  return (value ?? "").trim();
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
