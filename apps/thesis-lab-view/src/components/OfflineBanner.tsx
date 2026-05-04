import { WifiOff } from "lucide-react";
import { useOnlineStatus } from "@/hooks/usePWA";

/** Banner discreto mostrado apenas quando o dispositivo perde conexão. */
export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div className="fixed top-0 inset-x-0 z-[60] safe-top pointer-events-none">
      <div className="mx-auto max-w-screen-md px-4 pt-2">
        <div className="pointer-events-auto flex items-center gap-2 rounded-lg border border-pending/40 bg-pending/10 backdrop-blur-md px-3 py-2 text-xs text-pending shadow-elevated animate-fade-up">
          <WifiOff className="w-3.5 h-3.5" />
          <span className="font-medium">Sem conexão</span>
          <span className="text-pending/70">— exibindo dados em cache.</span>
        </div>
      </div>
    </div>
  );
}
