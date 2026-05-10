import { describe, expect, it } from "vitest";
import type { SpecificMicrotrade, TheseEnvelope } from "@/types/domain";
import { buildLabCandidateSuggestions } from "./lab-candidates";

function makeMicrotrade(
  overrides: Partial<TheseEnvelope> & {
    id: string;
    status: TheseEnvelope["status"];
    updated_at: string;
    specific?: Partial<SpecificMicrotrade>;
    closed_at?: string;
  },
): TheseEnvelope {
  return {
    id: overrides.id,
    front: "cripto",
    title: overrides.title ?? overrides.id,
    asset_label: overrides.asset_label ?? overrides.id.toUpperCase(),
    hypothesis: overrides.hypothesis ?? "Hipotese teste",
    status: overrides.status,
    opened_at: overrides.opened_at ?? "2026-05-04T19:00:00Z",
    updated_at: overrides.updated_at,
    closed_at: overrides.closed_at,
    expected_result_pct: overrides.expected_result_pct ?? 0.8,
    current_result_pct: overrides.current_result_pct ?? 0.1,
    confidence_pct: overrides.confidence_pct ?? 70,
    entry_value: overrides.entry_value ?? 100,
    current_value: overrides.current_value ?? 101,
    target_value: overrides.target_value ?? 102,
    stop_or_invalidation: overrides.stop_or_invalidation ?? "stop",
    stop_value: overrides.stop_value ?? 99,
    suggested_action: overrides.suggested_action ?? "manter",
    learning_note: overrides.learning_note ?? "",
    data_quality: overrides.data_quality ?? {
      freshness_status: "fresh",
      last_update_at: overrides.updated_at,
      confidence_in_data_pct: 80,
    },
    specific: {
      kind: "microtrade",
      window_min: 20,
      expires_at: "2026-05-04T19:40:00Z",
      last_tick_at: "2026-05-04T19:12:00Z",
      is_data_delayed: false,
      trigger_pressure_pct: 55,
      evidences: ["teste"],
      short_thesis_summary: "Resumo curto do gatilho",
      ...overrides.specific,
    },
    completion: overrides.completion ?? {
      is_complete: true,
      completion_pct: 100,
      missing_fields: [],
      pending_items: [],
      next_required_action: "seguir",
    },
  };
}

