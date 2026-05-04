import { describe, expect, it } from "vitest";
import type { SpecificMicrotrade, TheseEnvelope } from "@/types/domain";
import { buildLabSections } from "./lab-groups";

function makeMicrotrade(
  overrides: Partial<TheseEnvelope> & {
    id: string;
    status: TheseEnvelope["status"];
    updated_at: string;
    opened_at?: string;
    closed_at?: string;
    specific?: Partial<SpecificMicrotrade>;
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
      last_tick_at: "2026-05-04T19:25:00Z",
      is_data_delayed: false,
      trigger_pressure_pct: 55,
      evidences: ["teste"],
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

describe("lab groups", () => {
  it("classifies live, queued, and historical microtrades into separate sections", () => {
    const now = new Date("2026-05-04T19:30:00Z").getTime();
    const items = [
      makeMicrotrade({
        id: "live-now",
        status: "monitorando",
        updated_at: "2026-05-04T19:29:00Z",
        specific: {
          last_tick_at: "2026-05-04T19:25:00Z",
          expires_at: "2026-05-04T19:38:00Z",
        },
      }),
      makeMicrotrade({
        id: "queued-open",
        status: "confirmando",
        updated_at: "2026-05-04T19:28:00Z",
        specific: {
          last_tick_at: "2026-05-04T19:10:00Z",
          expires_at: "2026-05-04T19:45:00Z",
        },
      }),
      makeMicrotrade({
        id: "closed-win",
        status: "validada",
        updated_at: "2026-05-04T19:27:00Z",
        closed_at: "2026-05-04T19:27:00Z",
      }),
    ];

    const sections = buildLabSections(items, now);

    expect(sections.activeNow.map((item) => item.id)).toEqual(["live-now"]);
    expect(sections.queued.map((item) => item.id)).toEqual(["queued-open"]);
    expect(sections.recentClosed.map((item) => item.id)).toEqual(["closed-win"]);
  });

  it("treats lifecycle-closed statuses as history even when closed_at is missing", () => {
    const now = new Date("2026-05-04T19:30:00Z").getTime();
    const items = [
      makeMicrotrade({
        id: "validated-without-closed-at",
        status: "validada",
        updated_at: "2026-05-04T19:29:00Z",
      }),
      makeMicrotrade({
        id: "preparing-open",
        status: "preparando",
        updated_at: "2026-05-04T19:28:00Z",
        specific: {
          last_tick_at: "2026-05-04T19:02:00Z",
          expires_at: "2026-05-04T19:42:00Z",
        },
      }),
    ];

    const sections = buildLabSections(items, now);

    expect(sections.activeNow).toHaveLength(0);
    expect(sections.queued.map((item) => item.id)).toEqual(["preparing-open"]);
    expect(sections.recentClosed.map((item) => item.id)).toEqual(["validated-without-closed-at"]);
  });
});
