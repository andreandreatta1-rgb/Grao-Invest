// Helpers de formatação consistentes (BR).

export const fmtPct = (v: number, digits = 2) =>
  `${v >= 0 ? "+" : ""}${(v).toFixed(digits)}%`;

export const fmtPctRatio = (v: number, digits = 1) =>
  `${(v * 100).toFixed(digits)}%`;

export const fmtMoney = (v: number, currency = "BRL") =>
  v.toLocaleString("pt-BR", { style: "currency", currency, maximumFractionDigits: 2 });

export const fmtNumber = (v: number, digits = 2) =>
  v.toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const fmtCompact = (v: number) =>
  v.toLocaleString("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

export function fmtRelative(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 5) return "agora";
  if (diff < 60) return `há ${Math.floor(diff)}s`;
  if (diff < 3600) return `há ${Math.floor(diff / 60)}min`;
  if (diff < 86400) return `há ${Math.floor(diff / 3600)}h`;
  return `há ${Math.floor(diff / 86400)}d`;
}

export function fmtCountdown(iso: string): string {
  const diff = Math.max(0, (new Date(iso).getTime() - Date.now()) / 1000);
  const m = Math.floor(diff / 60);
  const s = Math.floor(diff % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
