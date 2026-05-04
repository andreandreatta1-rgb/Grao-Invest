import { cn } from "@/lib/utils";
import type { StatusTese } from "@/types/domain";

const map: Record<StatusTese, { label: string; cls: string; live?: boolean }> = {
  preparando:           { label: "Preparando",           cls: "bg-muted text-muted-foreground" },
  confirmando:          { label: "Confirmando",          cls: "bg-pending/15 text-pending", live: true },
  monitorando:          { label: "Monitorando",          cls: "bg-primary/15 text-primary", live: true },
  validada:             { label: "Validada",             cls: "bg-validated/15 text-validated" },
  refutada:             { label: "Refutada",             cls: "bg-refuted/15 text-refuted" },
  encerrada_tempo:      { label: "Encerrada (tempo)",    cls: "bg-info/10 text-info" },
  encerrada_inatividade:{ label: "Encerrada (inativa)",  cls: "bg-muted text-muted-foreground" },
};

export function StatusPill({ status, className }: { status: StatusTese; className?: string }) {
  const m = map[status];
  return (
    <span className={cn("pill", m.cls, className)}>
      <span className={cn("w-1.5 h-1.5 rounded-full bg-current opacity-90", m.live && "animate-pulse-slow")} />
      {m.label}
    </span>
  );
}
