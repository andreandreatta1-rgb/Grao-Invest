import { Outlet, NavLink, useLocation, Link } from "react-router-dom";
import { Activity, FlaskConical, Inbox, LineChart, Radar, Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { api, isMock } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import { HealthBadge } from "@/components/HealthBadge";
import { OfflineBanner } from "@/components/OfflineBanner";
import type { SaudeDado } from "@/types/domain";

const tabs = [
  { to: "/",          label: "Cockpit",   icon: Activity },
  { to: "/teses",     label: "Teses",     icon: Radar },
  { to: "/lab",       label: "Lab",       icon: FlaskConical },
  { to: "/mercado",   label: "Mercado",   icon: LineChart },
  { to: "/decisoes",  label: "Decisões",  icon: Inbox },
];

export default function MobileShell() {
  const { pathname } = useLocation();
  const { data } = useQuery({ queryKey: ["cockpit-resumo"], queryFn: api.cockpit, refetchInterval: 30_000 });

  const titleMap: Record<string, string> = {
    "/": "Cockpit",
    "/teses": "Teses",
    "/lab": "Laboratório Realtime",
    "/mercado": "Mercado",
    "/decisoes": "Centro de Decisões",
    "/config": "Configuração",
    "/instalar": "Instalar app",
  };
  const title = titleMap[pathname.split("/").slice(0, 2).join("/")] ?? "Grão Invest";
  const overallHealth: SaudeDado =
    !data ? "atualizado" :
    Object.values(data.frentes).some(f => f.saude === "indisponivel") ? "indisponivel" :
    Object.values(data.frentes).some(f => f.saude === "parcial") ? "parcial" : "atualizado";

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <OfflineBanner />
      {/* Header */}
      <header className="safe-top sticky top-0 z-40 border-b border-border/60 bg-background/85 backdrop-blur-xl">
        <div className="mx-auto max-w-screen-md px-4 pt-3 pb-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-primary grid place-items-center shadow-glow">
              <span className="font-display text-sm font-bold text-primary-foreground">G</span>
            </div>
            <div className="flex flex-col leading-tight">
              <span className="font-display text-[15px] font-semibold tracking-tight">{title}</span>
              <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Grão Invest · Laboratório</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-end gap-0.5">
              <HealthBadge saude={overallHealth} label="Sistema" />
              {data && (
                <span className="text-[10px] text-muted-foreground tabular">
                  {isMock() && <span className="text-accent mr-1">mock</span>}
                  atualizado {fmtRelative(data.ultimaAtualizacao)}
                </span>
              )}
            </div>
            <Link
              to="/config"
              aria-label="Configuração da API"
              className="w-9 h-9 rounded-lg bg-surface-1 border border-border/60 grid place-items-center text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors"
            >
              <Settings2 className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Conteúdo */}
      <main className="flex-1 mx-auto w-full max-w-screen-md px-4 pt-4 pb-28">
        <Outlet />
      </main>

      {/* Tab bar */}
      <nav className="safe-bottom fixed bottom-0 inset-x-0 z-50 border-t border-border/60 bg-background/90 backdrop-blur-xl">
        <ul className="mx-auto max-w-screen-md grid grid-cols-5">
          {tabs.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn(
                    "relative flex flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
                    isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && <span className="absolute top-0 h-0.5 w-8 rounded-full bg-primary shadow-glow" />}
                    <Icon className={cn("w-5 h-5 transition-transform", isActive && "scale-110")} strokeWidth={isActive ? 2.4 : 1.8} />
                    <span>{label}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
