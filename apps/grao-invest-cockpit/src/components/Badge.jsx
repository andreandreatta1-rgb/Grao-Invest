import { C, alpha, mono, withAlpha } from "./tokens.js";

const styles = {
  open: { bg: withAlpha(C.teal, alpha.subtle), color: C.teal, border: withAlpha(C.teal, alpha.border) },
  closed: { bg: withAlpha(C.muted, alpha.subtle), color: C.muted, border: withAlpha(C.muted, alpha.border) },
  warning: { bg: withAlpha(C.amber, alpha.subtle), color: C.amber, border: withAlpha(C.amber, alpha.border) },
  success: { bg: withAlpha(C.green, alpha.subtle), color: C.green, border: withAlpha(C.green, alpha.border) },
  danger: { bg: withAlpha(C.coral, alpha.subtle), color: C.coral, border: withAlpha(C.coral, alpha.border) },
  neutral: { bg: withAlpha(C.dim, alpha.strong), color: C.muted, border: C.dim },
  high: { bg: withAlpha(C.gold, alpha.subtle), color: C.gold, border: withAlpha(C.gold, alpha.border) },
  bull: { bg: withAlpha(C.teal, alpha.subtle), color: C.teal, border: withAlpha(C.teal, alpha.border) },
  bear: { bg: withAlpha(C.coral, alpha.subtle), color: C.coral, border: withAlpha(C.coral, alpha.border) },
  info: { bg: withAlpha(C.sky, alpha.subtle), color: C.sky, border: withAlpha(C.sky, alpha.border) },
  purple: { bg: withAlpha(C.purple, alpha.subtle), color: C.purple, border: withAlpha(C.purple, alpha.border) },
};

export function Badge({ label, type = "neutral" }) {
  const s = styles[type] || styles.neutral;

  return (
    <span
      style={{
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        fontSize: 10,
        fontWeight: 700,
        padding: "2px 8px",
        borderRadius: 6,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        fontFamily: mono,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}

export default Badge;
