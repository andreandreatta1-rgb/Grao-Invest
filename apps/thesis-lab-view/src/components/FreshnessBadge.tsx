import { cn } from "@/lib/utils";
import type { FreshnessStatus } from "@/types/domain";
import { fmtRelative } from "@/lib/format";

const map: Record<FreshnessStatus, { color: string; ring: string; label: string }> = {
  fresh:   { color: "bg-validated", ring: "ring-validated/30", label: "Atualizado" },
  partial: { color: "bg-pending",   ring: "ring-pending/30",   label: "Parcial" },
  stale:   { color: "bg-pending",   ring: "ring-pending/30",   label: "Defasado" },
  missing: { color: "bg-refuted",   ring: "ring-refuted/30",   label: "Indisponível" },
};

interface Props {
  status: FreshnessStatus;
  lastUpdateAt?: string;
  confidencePct?: number;
  className?: string;
}

export function FreshnessBadge({ status, lastUpdateAt, confidencePct, className }: Props) {
  const m = map[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-[11px] text-muted-foreground", className)}>
      <span className={cn("w-1.5 h-1.5 rounded-full ring-4", m.color, m.ring, status === "fresh" && "animate-pulse-slow")} />
      <span>{m.label}</span>
      {lastUpdateAt && <span className="tabular">· {fmtRelative(lastUpdateAt)}</span>}
      {typeof confidencePct === "number" && (
        <span className="tabular">· dado {Math.round(confidencePct)}%</span>
      )}
    </span>
  );
}
