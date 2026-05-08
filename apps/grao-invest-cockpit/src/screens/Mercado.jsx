import { Badge, C, KPICard, ScreenHero, mono } from "../components";

const fallbackMarket = [
  { asset: "PETR4", front: "B3", price: 38.28, dayPct: 2.36, weekPct: 10.99, confidence: 97, status: "monitorando", activeTheses: 1, color: C.teal },
  { asset: "VALE3", front: "B3", price: 72.1, dayPct: 0.84, weekPct: 3.2, confidence: 82, status: "candidato", activeTheses: 0, color: C.purple },
  { asset: "MGLU3", front: "B3", price: 9.25, dayPct: -1.2, weekPct: 5.44, confidence: 64, status: "atenção", activeTheses: 2, color: C.amber },
  { asset: "WEGE3", front: "B3", price: 45.8, dayPct: 0.3, weekPct: 1.1, confidence: 55, status: "monitorando", activeTheses: 0, color: C.sky },
  { asset: "ITUB4", front: "B3", price: 33.4, dayPct: 0.6, weekPct: 2.8, confidence: 91, status: "monitorando", activeTheses: 0, color: C.teal },
  { asset: "BTCUSDT", front: "Cripto", price: 62400, dayPct: 2.24, weekPct: 7.37, confidence: 84, status: "monitorando", activeTheses: 1, color: C.teal },
  { asset: "ETHUSDT", front: "Cripto", price: 3200, dayPct: -0.8, weekPct: 2.1, confidence: 71, status: "atenção", activeTheses: 0, color: C.amber },
  { asset: "SOLUSDT", front: "Cripto", price: 145, dayPct: 4.1, weekPct: 5.4, confidence: 56, status: "candidato", activeTheses: 0, color: C.purple },
  { asset: "Galpão Campinas", front: "Imóveis", price: 850000, dayPct: 0, weekPct: 7.06, confidence: 78, status: "monitorando", activeTheses: 1, color: C.teal },
  { asset: "Sala SP", front: "Imóveis", price: 280000, dayPct: 0, weekPct: 1.2, confidence: 45, status: "monitorando", activeTheses: 0, color: C.sky },
  { asset: "Apart. RJ", front: "Imóveis", price: 650000, dayPct: 0, weekPct: 0.8, confidence: 52, status: "candidato", activeTheses: 0, color: C.purple },
];

const b3Confidence = {
  PETR4: 97,
  VALE3: 82,
  MGLU3: 64,
  WEGE3: 55,
  ITUB4: 91,
};

const cryptoConfidence = {
  BTCUSDT: 84,
  ETHUSDT: 71,
  SOLUSDT: 56,
};

