import type { StatPillData } from "../types";

type StatPillProps = {
  stat: StatPillData;
};

const toneClass: Record<NonNullable<StatPillData["tone"]>, string> = {
  default: "text-white",
  green: "text-grao-green",
  date: "text-grao-text2 text-xs",
  red: "text-grao-red",
  gold: "text-grao-gold",
};

export function StatPill({ stat }: StatPillProps) {
  const valueTone = toneClass[stat.tone ?? "default"];

  return (
    <div className="flex-1 rounded-xl border border-white/7 bg-white/[0.04] px-3 py-2.5">
      <div className="mb-1 text-[9px] font-bold uppercase tracking-[0.08em] text-grao-text3">
        {stat.label}
      </div>
      <div className={`text-sm font-bold ${valueTone}`}>{stat.value}</div>
    </div>
  );
}
