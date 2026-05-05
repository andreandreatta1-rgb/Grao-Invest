type StrategyBadgeProps = {
  label: string;
  tone: "blue" | "purple" | "green";
};

const toneClass = {
  blue: "border-grao-blue/20 bg-grao-blue/10 text-grao-blue",
  purple: "border-violet-400/20 bg-violet-400/[0.08] text-violet-300",
  green: "border-grao-green/20 bg-grao-green/[0.08] text-grao-green",
};

export function StrategyBadge({ label, tone }: StrategyBadgeProps) {
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold ${toneClass[tone]}`}>
      <span aria-hidden="true">▦</span>
      {label}
    </div>
  );
}
