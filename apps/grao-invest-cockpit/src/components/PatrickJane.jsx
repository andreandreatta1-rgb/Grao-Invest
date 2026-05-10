import { C, mono } from "./tokens.js";

const STATE_CONFIG = {
  reporting: { label: "Reportando", color: C.gold },
  observing: { label: "Observando", color: C.sky },
  testing: { label: "Testando", color: C.purple },
  alerting: { label: "Alertando", color: C.coral },
  celebrating: { label: "Celebrando", color: C.green },
};

const IMG_MAP = {
  dashboard: "/assets/metodo/01.webp",
  teses: "/assets/metodo/02.webp",
  mercado: "/assets/metodo/03.webp",
  backtest: "/assets/metodo/04.webp",
  risco: "/assets/metodo/05.webp",
  alertas: "/assets/metodo/06.webp",
  aprendizado: "/assets/metodo/07.webp",
  metodo: "/assets/metodo/08.webp",
  saude: "/assets/metodo/09.webp",
};

const METHOD_STEPS = ["Observar", "Formular", "Testar", "Provar", "Aprender"];

function PatrickJaneImage({
  color,
  screen = "dashboard",
  imageHeight = 108,
  imageWidth = "auto",
  imageBorderColor,
  imageStyle = {},
  hero = false,
}) {
  const src = IMG_MAP[screen] || IMG_MAP.dashboard;
  const { visualMaxWidth = 520, ...cleanImageStyle } = imageStyle;
  const isPriorityImage = hero || Number(imageHeight) >= 140;
  const resolvedImageStyle = hero
      ? {
        ...cleanImageStyle,
        width: "100%",
        height: "100%",
        minHeight: "100%",
        maxHeight: "none",
        objectFit: cleanImageStyle.objectFit === "cover" ? "contain" : cleanImageStyle.objectFit || "contain",
        objectPosition: cleanImageStyle.objectPosition || "center center",
      }
    : {
      width: imageWidth,
      height: imageHeight,
      objectFit: cleanImageStyle.objectFit || "cover",
      objectPosition: cleanImageStyle.objectPosition || "top center",
      ...cleanImageStyle,
    };
  const img = (
    <img
      src={src}
      alt="Patrick Jane"
      decoding="async"
      fetchpriority={isPriorityImage ? "high" : "auto"}
      loading={isPriorityImage ? "eager" : "lazy"}
      style={{
        width: resolvedImageStyle.width,
        height: resolvedImageStyle.height,
        flexShrink: 0,
        borderRadius: hero ? 14 : 12,
        objectFit: resolvedImageStyle.objectFit,
        objectPosition: resolvedImageStyle.objectPosition,
        border: `2px solid ${imageBorderColor || color}`,
        background: color + "12",
        boxShadow: hero ? `0 18px 42px ${color}18` : undefined,
        ...resolvedImageStyle,
      }}
    />
  );

  if (hero) {
    return (
      <div
        data-testid="patrick-jane-visual"
        style={{
          aspectRatio: "16 / 9",
          justifySelf: "start",
          maxWidth: visualMaxWidth,
          minWidth: 220,
          width: "100%",
          overflow: "hidden",
          borderRadius: 14,
          background: color + "0f",
        }}
      >
        {img}
      </div>
    );
  }

  return img;
}

