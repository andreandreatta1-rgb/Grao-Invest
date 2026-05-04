import { cn } from "@/lib/utils";
import { fmtPctRatio } from "@/lib/format";

export function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color =
    value >= 0.7 ? "bg-validated" : value >= 0.5 ? "bg-primary" : "bg-pending";
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative h-1.5 flex-1 rounded-full bg-surface-2 overflow-hidden">
        <div className={cn("absolute inset-y-0 left-0 rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-muted-foreground tabular w-10 text-right">{fmtPctRatio(value, 0)}</span>
    </div>
  );
}
