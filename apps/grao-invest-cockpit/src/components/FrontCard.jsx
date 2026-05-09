import { C, mono } from "./tokens.js";
import { fmtDate, fmtInteger, fmtPct } from "../utils/formatters.js";
import Badge from "./Badge.jsx";
import KPICard from "./KPICard.jsx";
import ProgressBar from "./ProgressBar.jsx";

const frontStyles = {
  B3: { accent: C.teal, type: "bull" },
  Cripto: { accent: C.gold, type: "high" },
  Imóveis: { accent: C.sky, type: "info" },
};

export function FrontCard({
  front,
  tested,
  goLive,
  validatedPct,
  status = "atualizado",
}) {
  const frontData = typeof front === "object" && front !== null ? front : {};
  const frontLabel = frontData.label || front;
  const testedValue = frontData.tested ?? tested;
  const goLiveValue = frontData.goLive ?? goLive;
  const activeAssetsValue = frontData.activeAssets ?? frontData.activeAssetCount ?? null;
  const validatedValue = frontData.validatedPct ?? validatedPct;
  const statusValue = frontData.status ?? status;
  const lastUpdatedAt = frontData.lastUpdatedAt;
  const style = frontStyles[frontLabel] || { accent: C.muted, type: "neutral" };
  const isRealEstate = ["real_estate", "real-estate"].includes(frontData.id) || frontLabel === "Imóveis";
  const testedLabel = isRealEstate ? "Avaliadas" : "Testadas";
  const testedSub = isRealEstate ? "radar imobiliário" : "amostra validada";
  const activeLabel = isRealEstate ? "No radar" : "Planos ativos";
  const activeSub = isRealEstate
    ? "candidatos imobiliários"
    : activeAssetsValue !== null
      ? `${fmtInteger(activeAssetsValue)} ativos cobertos`
      : "hipóteses abertas";

  return (
    <article
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderTop: `2px solid ${style.accent}`,
        borderRadius: 14,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <h2 style={{ color: C.text, fontSize: 15, fontWeight: 700, margin: 0 }}>
          {frontLabel}
        </h2>
        <Badge label={statusValue} type={style.type} />
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 8,
        }}
      >
        <KPICard label={testedLabel} value={fmtInteger(testedValue)} sub={testedSub} accent={C.sky} valueFontSize={13} />
        <KPICard label={activeLabel} value={fmtInteger(goLiveValue)} sub={activeSub} accent={C.teal} valueFontSize={13} />
        <KPICard
          label="Validadas"
          value={fmtPct(validatedValue)}
          sub="taxa histórica"
          valueColor={style.accent}
          accent={style.accent}
          valueFontSize={13}
        />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        <div
          data-testid={`front-validation-${frontLabel}`}
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 10,
            color: C.muted,
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          <span>{"Validação da frente"}</span>
          <span>{" · "}</span>
          <span style={{ color: style.accent, fontFamily: mono }}>taxa {fmtPct(validatedValue)}</span>
        </div>
        <ProgressBar progress={validatedValue} color={style.accent} />
        {lastUpdatedAt && (
          <div
            data-testid={`front-update-${frontLabel}`}
            style={{ color: C.muted, fontSize: 10, lineHeight: 1.4 }}
          >
            Base atualizada em {fmtDate(lastUpdatedAt)}
          </div>
        )}
      </div>
    </article>
  );
}

export default FrontCard;
