import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string;
  hint?: string;
  trend?: "up" | "down" | "neutral";
  accent?: "primary" | "gold" | "validated" | "refuted" | "muted";
  className?: string;
}

const accents = {
  primary:   "text-primary",
  gold:      "text-accent",
  validated: "text-validated",
  refuted:   "text-refuted",
  muted:     "text-foreground",
};

export function MetricCard({ label, value, hint, accent = "muted", className }: Props) {
  return (
    <div className={cn("glass-card p-4 flex flex-col gap-1.5", className)}>
      <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">{label}</span>
      <span className={cn("font-display text-2xl font-semibold tabular leading-none", accents[accent])}>{value}</span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </div>
  );
}
