export const C = Object.freeze({
  bg: "#070b14",
  panel: "#0c1120",
  card: "#101828",
  border: "#1a2540",
  hover: "#141f35",
  line: "#1e2d4a",
  faint: "#0d1630",
  gold: "#c8a444",
  goldLight: "#e8c870",
  goldDim: "#8a6e2c",
  teal: "#00c896",
  tealDim: "#006b50",
  coral: "#ff5e5e",
  coralDim: "#7a2020",
  amber: "#f5a623",
  amberDim: "#7a4e05",
  green: "#22c55e",
  greenDim: "#14532d",
  sky: "#3b9eff",
  skyDim: "#1a4d8c",
  purple: "#a78bfa",
  text: "#e2eaf8",
  muted: "#5a7090",
  dim: "#2e4060",
  casinoA: "#08180e",
  casinoB: "#051008",
  casinoBorder: "#163022",
});

export const mono = "'JetBrains Mono', 'Fira Code', monospace";

export const fmt = (v, decimals = 2) => {
  const n = parseFloat(v);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(decimals)}%`;
};

export const alpha = Object.freeze({
  subtle: "20",
  border: "40",
  strong: "60",
  glow: "18",
});

export function withAlpha(color, alphaValue) {
  return `${color}${alphaValue}`;
}
