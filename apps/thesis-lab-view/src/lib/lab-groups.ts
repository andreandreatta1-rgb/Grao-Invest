import { isClosedThesis, type SpecificMicrotrade, type TheseEnvelope } from "@/types/domain";

export type LabSections = {
  activeNow: TheseEnvelope[];
  queued: TheseEnvelope[];
  recentClosed: TheseEnvelope[];
};

export function buildLabSections(items: TheseEnvelope[], now = Date.now()): LabSections {
  const sorted = [...items].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  const sections: LabSections = {
    activeNow: [],
    queued: [],
    recentClosed: [],
  };

  for (const item of sorted) {
    if (isClosedThesis(item)) {
      sections.recentClosed.push(item);
      continue;
    }

    if (isLiveLabMicrotrade(item, now)) {
      sections.activeNow.push(item);
      continue;
    }

    sections.queued.push(item);
  }

  return sections;
}

export function isLiveLabMicrotrade(item: TheseEnvelope, now = Date.now()) {
  const spec = item.specific as Partial<SpecificMicrotrade>;
  if (spec.kind !== "microtrade") return false;
  if (isClosedThesis(item)) return false;
  if (!spec.last_tick_at || !spec.expires_at) return false;

  const lastTickAgeMs = now - new Date(spec.last_tick_at).getTime();
  const expiresAtMs = new Date(spec.expires_at).getTime();

  return Number.isFinite(lastTickAgeMs) && lastTickAgeMs <= 10 * 60_000 && expiresAtMs > now;
}
