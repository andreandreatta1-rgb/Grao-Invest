import { C } from "./tokens.js";

function clampProgress(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.min(100, Math.max(0, number));
}

export function ProgressBar({ progress, color = C.teal, label }) {
  const safeProgress = clampProgress(progress);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {label && <span style={{ color: C.muted, fontSize: 10 }}>{label}</span>}
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={safeProgress}
        style={{
          background: C.panel,
          border: `1px solid ${C.border}`,
          borderRadius: 999,
          height: 8,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            background: color,
            height: "100%",
            width: `${safeProgress}%`,
            borderRadius: 999,
          }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
