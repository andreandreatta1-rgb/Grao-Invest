import { useState } from "react";
import type { Trade } from "../types";
import { StatPill } from "./StatPill";
import { StatusDot } from "./StatusDot";
import { StrategyBadge } from "./StrategyBadge";

type TradeCardProps = {
  trade: Trade;
};

export function TradeCard({ trade }: TradeCardProps) {
  const [pressed, setPressed] = useState(false);
  const isPositive = trade.resultPct >= 0;
  const sideColor = trade.direction === "up" ? "bg-grao-green shadow-[0_0_12px_rgba(0,212,170,0.5)]" : "bg-grao-red shadow-[0_0_12px_rgba(255,77,106,0.5)]";
  const resultTone = isPositive ? "text-grao-green2 text-glow-green" : "text-grao-red text-glow-red";
  const cardGlow = isPositive ? "shadow-greenGlow" : trade.status === "invalid" ? "shadow-redGlow" : "";
  const progressTone = trade.status === "invalid"
    ? "from-grao-red to-[#ff6b7a]"
    : trade.status === "warn" && trade.resultPct < 0
      ? "from-grao-gold to-[#f7d96a]"
      : "from-grao-green to-grao-green2";

  return (
    <article
      onClick={() => {
        setPressed(true);
        window.setTimeout(() => setPressed(false), 150);
      }}
      className={`group relative mb-3.5 cursor-pointer overflow-hidden rounded-[20px] border border-white/7 bg-gradient-to-br from-grao-card2 to-grao-card p-[18px] transition-all duration-200 hover:-translate-y-0.5 hover:border-white/12 hover:shadow-[0_12px_32px_rgba(0,0,0,0.3)] ${cardGlow} ${pressed ? "scale-[0.98]" : ""}`}
    >
      <span className={`absolute left-0 top-0 h-full w-[3px] rounded-r-sm ${sideColor}`} />

      <div className="mb-3.5 flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-grao-text3">#{trade.id}</span>
          <h3 className="text-xl font-extrabold tracking-[-0.03em] text-white">{trade.ticker}</h3>
          <div className="mt-0.5 flex items-center gap-1.5">
            <StatusDot status={trade.status} />
            <span
              className={`text-[11px] font-semibold ${
                trade.status === "invalid" ? "text-grao-red" : trade.status === "warn" ? "text-grao-gold" : "text-grao-blue"
              }`}
            >
              {trade.statusLabel}
            </span>
          </div>
        </div>

        <div className="text-right">
          <div className={`text-[22px] font-extrabold tracking-[-0.03em] ${resultTone}`}>
            {trade.resultPct > 0 ? "+" : ""}
            {trade.resultPct.toFixed(2).replace(".", ",")}%
          </div>
          <div className="mt-1 text-[10px] text-grao-text3">{trade.resultLabel}</div>
        </div>
      </div>

      <div className="mb-3.5 flex gap-2">
        {trade.pills.map((pill) => (
          <StatPill key={`${trade.id}-${pill.label}`} stat={pill} />
        ))}
      </div>

      <p className="mb-3 text-xs leading-normal text-grao-text2">{trade.description}</p>

      <div className="mt-2 flex items-center gap-2.5">
        <div className="h-1 flex-1 overflow-hidden rounded bg-white/[0.08]">
          <div
            className={`h-full rounded bg-gradient-to-r ${progressTone} transition-[width] duration-700 ease-out`}
            style={{ width: `${trade.progressPct}%` }}
          />
        </div>
        <span className="whitespace-nowrap text-[10px] text-grao-text3">{trade.progressLabel}</span>
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <StrategyBadge label={trade.strategy} tone={trade.strategyTone} />
        <div className="flex gap-2.5 text-[11px] text-grao-text3">
          <span>
            Max <strong className="font-semibold text-grao-green">{trade.maxGain}</strong>
          </span>
          <span>
            <strong className="font-semibold text-grao-red">{trade.riskLabel}</strong>
          </span>
        </div>
      </div>
    </article>
  );
}
