import { monthlyBars, strategyReturns } from "../data/mockData";

export function AnalisarScreen() {
  return (
    <section className="content-screen">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-base font-bold text-white">Desempenho Geral</h1>
        <div className="rounded-full border border-grao-green/20 bg-grao-green/10 px-2.5 py-1 text-[11px] font-bold text-grao-green">
          Mai 2026
        </div>
      </div>

      <div className="mb-3.5 rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-5">
        <div className="mb-3.5 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold">Taxa de Acerto</h2>
            <div className="mt-0.5 text-xs text-grao-text3">últimas 30 teses</div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-extrabold text-grao-green2">68%</div>
            <div className="text-[11px] text-grao-text3">↑ +4pp mês</div>
          </div>
        </div>
        <div className="h-2 overflow-hidden rounded-lg bg-white/[0.08]">
          <div className="h-full w-[68%] rounded-lg bg-gradient-to-r from-grao-green to-grao-green2 transition-[width] duration-700" />
        </div>
        <div className="mt-3.5 flex gap-3">
          <MiniStat label="Ganhos" value="20" tone="up" />
          <MiniStat label="Perdas" value="7" tone="down" />
          <MiniStat label="Abertas" value="3" tone="neutral" />
        </div>
      </div>

      <div className="mb-3.5 rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-5">
        <h2 className="mb-3.5 text-sm font-bold">Retorno por Estratégia</h2>
        <div className="flex flex-col gap-2.5">
          {strategyReturns.map((strategy) => (
            <div key={strategy.label}>
              <div className="mb-1 flex justify-between">
                <span className="text-xs font-semibold">{strategy.label}</span>
                <span className="text-xs font-bold text-grao-green">{strategy.value}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-md bg-white/[0.08]">
                <div
                  className={`h-full rounded-md bg-gradient-to-r ${strategyTone(strategy.tone)}`}
                  style={{ width: `${strategy.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-3.5 rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-5">
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="text-sm font-bold">Evolução Mensal</h2>
          <span className="text-[13px] font-bold text-grao-green">2026</span>
        </div>
        <div className="flex h-[60px] items-end gap-1">
          {monthlyBars.map((height, index) => (
            <div
              key={`${height}-${index}`}
              className={`origin-bottom animate-riseBar rounded-t ${index === 2 ? "bg-gradient-to-b from-grao-red to-grao-red/30" : "bg-gradient-to-b from-grao-green2 to-grao-green/30"}`}
              style={{ height: `${height}%`, flex: 1, animationDelay: `${100 + index * 45}ms` }}
            />
          ))}
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-grao-text3">
          {['Jan', 'Fev', 'Mar', 'Abr', 'Mai'].map((month) => <span key={month}>{month}</span>)}
        </div>
      </div>
      <div className="h-5" />
    </section>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone: "up" | "down" | "neutral" }) {
  const toneClass = tone === "up" ? "text-grao-green2" : tone === "down" ? "text-grao-red" : "text-grao-text2";
  return (
    <div className="flex-1 rounded-[10px] bg-white/[0.03] p-2.5 text-center">
      <div className={`text-base font-extrabold ${toneClass}`}>{value}</div>
      <div className="mt-0.5 text-[10px] text-grao-text3">{label}</div>
    </div>
  );
}

function strategyTone(tone: "blue" | "purple" | "gold") {
  return {
    blue: "from-grao-blue to-[#7bb3ff]",
    purple: "from-violet-400 to-violet-300",
    gold: "from-grao-gold to-[#f7d96a]",
  }[tone];
}