function money(value) {
  if (value === null || value === undefined || value === "") return "R$ --";
  const number = Number(value);
  if (number >= 1000000) return `R$ ${(number / 1000000).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M`;
  if (number >= 100000) return `R$ ${(number / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}K`;
  return `R$ ${number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function pct(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--%";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function statusType(status) {
  if (status === "atenção") return "warning";
  if (status === "candidato") return "purple";
  return "open";
}

function confidenceColor(value) {
  if (value >= 85) return C.teal;
  if (value >= 70) return C.purple;
  if (value >= 55) return C.amber;
  return C.sky;
}

function normalizeAsset(asset) {
  const forcedB3Confidence = asset.front === "B3" ? b3Confidence[asset.asset] : undefined;
  const forcedCryptoConfidence = asset.front === "Cripto" ? cryptoConfidence[asset.asset] : undefined;
  const forcedConfidence = forcedB3Confidence ?? forcedCryptoConfidence;
  const confidence = Number(forcedConfidence ?? asset.confidence ?? asset.confidencePct ?? asset.patterns ?? 55);
  return {
    ...asset,
    confidence: Math.min(100, Math.max(0, Number.isFinite(confidence) ? confidence : 55)),
    color: forcedConfidence !== undefined ? confidenceColor(confidence) : asset.color || confidenceColor(confidence),
  };
}

function mergeAssets(realAssets) {
  const byKey = new Map();
  fallbackMarket.forEach((asset) => byKey.set(`${asset.front}-${asset.asset}`, normalizeAsset(asset)));
  (realAssets || []).forEach((asset) => {
    const normalized = normalizeAsset(asset);
    byKey.set(`${normalized.front}-${normalized.asset}`, normalized);
  });
  return Array.from(byKey.values());
}

function ConfidenceMeter({ value, color, assetName, compact = false }) {
  return (
    <div data-testid={assetName ? `confidence-meter-${assetName}` : undefined} style={{ minWidth: compact ? 0 : 170, width: compact ? "100%" : undefined }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ color: C.muted, fontSize: compact ? 8 : 9, fontFamily: mono, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>Confiança Halley</span>
        <span style={{ color, fontSize: 10, fontFamily: mono, fontWeight: 700, flexShrink: 0, marginLeft: 6 }}>{Math.round(value)}%</span>
      </div>
      <div style={{ background: C.faint, borderRadius: 99, height: 5, overflow: "hidden" }}>
        <div style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 99, transition: "width 0.7s cubic-bezier(.4,0,.2,1)" }} />
      </div>
    </div>
  );
}

function ThesisCountBadge({ asset }) {
  const hasThesis = asset.activeTheses > 0;
  const label = hasThesis ? `${asset.activeTheses} TESE${asset.activeTheses > 1 ? "S" : ""}` : "—";
  return (
    <span
      data-testid={`thesis-count-${asset.asset}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: hasThesis ? 58 : 36,
        whiteSpace: "nowrap",
      }}
    >
      <Badge label={label} type={hasThesis ? "info" : "neutral"} />
    </span>
  );
}

function CasinoRow({ asset, compact = false }) {
  const dayColor = asset.dayPct >= 0 ? C.teal : C.coral;
  const weekColor = asset.weekPct >= 0 ? C.teal : C.coral;

  if (compact) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "minmax(96px, 1.1fr) 78px 58px minmax(130px, 1.4fr) max-content max-content", gap: 8, alignItems: "center", padding: "9px 12px", borderBottom: `1px solid ${C.casinoBorder}` }}>
        <span style={{ color: C.text, fontWeight: 700, fontSize: 11 }}>{asset.asset}</span>
        <span style={{ color: C.text, fontFamily: mono, fontSize: 11 }}>{money(asset.price)}</span>
        <span style={{ color: dayColor, fontFamily: mono, fontSize: 11 }}>{pct(asset.dayPct)}</span>
        <ConfidenceMeter value={asset.confidence} color={asset.color} assetName={asset.asset} compact />
        <Badge label={asset.status} type={statusType(asset.status)} />
        <ThesisCountBadge asset={asset} />
      </div>
    );
  }

  return (
    <tr style={{ borderBottom: `1px solid ${C.casinoBorder}` }}>
      <td style={{ padding: "10px 12px", color: C.text, fontWeight: 700 }}>{asset.asset}</td>
      <td style={{ padding: "10px 12px", color: C.text, fontFamily: mono }}>{money(asset.price)}</td>
      <td style={{ padding: "10px 12px", color: dayColor, fontFamily: mono }}>{pct(asset.dayPct)}</td>
      <td style={{ padding: "10px 12px", color: weekColor, fontFamily: mono }}>{pct(asset.weekPct)}</td>
      <td style={{ padding: "10px 12px" }}><ConfidenceMeter value={asset.confidence} color={asset.color} assetName={asset.asset} /></td>
      <td style={{ padding: "10px 12px" }}><Badge label={asset.status} type={statusType(asset.status)} /></td>
      <td style={{ padding: "10px 12px" }}><ThesisCountBadge asset={asset} /></td>
    </tr>
  );
}