export function PatrickJane({
  state = "reporting",
  message = "",
  insights = [],
  size = "md",
  screen = "dashboard",
  compact = false,
  hero = false,
  imageHeight,
  imageWidth,
  imageBorderColor,
  imageStyle = {},
  portraitOnly = false,
  contentStyle = {},
  style = {},
  onClick,
}) {
  const cfg = STATE_CONFIG[state] || STATE_CONFIG.reporting;
  const { label, color } = cfg;
  const isCompact = compact || size === "sm";
  const resolvedImageHeight = imageHeight || (hero ? 176 : isCompact ? 90 : 108);
  const resolvedImageWidth = imageWidth || (hero ? "100%" : "auto");
  const heroInsights = Array.isArray(insights) ? insights.filter(Boolean) : [];
  const useDecisionPanel = hero && heroInsights.length > 0;

  if (portraitOnly) {
    return (
      <PatrickJaneImage
        color={color}
        screen={screen}
        imageHeight={resolvedImageHeight}
        imageWidth={resolvedImageWidth}
        imageBorderColor={imageBorderColor}
        imageStyle={imageStyle}
        hero={hero}
      />
    );
  }

  return (
    <div
      onClick={onClick}
      style={{
        display: hero ? "grid" : "flex",
        gridTemplateColumns: hero ? "minmax(220px, 0.82fr) minmax(0, 1fr)" : undefined,
        alignItems: hero ? "stretch" : "center",
        gap: hero ? 18 : isCompact ? 10 : 14,
        minWidth: 0,
        cursor: onClick ? "pointer" : "default",
        ...style,
      }}
    >
      <PatrickJaneImage
        color={color}
        screen={screen}
        imageHeight={resolvedImageHeight}
        imageWidth={resolvedImageWidth}
        imageBorderColor={imageBorderColor}
        imageStyle={imageStyle}
        hero={hero}
      />
      <div
        style={{
          alignSelf: hero ? "stretch" : undefined,
          display: hero ? "flex" : undefined,
          flexDirection: hero ? "column" : undefined,
          justifyContent: hero ? "center" : undefined,
          minWidth: 0,
          ...contentStyle,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexWrap: "wrap",
            marginBottom: 4,
          }}
        >
          <span style={{ color: C.text, fontSize: isCompact ? 12 : 13, fontWeight: 700 }}>
            Patrick Jane
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: color + "15",
              color,
              border: `1px solid ${color + "35"}`,
              borderRadius: 6,
              padding: "2px 7px",
              fontSize: 9,
              fontWeight: 700,
              fontFamily: mono,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              whiteSpace: "nowrap",
            }}
          >
            <span
              style={{
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: color,
                display: "inline-block",
                boxShadow: `0 0 6px ${color}`,
              }}
            />
            {label}
          </span>
        </div>
        <div
          style={{
            color,
            fontSize: 9,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            fontFamily: mono,
            marginBottom: message || useDecisionPanel ? 8 : 0,
          }}
        >
          Porta-voz do laboratório Grão Invest
        </div>
        {message && !useDecisionPanel && (
          <div style={{ color: C.muted, fontSize: isCompact ? 11 : 12, lineHeight: 1.6 }}>
            {message}
          </div>
        )}
        {useDecisionPanel ? (
          <div
            data-testid="patrick-jane-decision-panel"
            style={{
              background: `linear-gradient(135deg, ${C.panel}, ${C.faint})`,
              border: `1px solid ${C.border}`,
              borderRadius: 12,
              display: "flex",
              flexDirection: "column",
              gap: 10,
              minHeight: 218,
              padding: 12,
            }}
          >
            <div
              style={{
                borderBottom: `1px solid ${C.line}`,
                display: "grid",
                gap: 4,
                paddingBottom: 9,
              }}
            >
              <div
                style={{
                  color,
                  fontFamily: mono,
                  fontSize: 8,
                  fontWeight: 800,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                Painel de decisão
              </div>
              <div style={{ color: C.text, fontSize: 12, fontWeight: 800, lineHeight: 1.35 }}>
                Conclusão executiva
              </div>
              <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.45 }}>
                {message}
              </div>
            </div>
            <div
              data-testid="patrick-jane-insights"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              {heroInsights.map((item) => (
                <div
                  key={`${item.label}-${item.value}`}
                  style={{
                    borderLeft: `2px solid ${item.color || color}`,
                    minWidth: 0,
                    padding: "2px 0 2px 9px",
                  }}
                >
                  <div
                    style={{
                      color: item.color || color,
                      fontFamily: mono,
                      fontSize: 8,
                      fontWeight: 800,
                      letterSpacing: "0.08em",
                      marginBottom: 4,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {item.label}
                  </div>
                  <div style={{ color: C.text, fontSize: 11, fontWeight: 700, lineHeight: 1.35 }}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
            <div
              style={{
                alignItems: "center",
                borderTop: `1px solid ${C.line}`,
                display: "grid",
                gap: 8,
                gridTemplateColumns: "112px minmax(0, 1fr)",
                marginTop: "auto",
                paddingTop: 10,
              }}
            >
              <div
                style={{
                  color,
                  fontFamily: mono,
                  fontSize: 8,
                  fontWeight: 800,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                Método Grão
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 6 }}>
                {METHOD_STEPS.map((step, index) => (
                  <div
                    key={step}
                    style={{
                      alignItems: "center",
                      background: index === 0 ? `${color}12` : C.card,
                      border: `1px solid ${index === 0 ? `${color}45` : C.border}`,
                      borderRadius: 8,
                      color: index === 0 ? color : C.muted,
                      display: "flex",
                      fontFamily: mono,
                      fontSize: 8,
                      fontWeight: 800,
                      justifyContent: "center",
                      minHeight: 28,
                      minWidth: 0,
                      overflow: "hidden",
                      padding: "0 4px",
                      textOverflow: "ellipsis",
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {step}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : heroInsights.length > 0 && (
          <div
            data-testid="patrick-jane-insights"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 8,
              marginTop: 12,
            }}
          >
            {heroInsights.map((item) => (
              <div
                key={`${item.label}-${item.value}`}
                style={{
                  background: C.panel,
                  border: `1px solid ${C.border}`,
                  borderLeft: `2px solid ${item.color || color}`,
                  borderRadius: 9,
                  minWidth: 0,
                  padding: "9px 10px",
                }}
              >
                <div
                  style={{
                    color: item.color || color,
                    fontFamily: mono,
                    fontSize: 8,
                    fontWeight: 800,
                    letterSpacing: "0.08em",
                    marginBottom: 4,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.label}
                </div>
                <div style={{ color: C.text, fontSize: 11, fontWeight: 700, lineHeight: 1.35 }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function PatrickJaneMini({ state = "reporting", message = "", screen = "dashboard" }) {
  const { color, label } = STATE_CONFIG[state] || STATE_CONFIG.reporting;

  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        alignItems: "flex-start",
        background: color + "10",
        border: `1px solid ${color + "30"}`,
        borderRadius: 10,
        padding: "10px 12px",
      }}
    >
      <PatrickJaneImage color={color} screen={screen} imageHeight={90} />
      <div>
        <div
          style={{
            fontSize: 9,
            color,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontFamily: mono,
            marginBottom: 3,
          }}
        >
          Patrick Jane · {label}
        </div>
        <div style={{ fontSize: 11, color: C.muted, lineHeight: 1.6 }}>{message}</div>
      </div>
    </div>
  );
}

export default PatrickJane;
