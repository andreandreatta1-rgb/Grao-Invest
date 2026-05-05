import { useMemo, useState } from "react";
import { BottomNav } from "./components/BottomNav";
import { TabBar } from "./components/TabBar";
import { AnalisarScreen } from "./screens/AnalisarScreen";
import { MercadoScreen } from "./screens/MercadoScreen";
import { TesesScreen } from "./screens/TesesScreen";

type MainTab = "teses" | "mercado" | "analisar";
type NavItem = MainTab | "perfil";

const tabs: { id: MainTab; label: string }[] = [
  { id: "teses", label: "Teses" },
  { id: "mercado", label: "Mercado" },
  { id: "analisar", label: "Analisar" },
];

const navItems: { id: NavItem; label: string; icon: string }[] = [
  { id: "teses", label: "Teses", icon: "▤" },
  { id: "mercado", label: "Mercado", icon: "↗" },
  { id: "analisar", label: "Analisar", icon: "⌁" },
  { id: "perfil", label: "Perfil", icon: "●" },
];

function App() {
  const [activeTab, setActiveTab] = useState<MainTab>("teses");
  const [activeNav, setActiveNav] = useState<NavItem>("teses");

  const screen = useMemo(() => {
    if (activeTab === "mercado") return <MercadoScreen />;
    if (activeTab === "analisar") return <AnalisarScreen />;
    return <TesesScreen />;
  }, [activeTab]);

  function changeTab(tab: MainTab) {
    setActiveTab(tab);
    setActiveNav(tab);
  }

  function changeNav(item: NavItem) {
    setActiveNav(item);
    if (item !== "perfil") setActiveTab(item);
  }

  return (
    <main className="min-h-screen bg-grao-bg px-5 py-5 text-white sm:flex sm:items-start sm:justify-center">
      <div className="relative flex min-h-[844px] w-full max-w-[390px] flex-col overflow-hidden rounded-[48px] bg-grao-bg shadow-phone ring-1 ring-white/8">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[200px] bg-[radial-gradient(ellipse_at_50%_0%,rgba(0,212,170,0.06)_0%,transparent_70%)]" />

        <StatusBar />

        <header className="relative bg-[linear-gradient(180deg,#141c30_0%,transparent_100%)] px-6 pt-5">
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-gradient-to-br from-grao-green to-grao-green2 text-lg font-black text-grao-bg shadow-[0_4px_16px_rgba(0,212,170,0.4)]">
                G
              </div>
              <div className="text-lg font-bold tracking-[-0.02em]">
                <span className="bg-gradient-to-br from-grao-green to-grao-green2 bg-clip-text text-transparent">Grão</span> Invest
              </div>
            </div>
            <button
              type="button"
              className="relative flex h-[38px] w-[38px] items-center justify-center rounded-xl border border-white/7 bg-grao-card2 transition-all duration-200 hover:scale-105 hover:bg-grao-card"
              aria-label="Notificações"
            >
              <BellIcon />
              <span className="absolute right-2 top-2 h-[7px] w-[7px] rounded-full border-2 border-grao-bg bg-grao-green" />
            </button>
          </div>
          <TabBar tabs={tabs} activeTab={activeTab} onChange={changeTab} />
        </header>

        <div className="flex-1 overflow-y-auto px-6 pb-5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {screen}
        </div>

        <button
          type="button"
          className="absolute bottom-[90px] right-6 z-20 flex h-[52px] w-[52px] items-center justify-center rounded-2xl bg-gradient-to-br from-grao-green to-grao-green2 text-2xl font-light text-grao-bg shadow-[0_8px_24px_rgba(0,212,170,0.4)] transition-all duration-200 hover:scale-110 hover:rotate-90"
          aria-label="Nova tese"
        >
          +
        </button>

        <BottomNav items={navItems} activeItem={activeNav} onChange={changeNav} />
      </div>
    </main>
  );
}

function StatusBar() {
  return (
    <div className="relative z-10 flex items-center justify-between px-7 pt-3.5 text-[13px] font-semibold text-white">
      <span>18:17</span>
      <div className="flex items-center gap-1.5">
        <SignalIcon />
        <WifiIcon />
        <span className="text-xs font-bold text-[#a8ff78]">82%</span>
      </div>
    </div>
  );
}

function SignalIcon() {
  return (
    <svg width="16" height="12" viewBox="0 0 16 12" fill="white" opacity="0.9" aria-hidden="true">
      <rect x="0" y="3" width="3" height="9" rx="1" />
      <rect x="4.5" y="2" width="3" height="10" rx="1" />
      <rect x="9" y="0" width="3" height="12" rx="1" />
      <rect x="13.5" y="0" width="2.5" height="12" rx="1" opacity="0.3" />
    </svg>
  );
}

function WifiIcon() {
  return (
    <svg width="15" height="12" viewBox="0 0 15 12" fill="white" opacity="0.9" aria-hidden="true">
      <path d="M7.5 2.5 C5 2.5 2.8 3.6 1.2 5.4L0 4.1C2 1.9 4.6 0.5 7.5 0.5s5.5 1.4 7.5 3.6L13.8 5.4C12.2 3.6 10 2.5 7.5 2.5z" />
      <path d="M7.5 5.5C6 5.5 4.7 6.1 3.7 7.1L2.5 5.9C3.8 4.7 5.6 4 7.5 4s3.7.7 5 1.9L11.3 7.1C10.3 6.1 9 5.5 7.5 5.5z" />
      <circle cx="7.5" cy="10" r="1.5" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

export default App;
