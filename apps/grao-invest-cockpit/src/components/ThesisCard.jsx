import { useState } from "react";
import { C, mono } from "./tokens.js";
import { fmtDate, fmtDays, fmtInteger, fmtMoney, fmtPct } from "../utils/formatters.js";
import Badge from "./Badge.jsx";

const statusMap = {
  monitoring: { label: "Observando", type: "info" },
  near_target: { label: "Confirmando", type: "open" },
  target_hit: { label: "Validada", type: "success" },
  stop_alert: { label: "Alerta", type: "warning" },
  invalidated: { label: "Refutada", type: "danger" },
  closed: { label: "Fechada", type: "closed" },
};

function directionType(direction) {
  if (direction === "Alta") return "bull";
  if (direction === "Baixa") return "bear";
  if (direction === "Revisar") return "warning";
  if (direction === "Descartada") return "danger";
  if (direction === "Encerrada") return "closed";
  return "info";
}

function metric(label, value, color = C.text) {
  return (
    <div
      key={label}
      style={{
        background: C.panel,
        borderRadius: 8,
        padding: "8px 10px",
        minWidth: 0,
      }}
    >
      <div
        style={{
          color: C.muted,
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: 3,
        }}
      >
        {label}
      </div>
      <div
        style={{
          color,
          fontSize: 13,
          fontWeight: 700,
          fontFamily: mono,
          minWidth: 0,
          overflowWrap: "anywhere",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function summaryLine(label, value, color = C.text) {
  return (
    <div
      key={label}
      style={{
        display: "grid",
        gridTemplateColumns: "58px minmax(0, 1fr)",
        gap: 8,
        alignItems: "baseline",
        minWidth: 0,
      }}
    >
      <span
        style={{
          color: C.muted,
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
      <span
        style={{
          color,
          fontSize: 11,
          lineHeight: 1.45,
          minWidth: 0,
          overflowWrap: "anywhere",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function isRangeThesis(thesis) {
  const text = [
    thesis.direction,
    thesis.id,
    thesis.thesisId,
    thesis.operation,
    thesis.hypothesis,
  ].join(" ").toLowerCase();
  return text.includes("neutra") || text.includes("range") || text.includes("iron condor");
}

function priceReferenceLabel(thesis) {
  return thesis.priceReferenceLabel || (isRangeThesis(thesis) ? "Faixa" : "Alvo");
}

function rangeText(thesis) {
  const lower = thesis.rangeLowerPrice ?? thesis.stopPrice;
  const upper = thesis.rangeUpperPrice;
  if (lower !== null && lower !== undefined && upper !== null && upper !== undefined) {
    return `${fmtMoney(lower)} - ${fmtMoney(upper)}`;
  }
  return "em torno do centro";
}

function priceMetrics(thesis) {
  if (isRangeThesis(thesis)) {
    return [
      metric("Entrada/Centro", fmtMoney(thesis.entryPrice)),
      metric(priceReferenceLabel(thesis), rangeText(thesis), C.green),
      metric("Quebra", "fora da faixa", C.coral),
    ];
  }

  return [
    metric("Entrada", fmtMoney(thesis.entryPrice)),
    metric(priceReferenceLabel(thesis), fmtMoney(thesis.targetPrice), C.green),
    metric("Stop", fmtMoney(thesis.stopPrice), C.coral),
  ];
}

function holdingPeriodLabel(thesis) {
  const hours = Number(thesis.hoursOpen);
  if (thesis.front === "Cripto" && Number.isFinite(hours) && hours < 48) {
    return `${fmtInteger(Math.max(1, Math.round(hours)))} h`;
  }
  return fmtDays(thesis.daysOpen);
}

export function ThesisCard({ thesis }) {
  const [expanded, setExpanded] = useState(false);
  const status = statusMap[thesis.status] || statusMap.monitoring;
  const momentumColor = thesis.currentPct >= 0 ? C.teal : C.coral;
  const accessibleName = `Tese ${thesis.id} ${thesis.asset}`;
  const coverageNotes = Array.isArray(thesis.coverageNotes) ? thesis.coverageNotes.filter(Boolean) : [];

  return (
    <article
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderLeft: `3px solid ${momentumColor}`,
        borderRadius: 12,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        minWidth: 0,
      }}
    >
      <button
        type="button"
        aria-expanded={expanded}
        aria-label={`${accessibleName} ${expanded ? "recolher" : "expandir"}`}
        onClick={() => setExpanded((current) => !current)}
        style={{
          background: C.card,
          border: 0,
          color: C.text,
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          minWidth: 0,
          overflowWrap: "anywhere",
          padding: 16,
          textAlign: "left",
        }}
      >
        <div
          data-testid={`thesis-card-header-${thesis.id}`}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "nowrap",
            gap: 12,
            minWidth: 0,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              flexWrap: "nowrap",
              gap: 8,
              minWidth: 0,
              flex: 1,
            }}
          >
            <span style={{ color: C.muted, fontSize: 10, fontFamily: mono }}>
              #{thesis.id}
            </span>
            <span
              data-testid={`thesis-card-asset-${thesis.id}`}
              style={{
                color: C.text,
                fontSize: 15,
                fontWeight: 700,
                maxWidth: 130,
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {thesis.asset}
            </span>
            <Badge label={thesis.direction} type={directionType(thesis.direction)} />
          </div>
          <span style={{ flexShrink: 0 }}>
            <Badge label={status.label} type={status.type} />
          </span>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(92px, 1fr))",
            gap: 8,
            minWidth: 0,
          }}
        >
          {priceMetrics(thesis)}
          {metric("Momento", fmtPct(thesis.currentPct), momentumColor)}
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            alignItems: "center",
            minWidth: 0,
          }}
        >
          <Badge label={`Potencial ${fmtPct(thesis.expectedPct)}`} type="info" />
          <span style={{ color: C.muted, fontSize: 10 }}>
            Aberta em {fmtDate(thesis.openedAt)}
          </span>
          <span style={{ color: C.muted, fontSize: 10, marginLeft: "auto" }}>
            {holdingPeriodLabel(thesis)}
          </span>
        </div>
        {coverageNotes.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              minWidth: 0,
            }}
          >
            {coverageNotes.map((note) => (
              <span
                key={note}
                style={{
                  background: C.panel,
                  border: `1px solid ${C.line}`,
                  borderRadius: 7,
                  color: C.muted,
                  fontSize: 10,
                  lineHeight: 1.35,
                  minWidth: 0,
                  overflowWrap: "anywhere",
                  padding: "5px 7px",
                }}
              >
                {note}
              </span>
            ))}
          </div>
        )}
        <div
          style={{
            background: C.panel,
            borderRadius: 8,
            display: "flex",
            flexDirection: "column",
            gap: 6,
            minWidth: 0,
            overflowWrap: "anywhere",
            padding: "9px 10px",
          }}
        >
          {summaryLine("Motivo", thesis.hypothesis)}
          {summaryLine("Operação", thesis.operation, C.sky)}
          {summaryLine("Saída", thesis.invalidation, C.amber)}
        </div>
      </button>
      {expanded && (
        <div
          data-testid="thesis-expanded-details"
          style={{
            borderTop: `1px solid ${C.border}`,
            display: "flex",
            flexDirection: "column",
            gap: 10,
            minWidth: 0,
            overflowWrap: "anywhere",
            padding: "0 16px 16px",
          }}
        >
          <p
            style={{
              color: C.text,
              fontSize: 12,
              lineHeight: 1.55,
              margin: 0,
              minWidth: 0,
              overflowWrap: "anywhere",
            }}
          >
            {thesis.hypothesis}
          </p>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              minWidth: 0,
            }}
          >
            {thesis.evidence?.map((item) => (
              <span
                key={item}
                style={{
                  color: C.muted,
                  fontSize: 11,
                  minWidth: 0,
                  overflowWrap: "anywhere",
                }}
              >
                {item}
              </span>
            ))}
          </div>
          <div
            style={{
              background: C.panel,
              borderRadius: 8,
              padding: "10px 12px",
              display: "flex",
              flexDirection: "column",
              gap: 6,
              minWidth: 0,
              overflowWrap: "anywhere",
            }}
          >
            <span
              style={{
                color: C.sky,
                fontSize: 12,
                fontWeight: 600,
                minWidth: 0,
                overflowWrap: "anywhere",
              }}
            >
              {thesis.operation}
            </span>
            <span style={{ color: C.muted, fontSize: 11 }}>
              Aberta em {fmtDate(thesis.openedAt)}
            </span>
            <span
              style={{
                color: C.amber,
                fontSize: 11,
                minWidth: 0,
                overflowWrap: "anywhere",
              }}
            >
              {thesis.invalidation}
            </span>
          </div>
          <p
            style={{
              color: C.green,
              fontSize: 12,
              lineHeight: 1.5,
              margin: 0,
              minWidth: 0,
              overflowWrap: "anywhere",
            }}
          >
            {thesis.learning}
          </p>
        </div>
      )}
    </article>
  );
}

export default ThesisCard;
