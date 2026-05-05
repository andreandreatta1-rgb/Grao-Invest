import type { MarketAsset, StrategyReturn, Trade } from "../types";

export const trades: Trade[] = [
  {
    id: 1595,
    ticker: "B3SA3",
    direction: "down",
    status: "invalid",
    statusLabel: "Aberta · Invalidada",
    resultPct: -2.3,
    resultLabel: "vs entrada",
    pills: [
      { label: "Entrada", value: "R$ 17,04" },
      { label: "Esperado", value: "+0,66%", tone: "green" },
      { label: "Data", value: "30/03/26", tone: "date" },
    ],
    description:
      "Venda até 2026-04-22. Plano: capturar queda de 17,04 em direção a 16,64. Monitorar suporte técnico.",
    progressPct: 44,
    progressLabel: "44% da meta",
    strategy: "Bear Put Spread",
    strategyTone: "blue",
    maxGain: "+5,20%",
    riskLabel: "Perda lim.",
  },
  {
    id: 1594,
    ticker: "SUZB3",
    direction: "up",
    status: "warn",
    statusLabel: "Aberta · Atenção",
    resultPct: -1.35,
    resultLabel: "vs entrada",
    pills: [
      { label: "Entrada", value: "R$ 48,51" },
      { label: "Esperado", value: "+2,34%", tone: "green" },
      { label: "Data", value: "14/04/26", tone: "date" },
    ],
    description:
      "Compra até 2026-04-20. Plano: buscar alta de 48,51 para perto de 51,35. Se cair abaixo de 47,80, revisar.",
    progressPct: 20,
    progressLabel: "20% da meta",
    strategy: "Bull Call Spread",
    strategyTone: "purple",
    maxGain: "+5,40%",
    riskLabel: "Perda lim.",
  },
  {
    id: 1593,
    ticker: "BPAC11",
    direction: "up",
    status: "warn",
    statusLabel: "Aberta · Atenção",
    resultPct: 1.07,
    resultLabel: "vs entrada",
    pills: [
      { label: "Entrada", value: "R$ 63,25" },
      { label: "Esperado", value: "+3,15%", tone: "green" },
      { label: "Data", value: "14/04/26", tone: "date" },
    ],
    description:
      "Compra visando alta para R$ 65,24. Momentum positivo. Suporte em 62,80 deve ser mantido.",
    progressPct: 34,
    progressLabel: "34% da meta",
    strategy: "Compra Direta",
    strategyTone: "green",
    maxGain: "+6,80%",
    riskLabel: "Stop -2%",
  },
];

export const marketAssets: MarketAsset[] = [
  { ticker: "B3SA3", name: "B3 S.A. Brasil Bolsa Balcão", price: "R$ 16,65", changePct: -2.3, logo: "B3", tone: "blue" },
  { ticker: "SUZB3", name: "Suzano S.A.", price: "R$ 47,86", changePct: -1.35, logo: "SZ", tone: "purple" },
  { ticker: "BPAC11", name: "BTG Pactual", price: "R$ 63,93", changePct: 1.07, logo: "BP", tone: "green" },
  { ticker: "PETR4", name: "Petróleo Brasileiro", price: "R$ 38,42", changePct: 0.53, logo: "PT", tone: "gold" },
  { ticker: "VALE3", name: "Vale S.A.", price: "R$ 62,15", changePct: -0.88, logo: "VL", tone: "red" },
];

export const strategyReturns: StrategyReturn[] = [
  { label: "Bull Call Spread", value: "+8,4%", pct: 84, tone: "blue" },
  { label: "Bear Put Spread", value: "+3,1%", pct: 31, tone: "purple" },
  { label: "Compra Direta", value: "+1,2%", pct: 12, tone: "gold" },
];

export const intradayBars = [30, 45, 35, 60, 50, 75, 65, 80, 70, 90, 85, 95];
export const monthlyBars = [55, 72, 48, 85, 60];