describe("lab candidates", () => {
  it("builds ranked candidate suggestions from queued microtrades only", () => {
    const now = new Date("2026-05-04T19:30:00Z").getTime();
    const items = [
      makeMicrotrade({
        id: "candidate-high",
        asset_label: "BTC/USDT",
        status: "confirmando",
        updated_at: "2026-05-04T19:29:00Z",
        confidence_pct: 78,
        specific: {
          trigger_pressure_pct: 84,
          last_tick_at: "2026-05-04T19:11:00Z",
          expires_at: "2026-05-04T19:41:00Z",
          short_thesis_summary: "Reabsorver rompimento falso na borda inferior.",
          evidences: ["CVD positivo", "sweep de liquidez"],
        },
        suggested_action: "Confirmar entrada se o fluxo mantiver compra.",
      }),
      makeMicrotrade({
        id: "candidate-low",
        asset_label: "ETH/USDT",
        status: "preparando",
        updated_at: "2026-05-04T19:28:00Z",
        confidence_pct: 58,
        data_quality: {
          freshness_status: "partial",
          last_update_at: "2026-05-04T19:28:00Z",
          confidence_in_data_pct: 65,
        },
        specific: {
          trigger_pressure_pct: 38,
          last_tick_at: "2026-05-04T19:05:00Z",
          expires_at: "2026-05-04T19:50:00Z",
          short_thesis_summary: "Aguardar retorno na VWAP.",
          evidences: ["fluxo ainda misto"],
        },
        suggested_action: "Aguardar gatilho primario.",
      }),
      makeMicrotrade({
        id: "live-now",
        asset_label: "SOL/USDT",
        status: "monitorando",
        updated_at: "2026-05-04T19:29:00Z",
        confidence_pct: 75,
        specific: {
          trigger_pressure_pct: 71,
          last_tick_at: "2026-05-04T19:25:00Z",
          expires_at: "2026-05-04T19:38:00Z",
        },
      }),
      makeMicrotrade({
        id: "closed-win",
        asset_label: "BNB/USDT",
        status: "validada",
        updated_at: "2026-05-04T19:20:00Z",
        closed_at: "2026-05-04T19:20:00Z",
      }),
    ];

    const suggestions = buildLabCandidateSuggestions(items, now);

    expect(suggestions.map((item) => item.thesis.id)).toEqual(["candidate-high", "candidate-low"]);
    expect(suggestions[0]?.priority).toBe("alta");
    expect(suggestions[0]?.source).toBe("queued");
    expect(suggestions[0]?.triggerReason).toContain("Reabsorver rompimento falso");
    expect(suggestions[0]?.expectedTimeLabel).toBe("11 min");
    expect(suggestions[0]?.nextStepLabel).toBe("Confirmar gatilho");
    expect(suggestions[1]?.priority).toBe("media");
    expect(suggestions[1]?.nextStepLabel).toBe("Preparar entrada");
  });

  it("limits the radar to the strongest three candidates", () => {
    const now = new Date("2026-05-04T19:30:00Z").getTime();
    const ids = ["a", "b", "c", "d"].map((id, index) =>
      makeMicrotrade({
        id,
        status: "confirmando",
        updated_at: `2026-05-04T19:2${index}:00Z`,
        confidence_pct: 80 - (index * 5),
        specific: {
          trigger_pressure_pct: 90 - (index * 10),
          last_tick_at: "2026-05-04T19:10:00Z",
          expires_at: "2026-05-04T19:45:00Z",
        },
      }),
    );

    const suggestions = buildLabCandidateSuggestions(ids, now);

    expect(suggestions).toHaveLength(3);
    expect(suggestions.map((item) => item.thesis.id)).toEqual(["a", "b", "c"]);
  });

  it("falls back to live actionable setups when there are no queued candidates", () => {
    const now = new Date("2026-05-04T19:30:00Z").getTime();
    const items = [
      makeMicrotrade({
        id: "live-strong",
        status: "monitorando",
        updated_at: "2026-05-04T19:29:00Z",
        confidence_pct: 76,
        specific: {
          trigger_pressure_pct: 81,
          last_tick_at: "2026-05-04T19:26:00Z",
          expires_at: "2026-05-04T19:39:00Z",
        },
      }),
      makeMicrotrade({
        id: "live-second",
        status: "confirmando",
        updated_at: "2026-05-04T19:28:00Z",
        confidence_pct: 64,
        specific: {
          trigger_pressure_pct: 62,
          last_tick_at: "2026-05-04T19:24:00Z",
          expires_at: "2026-05-04T19:37:00Z",
        },
      }),
    ];

    const suggestions = buildLabCandidateSuggestions(items, now);

    expect(suggestions.map((item) => item.thesis.id)).toEqual(["live-strong", "live-second"]);
    expect(suggestions[0]?.source).toBe("active");
  });

  it("prioritizes dedicated scanner candidates over queued or active cards", () => {
    const now = new Date("2026-05-04T19:30:00Z").getTime();
    const items = [
      makeMicrotrade({
        id: "queued-card",
        asset_label: "Bitcoin (BTC)",
        status: "confirmando",
        updated_at: "2026-05-04T19:28:00Z",
        specific: {
          trigger_pressure_pct: 60,
          last_tick_at: "2026-05-04T19:20:00Z",
          expires_at: "2026-05-04T19:44:00Z",
        },
      }),
    ];
    const scanner = [
      makeMicrotrade({
        id: "scanner-eth",
        asset_label: "Ethereum (ETH)",
        status: "preparando",
        updated_at: "2026-05-04T19:29:00Z",
        confidence_pct: 83,
        specific: {
          trigger_pressure_pct: 88,
          last_tick_at: "2026-05-04T19:27:00Z",
          expires_at: "2026-05-04T19:43:00Z",
          short_thesis_summary: "Fluxo comprador acelerando no scanner amplo.",
        },
      }),
      makeMicrotrade({
        id: "scanner-sol",
        asset_label: "Solana (SOL)",
        status: "confirmando",
        updated_at: "2026-05-04T19:28:30Z",
        confidence_pct: 79,
        specific: {
          trigger_pressure_pct: 80,
          last_tick_at: "2026-05-04T19:26:00Z",
          expires_at: "2026-05-04T19:41:00Z",
          short_thesis_summary: "Rompimento curto com continuidade acima da media.",
        },
      }),
    ];

    const suggestions = buildLabCandidateSuggestions(items, now, scanner);

    expect(suggestions.map((item) => item.thesis.id)).toEqual(["scanner-sol", "scanner-eth"]);
    expect(suggestions.every((item) => item.source === "scanner")).toBe(true);
    expect(suggestions.map((item) => item.triggerReason)).toContain("Fluxo comprador acelerando no scanner amplo.");
  });
});