function CasinoTable({ title, subtitle, assets, compact = false }) {
  return (
    <section style={{ background: `linear-gradient(135deg, ${C.casinoA}, ${C.casinoB})`, border: `1px solid ${C.casinoBorder}`, borderRadius: 14, padding: 16, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 220, height: 160, background: `radial-gradient(ellipse at 90% 30%, ${C.amber}12, transparent 60%)`, pointerEvents: "none" }} />
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", marginBottom: 13, position: "relative", zIndex: 2 }}>
        <div>
          <div style={{ color: C.text, fontSize: 14, fontWeight: 700 }}>{title}</div>
          {subtitle && <div style={{ color: C.muted, fontSize: 11, marginTop: 3 }}>{subtitle}</div>}
        </div>
      </div>
      <div style={{ position: "relative", zIndex: 2, overflowX: "auto" }}>
        {compact ? (
          <div>{assets.map((asset) => <CasinoRow key={`${asset.front}-${asset.asset}`} asset={asset} compact />)}</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr style={{ background: C.casinoA }}>
                {["Ativo", "Preço", "Var. dia", "Var. semana", "Confiança Halley", "Status", "Uso"].map((h) => (
                  <th key={h} style={{ padding: "9px 12px", color: C.muted, fontWeight: 600, textAlign: "left", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: `1px solid ${C.casinoBorder}`, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>{assets.map((asset) => <CasinoRow key={`${asset.front}-${asset.asset}`} asset={asset} />)}</tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export default function Mercado({ data }) {
  const assets = mergeAssets(data?.marketAssets ?? []);
  const attentionCount = assets.filter((asset) => asset.status === "atenção").length;
  const candidateCount = assets.filter((asset) => asset.status === "candidato").length;
  const sourceCount = new Set(assets.map((asset) => asset.front)).size;
  const b3 = assets.filter((asset) => asset.front === "B3");
  const crypto = assets.filter((asset) => asset.front === "Cripto");
  const realEstate = assets.filter((asset) => asset.front === "Imóveis");

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 24, minHeight: 640, padding: "24px 28px 40px" }}>
      <p style={{ color: C.muted, fontSize: 12, lineHeight: 1.5, margin: 0 }}>Contexto que alimenta o motor: cobertura, variação, confiança e sinais de dados antes de virar tese.</p>

      <ScreenHero
        screen="mercado"
        state="observing"
        accent={C.green}
        message="Mercado é a leitura de contexto. A decisão mora em Teses; aqui eu confiro se a fonte sustenta a hipótese."
        insights={[
          { label: "Papel da frente", value: "Confirmar fonte, preço e variação antes da tese.", color: C.green },
          { label: "Quando vira ação", value: "Só migra para Teses quando o padrão resiste.", color: C.sky },
          { label: "Leitura rápida", value: `${assets.length} ativos em ${sourceCount} frentes cobertas.`, color: C.teal },
        ]}
      />

      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <KPICard label="Ativos cobertos" value={assets.length.toLocaleString("pt-BR")} sub="B3, Cripto e Imóveis" accent={C.sky} valueColor={C.text} />
        <KPICard label="Em zona de atenção" value={attentionCount.toLocaleString("pt-BR")} sub="padrão se formando" accent={C.amber} valueColor={C.amber} />
        <KPICard label="Sinais candidatos" value={candidateCount.toLocaleString("pt-BR")} sub="aguardam volume" accent={C.purple} valueColor={C.purple} />
        <KPICard label="Fontes em leitura" value={sourceCount.toLocaleString("pt-BR")} sub="frentes cobertas" accent={C.teal} valueColor={C.teal} />
      </section>

      <CasinoTable title="Mesa principal — B3" subtitle="Confiança Halley = força do padrão histórico para alimentar o contexto" assets={b3} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <CasinoTable title="Cripto — mesa adjacente" assets={crypto} compact />
        <CasinoTable title="Imóveis — sala reservada" assets={realEstate} compact />
      </div>
    </main>
  );
}
