import { intradayBars, marketAssets } from "../data/mockData";

export function MercadoScreen() {
  return (
    <section className="content-screen">
      <SectionHeader title="Índices & Ativos" badge="Tempo real" />

      <div className="mb-5 rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-5">
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="text-sm font-bold">IBOV — Hoje</h2>
          <span className="text-sm font-bold text-grao-green">+0,82%</span>
        </div>
        <BarChart values={intradayBars} labels={["9h", "12h", "15h", "18h17"]} />
      </div>

      <SectionHeader title="Ações em destaque" />
      {marketAssets.map((asset) => (
        <button
          key={asset.ticker}
          type="button"
          className="mb-2.5 flex w-full items-center justify-between rounded-2xl border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card px-4 py-3.5 text-left transition-all duration-200 hover:translate-x-1 hover:border-white/10"
        >
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl border text-[13px] font-extrabold ${logoTone(asset.tone)}`}>
              {asset.logo}
            </div>
            <div>
              <div className="text-sm font-bold text-white">{asset.ticker}</div>
              <div className="mt-0.5 text-[11px] text-grao-text3">{asset.name}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[15px] font-bold text-white">{asset.price}</div>
            <div className={`mt-0.5 text-xs font-semibold ${asset.changePct >= 0 ? "text-grao-green2" : "text-grao-red"}`}>
              {asset.changePct > 0 ? "+" : ""}
              {asset.changePct.toFixed(2).replace(".", ",")}%
            </div>
          </div>
        </button>
      ))}
      <div className="h-5" />
    </section>
  );
}

type SectionHeaderProps = {
  title: string;
  badge?: string;
};

function SectionHeader({ title, badge }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h1 className="text-base font-bold text-white">{title}</h1>
      {badge ? (
        <div className="rounded-full border border-grao-green/20 bg-grao-green/10 px-2.5 py-1 text-[11px] font-bold text-grao-green">
          {badge}
        </div>
      ) : null}
    </div>
  );
}

function BarChart({ values, labels }: { values: number[]; labels: string[] }) {
  return (
    <>
      <div className="flex h-[60px] items-end gap-1">
        {values.map((height, index) => (
          <div
            key={`${height}-${index}`}
            className="origin-bottom animate-riseBar rounded-t bg-grao-green/40 transition-opacity hover:opacity-80"
            style={{ height: `${height}%`, flex: 1, animationDelay: `${100 + index * 40}ms` }}
          />
        ))}
      </div>
      <div className="mt-2 flex justify-between">
        {labels.map((label) => (
          <span key={label} className="text-[10px] text-grao-text3">{label}</span>
        ))}
      </div>
    </>
  );
}

function logoTone(tone: "blue" | "purple" | "green" | "gold" | "red") {
  return {
    blue: "border-grao-blue/20 bg-[linear-gradient(135deg,#1a3a6a,#0f2a4a)] text-grao-blue",
    purple: "border-violet-400/20 bg-[linear-gradient(135deg,#1a1040,#120d30)] text-violet-300",
    green: "border-grao-green/20 bg-[linear-gradient(135deg,#0a2a1a,#081e12)] text-grao-green",
    gold: "border-grao-gold/20 bg-[linear-gradient(135deg,#2a1a00,#1e1200)] text-grao-gold",
    red: "border-red-400/20 bg-[linear-gradient(135deg,#2a0a0a,#1e0808)] text-red-400",
  }[tone];
}
