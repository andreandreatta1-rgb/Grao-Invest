import type { TradeStatus } from "../types";

type StatusDotProps = {
  status: TradeStatus;
};

const statusClass: Record<TradeStatus, string> = {
  open: "bg-grao-blue shadow-[0_0_6px_#4f8ef7]",
  warn: "animate-pulseStatus bg-grao-gold shadow-[0_0_6px_#f5c842]",
  invalid: "bg-grao-red shadow-[0_0_6px_#ff4d6a]",
};

export function StatusDot({ status }: StatusDotProps) {
  return <span className={`h-1.5 w-1.5 rounded-full ${statusClass[status]}`} />;
}
