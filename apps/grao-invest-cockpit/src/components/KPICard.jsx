import { C, alpha, mono, withAlpha } from "./tokens.js";

export function KPICard({ label, value, sub, valueColor, accent, icon, valueFontSize = 26 }) {
  const cardAccent = accent || C.border;

  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderTop: `2px solid ${cardAccent}`,
        borderRadius: 14,
        padding: "18px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minWidth: 0,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: 80,
          height: 80,
          pointerEvents: "none",
          background: `radial-gradient(circle at top right, ${withAlpha(cardAccent, alpha.glow)}, transparent 70%)`,
          borderRadius: "0 14px 0 0",
        }}
      />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 2,
        }}
      >
        {icon && <span style={{ fontSize: 13 }}>{icon}</span>}
        <span
          style={{
            color: C.muted,
            fontSize: 10,
            textTransform: "uppercase",
            letterSpacing: "0.1em",
          }}
        >
          {label}
        </span>
      </div>
      <span
        style={{
          color: valueColor || C.text,
          fontSize: valueFontSize,
          fontWeight: 700,
          fontFamily: mono,
          letterSpacing: "-0.02em",
          lineHeight: 1,
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </span>
      {sub && (
        <span style={{ color: C.muted, fontSize: 11, marginTop: 2 }}>{sub}</span>
      )}
    </div>
  );
}

export default KPICard;
