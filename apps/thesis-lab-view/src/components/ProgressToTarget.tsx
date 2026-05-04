import { cn } from "@/lib/utils";

interface Props {
  entrada: number;
  alvo: number;
  stop: number;
  precoAtual: number;
  className?: string;
}

/** Barra que mostra onde o preço atual está entre stop e alvo. */
export function ProgressToTarget({ entrada, alvo, stop, precoAtual, className }: Props) {
  const min = Math.min(stop, alvo);
  const max = Math.max(stop, alvo);
  const span = max - min || 1;
  const pos = Math.max(0, Math.min(1, (precoAtual - min) / span)) * 100;
  const entryPos = Math.max(0, Math.min(1, (entrada - min) / span)) * 100;
  const long = alvo > stop;

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex justify-between text-[10px] uppercase tracking-widest text-muted-foreground">
        <span>{long ? "Stop" : "Alvo"}</span>
        <span>Entrada</span>
        <span>{long ? "Alvo" : "Stop"}</span>
      </div>
      <div className="relative h-2 rounded-full bg-surface-2">
        <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-refuted/50 via-primary/40 to-validated/60" />
        <div className="absolute top-1/2 -translate-y-1/2 w-px h-3 bg-foreground/40" style={{ left: `${entryPos}%` }} />
        <div className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-foreground border-2 border-background shadow-glow"
             style={{ left: `calc(${pos}% - 6px)` }} />
      </div>
    </div>
  );
}
