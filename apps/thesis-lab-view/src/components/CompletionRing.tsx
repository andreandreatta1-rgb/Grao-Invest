import { cn } from "@/lib/utils";

interface Props {
  pct: number; // 0..100
  size?: number;
  className?: string;
  label?: string;
}

/** Anel de completude do envelope da tese. */
export function CompletionRing({ pct, size = 28, className, label }: Props) {
  const v = Math.max(0, Math.min(100, pct));
  const stroke = 3;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (v / 100) * c;
  const color = v >= 100 ? "hsl(var(--validated))" : v >= 70 ? "hsl(var(--primary))" : "hsl(var(--pending))";

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} title={label ?? `Completude ${v}%`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="hsl(var(--surface-2))" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <span className="font-mono text-[10px] text-muted-foreground tabular">{Math.round(v)}%</span>
    </span>
  );
}
