export type TradeDirection = "up" | "down";
export type TradeStatus = "open" | "warn" | "invalid";

export type StatPillData = {
  label: string;
  value: string;
  tone?: "default" | "green" | "date" | "red" | "gold";
};

export type Trade = {
  id: number | string;
  ticker: string;
  direction: TradeDirection;
  status: TradeStatus;
  statusLabel: string;
  resultPct: number;
  resultLabel: string;
  pills: StatPillData[];
  description: string;
  progressPct: number;
  progressLabel: string;
  strategy: string;
  strategyTone: "blue" | "purple" | "green";
  maxGain: string;
  riskLabel: string;
  link?: string;
};

export type MarketAsset = {
  ticker: string;
  name: string;
  price: string;
  changePct: number;
  logo: string;
  tone: "blue" | "purple" | "green" | "gold" | "red";
};

export type StrategyReturn = {
  label: string;
  value: string;
  pct: number;
  tone: "blue" | "purple" | "gold";
};
