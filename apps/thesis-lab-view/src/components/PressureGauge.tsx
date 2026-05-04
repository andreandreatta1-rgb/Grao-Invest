import { cn } from "@/lib/utils";

/** Medidor de pressão (0..1) — quão próximo a tese está dos gatilhos. */
export function PressureGauge({ value, label = "Pressão dos gatilhos" }: { value: number; label?: string }) {
  const v = Math.max(0, Math.min(1, value));
  const angle = -90 + v * 180; // -90deg .. 90deg
  const zone =
    v >= 0.75 ? "validated" : v >= 0.45 ? "primary" : "pending";
  const color = `hsl(var(--${zone === "validated" ? "validated" : zone === "primary" ? "primary" : "pending"}))`;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-32 h-16 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full"
             style={{
               background: `conic-gradient(from -90deg at 50% 100%,
                 hsl(var(--pending)) 0deg,
                 hsl(var(--primary)) 90deg,
                 hsl(var(--validated)) 180deg)`,
               WebkitMaskImage: "radial-gradient(circle at 50% 100%, transparent 52%, black 53%, black 100%)",
                       maskImage: "radial-gradient(circle at 50% 100%, transparent 52%, black 53%, black 100%)",
             }}
        />
        <div className="absolute left-1/2 bottom-0 origin-bottom h-[58px] w-[2px] rounded-full transition-transform duration-700"
             style={{ background: color, transform: `translateX(-50%) rotate(${angle}deg)`, boxShadow: `0 0 10px ${color}` }} />
        <div className="absolute left-1/2 bottom-0 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-foreground" />
      </div>
      <div className="flex items-baseline gap-1">
        <span className="font-mono text-sm font-semibold tabular" style={{ color }}>{Math.round(v * 100)}%</span>
        <span className={cn("text-[10px] uppercase tracking-widest text-muted-foreground")}>{label}</span>
      </div>
    </div>
  );
}
