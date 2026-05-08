import { BadgeAlert, BadgeCheck, BadgeX } from "lucide-react";
import { C, alpha, withAlpha } from "./tokens.js";

const statusConfig = Object.freeze({
  validated: {
    Icon: BadgeCheck,
    color: C.teal,
    background: withAlpha(C.teal, alpha.glow),
    border: withAlpha(C.teal, alpha.border),
  },
  partial: {
    Icon: BadgeAlert,
    color: C.amber,
    background: withAlpha(C.amber, alpha.glow),
    border: withAlpha(C.amber, alpha.border),
  },
  degraded: {
    Icon: BadgeX,
    color: C.coral,
    background: withAlpha(C.coral, alpha.glow),
    border: withAlpha(C.coral, alpha.border),
  },
});

export function DataTrustSeal({ trust, screen = "dados", size = 30 }) {
  const normalized = trust?.status ? trust : { status: "partial", label: "Dados parciais", issues: [] };
  const config = statusConfig[normalized.status] ?? statusConfig.partial;
  const Icon = config.Icon;
  const title = normalized.issues?.length
    ? `${normalized.label}: ${normalized.issues.length} ponto(s) de validação`
    : normalized.label;

  return (
    <span
      role="img"
      aria-label={normalized.label}
      data-testid={`data-trust-seal-${screen}`}
      title={title}
      style={{
        alignItems: "center",
        background: config.background,
        border: `1px solid ${config.border}`,
        borderRadius: "50%",
        color: config.color,
        display: "inline-flex",
        flex: "0 0 auto",
        height: size,
        justifyContent: "center",
        width: size,
      }}
    >
      <Icon aria-hidden="true" size={Math.max(16, size - 12)} strokeWidth={2.2} />
    </span>
  );
}

export default DataTrustSeal;
