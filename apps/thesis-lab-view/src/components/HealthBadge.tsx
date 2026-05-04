import { cn } from "@/lib/utils";
import type { SaudeDado } from "@/types/domain";

interface Props {
  saude: SaudeDado;
  label?: string;
  className?: string;
  showLabel?: boolean;
}

const map: Record<SaudeDado, { color: string; text: string; ring: string }> = {
  atualizado:    { color: "bg-validated", text: "Atualizado",    ring: "ring-validated/30" },
  parcial:       { color: "bg-pending",   text: "Parcial",       ring: "ring-pending/30" },
  indisponivel:  { color: "bg-refuted",   text: "Indisponível",  ring: "ring-refuted/30" },
};

export function HealthBadge({ saude, label, className, showLabel = true }: Props) {
  const m = map[saude];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
      <span className={cn("w-1.5 h-1.5 rounded-full ring-4", m.color, m.ring, saude === "atualizado" && "animate-pulse-slow")} />
      {showLabel && <span>{label ?? m.text}</span>}
    </span>
  );
}
