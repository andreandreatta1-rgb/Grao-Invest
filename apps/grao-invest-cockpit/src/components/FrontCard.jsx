import { C, mono } from "./tokens.js";
import { fmtDate, fmtInteger, fmtPct } from "../utils/formatters.js";
import Badge from "./Badge.jsx";
import KPICard from "./KPICard.jsx";
import ProgressBar from "./ProgressBar.jsx";

const frontStyles = {
  B3: { accent: C.teal, type: "bull" },
  Cripto: { accent: C.gold, type: "high" },
  Imoveis: { accent: C.sky, type: "info" },
};

function normalizeFrontLabel(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function FrontCard({
  front,
  tested,
  goLive,
  validatedPct,
  status = "atualizado",
}) {
  const frontData = typeof front === "object" && front !== null ? front : {};
  const frontLabel = frontData.label || front;
  const normalizedFrontLabel = normalizeFrontLabel(frontLabel);
  const testedValue = frontData.tested ?? tested;
  const resolvedCountValue = frontData.resolvedCount ?? frontData.resolved_count ?? testedValue ?? null;
  const mappedCountValue = frontData.mappedCount ?? frontData.mapped_count ?? null;
  const radarTotalValue = frontData.radarTotal ?? frontData.radar_total ?? mappedCountValue ?? testedValue;
  const openCountValue = frontData.openCount ?? frontData.open_count ?? frontData.goLive ?? goLive;
  const closedCountValue = frontData.closedCount ?? frontData.closed_count ?? resolvedCountValue;
  const countingPolicy = frontData.countingPolicy ?? frontData.counting_policy ?? null;
  const goLiveValue = frontData.goLive ?? goLive;
  const activeAssetsValue = frontData.activeAssets ?? frontData.activeAssetCount ?? null;
  const validatedValue = frontData.validatedPct ?? validatedPct;
  const statusValue = frontData.status ?? status;
  const lastUpdatedAt = frontData.lastUpdatedAt;
  const style = frontStyles[normalizedFrontLabel] || { accent: C.muted, type: "neutral" };
  const isRealEstate = ["real_estate", "real-estate"].includes(frontData.id) || normalizedFrontLabel === "Imoveis";
  const isCrypto = frontData.id === "crypto" || normalizedFrontLabel === "Cripto";
  const showMappedCrypto = isCrypto
    && countingPolicy === "resolved_historical"
    && mappedCountValue !== null
    && resolvedCountValue !== null
    && mappedCountValue > resolvedCountValue;
  const testedLabel = isRealEstate ? "No radar" : showMappedCrypto ? "Mapeadas" : "Testadas";
  const testedSub = isRealEstate
    ? "candidatos canonicos"
    : showMappedCrypto
      ? `${fmtInteger(resolvedCountValue)} resolvidas no histórico`
      : "amostra validada";
  const testedDisplayValue = isRealEstate ? radarTotalValue : showMappedCrypto ? mappedCountValue : testedValue;
  const activeLabel = isRealEstate ? "Abertos" : "Planos ativos";
  const activeSub = isRealEstate
    ? "fila operacional"
    : activeAssetsValue !== null
      ? `${fmtInteger(activeAssetsValue)} ativos cobertos`
      : "hipoteses abertas";
  const activeDisplayValue = isRealEstate ? openCountValue : goLiveValue;
  const thirdLabel = isRealEstate ? "Encerrados" : "Validadas";
  const thirdValue = isRealEstate ? fmtInteger(closedCountValue) : fmtPct(validatedValue);
  const thirdSub = isRealEstate ? "aprendizados fora da fila" : "taxa historica";
  const realEstateProgress = radarTotalValue
    ? Math.min(100, Math.max(0, (Number(openCountValue || 0) / Number(radarTotalValue)) * 100))
    : 0;

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
        <KPICard label={testedLabel} value={fmtInteger(testedDisplayValue)} sub={testedSub} accent={C.sky} valueFontSize={13} />
        <KPICard label={activeLabel} value={fmtInteger(activeDisplayValue)} sub={activeSub} accent={C.teal} valueFontSize={13} />
        <KPICard
          label={thirdLabel}
          value={thirdValue}
          sub={thirdSub}
          valueColor={style.accent}
          accent={style.accent}
          valueFontSize={13}
        />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {isRealEstate ? (
          <>
            <div
              data-testid={`front-radar-${frontLabel}`}
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
              <span>{"Contrato do radar"}</span>
              <span>{" · "}</span>
              <span style={{ color: style.accent, fontFamily: mono }}>
                {fmtInteger(radarTotalValue)} = {fmtInteger(openCountValue)} abertos + {fmtInteger(closedCountValue)} encerrados
              </span>
            </div>
            <ProgressBar progress={realEstateProgress} color={style.accent} />
          </>
        ) : (
          <>
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
          </>
        )}
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
