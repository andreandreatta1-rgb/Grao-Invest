import { C, alpha, withAlpha } from "./tokens.js";
import PatrickJane from "./PatrickJane.jsx";

export function ScreenHero({
  screen,
  state = "reporting",
  message,
  insights = [],
  accent = C.gold,
  imageBorderColor,
  imageStyle,
  children,
  style = {},
  contentStyle = {},
}) {
  return (
    <section
      data-testid={`${screen}-screen-hero`}
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 14,
        overflow: "hidden",
        padding: 18,
        position: "relative",
        ...style,
      }}
    >
      <div
        style={{
          background: `radial-gradient(ellipse at 88% 24%, ${withAlpha(accent, alpha.glow)}, transparent 62%)`,
          height: 210,
          pointerEvents: "none",
          position: "absolute",
          right: 0,
          top: 0,
          width: 340,
        }}
      />
      <PatrickJane
        hero
        screen={screen}
        state={state}
        message={message}
        insights={insights}
        imageHeight={168}
        imageWidth="100%"
        imageBorderColor={imageBorderColor || `${accent}45`}
        imageStyle={imageStyle}
        style={{ gap: 24, position: "relative", zIndex: 2 }}
        contentStyle={{ maxWidth: 980, ...contentStyle }}
      />
      {children && (
        <div style={{ marginTop: 16, position: "relative", zIndex: 2 }}>
          {children}
        </div>
      )}
    </section>
  );
}

export default ScreenHero;
