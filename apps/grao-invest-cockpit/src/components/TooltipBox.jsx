import { C, mono } from "./tokens.js";

export function TooltipBox({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div
      style={{
        background: C.panel,
        border: `1px solid ${C.border}`,
        borderRadius: 10,
        padding: "10px 14px",
        fontSize: 12,
      }}
    >
      {label && <p style={{ color: C.muted, margin: "0 0 6px" }}>{label}</p>}
      {payload.map((p, i) => (
        <p
          key={`${p.name || "serie"}-${i}`}
          style={{
            color: p.color || C.gold,
            margin: "2px 0",
            fontWeight: 600,
            fontFamily: typeof p.value === "number" ? mono : "inherit",
          }}
        >
          {p.name ? `${p.name}: ` : ""}
          {typeof p.value === "number" ? p.value.toLocaleString("pt-BR") : p.value}
        </p>
      ))}
    </div>
  );
}

export default TooltipBox;
