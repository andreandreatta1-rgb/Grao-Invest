import { cn } from "@/lib/utils";
import type { Frente } from "@/types/domain";

const map: Record<Frente, string> = {
  B3:      "bg-primary/10 text-primary border-primary/30",
  Cripto:  "bg-accent/10 text-accent border-accent/30",
  Imoveis: "bg-info/10 text-info border-info/30",
};

export function FrenteBadge({ frente, className }: { frente: Frente; className?: string }) {
  return (
    <span className={cn("pill border", map[frente], className)}>
      {frente === "Imoveis" ? "Imóveis" : frente}
    </span>
  );
}
