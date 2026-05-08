import { C } from "./tokens.js";

function row(label, value, color) {
  return (
    <div
      key={label}
      style={{
        background: C.panel,
        border: `1px solid ${C.border}`,
        borderRadius: 10,
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 5,
      }}
    >
      <span
        style={{
          color,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
      <span style={{ color: C.text, fontSize: 12, lineHeight: 1.5 }}>
        {value}
      </span>
    </div>
  );
}

export function LearningLoopCard({ loop, pain, remedy, impact }) {
  const painValue = loop?.pain ?? pain;
  const remedyValue = loop?.remedy ?? remedy;
  const impactValue = loop?.expectedImpact ?? impact;

  return (
    <section
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderTop: `2px solid ${C.gold}`,
        borderRadius: 14,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {row("Dor observada", painValue, C.coral)}
      {row("Remédio aplicado", remedyValue, C.teal)}
      {row("Impacto esperado", impactValue, C.sky)}
    </section>
  );
}

export default LearningLoopCard;
