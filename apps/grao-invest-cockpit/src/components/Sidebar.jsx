import { C, alpha, mono, withAlpha } from "./tokens.js";
import { fmtDate } from "../utils/formatters.js";

const primaryNavItems = [
  { id: "dashboard", label: "Dashboard", icon: "target" },
  { id: "teses", label: "Teses", icon: "diamond" },
  { id: "mercado", label: "Mercado", icon: "wave" },
  { id: "backtest", label: "Validação", icon: "cycle" },
  { id: "risco", label: "Risco", icon: "risk" },
  { id: "alertas", label: "Alertas", icon: "pulse" },
];

const learningNavItems = [
  { id: "aprendizado", label: "Aprendizado", icon: "spark" },
  { id: "metodo", label: "M\u00e9todo", icon: "method" },
  { id: "saude", label: "Sa\u00fade", icon: "health" },
];

function NavIcon({ type }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    strokeWidth: 1.8,
  };

  return (
    <svg aria-hidden="true" viewBox="0 0 18 18" width="16" height="16" style={{ display: "block" }}>
      {type === "target" && (
        <>
          <circle cx="9" cy="9" r="5.8" {...common} />
          <circle cx="9" cy="9" r="1.8" fill="currentColor" />
        </>
      )}
      {type === "diamond" && <path d="M9 2.5 15 9l-6 6.5L3 9l6-6.5Z" {...common} />}
      {type === "wave" && <path d="M2 10c2.2-3.6 4.5-3.6 6.8 0s4.6 3.6 7 0" {...common} />}
      {type === "cycle" && (
        <>
          <path d="M4.2 6.2A5.6 5.6 0 0 1 14 5.5" {...common} />
          <path d="M14 3.1v2.4h-2.4" {...common} />
          <path d="M13.8 11.8A5.6 5.6 0 0 1 4 12.5" {...common} />
          <path d="M4 14.9v-2.4h2.4" {...common} />
        </>
      )}
      {type === "risk" && (
        <>
          <path d="M9 2.8 15.5 14H2.5L9 2.8Z" {...common} />
          <path d="M9 6.8v3.5" {...common} />
          <circle cx="9" cy="12.8" r="0.7" fill="currentColor" />
        </>
      )}
      {type === "pulse" && <path d="M2 9h3l1.5-3.5L9 13l2.2-5h4.8" {...common} />}
      {type === "spark" && (
        <>
          <path d="M9 2.5v13" {...common} />
          <path d="M2.5 9h13" {...common} />
          <path d="m4.5 4.5 9 9" {...common} />
          <path d="m13.5 4.5-9 9" {...common} />
        </>
      )}
      {type === "method" && (
        <>
          <circle cx="9" cy="9" r="6.2" {...common} />
          <path d="M9 4.8v4.4l3.1 2" {...common} />
        </>
      )}
      {type === "health" && (
        <>
          <path d="M9 15s-5.8-3.4-5.8-7.5A3.1 3.1 0 0 1 9 5.9a3.1 3.1 0 0 1 5.8 1.6C14.8 11.6 9 15 9 15Z" {...common} />
          <path d="M7 9h4" {...common} />
          <path d="M9 7v4" {...common} />
        </>
      )}
    </svg>
  );
}

function NavButton({ item, active, onSelect }) {
  const isActive = active === item.id;

  return (
    <button
      key={item.id}
      type="button"
      aria-label={item.label}
      onClick={() => onSelect?.(item.id)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        background: isActive ? withAlpha(C.gold, alpha.glow) : "transparent",
        color: isActive ? C.gold : C.muted,
        border: isActive ? `1px solid ${withAlpha(C.gold, "35")}` : "1px solid transparent",
        borderRadius: 10,
        padding: "10px 12px",
        fontSize: 13,
        fontWeight: isActive ? 600 : 400,
        cursor: "pointer",
        textAlign: "left",
        marginBottom: 2,
        transition: "all 0.15s",
        fontFamily: "inherit",
      }}
    >
      <span
        style={{
          width: 16,
          height: 16,
          textAlign: "center",
          opacity: isActive ? 1 : 0.6,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <NavIcon type={item.icon} />
      </span>
      {item.label}
    </button>
  );
}

function SidebarLabStatus({ lastUpdatedAt, uiRevision, buildInfo }) {
  const deployFingerprint = buildInfo?.gitCommitShort || buildInfo?.git_commit_short || "";
  const sourceApp = buildInfo?.sourceApp || buildInfo?.source_app || "";

  return (
    <section
      aria-label="Status do laboratório"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 10,
        margin: "0 12px 10px",
        padding: "10px 11px",
      }}
    >
      <div
        style={{
          color: C.gold,
          fontFamily: mono,
          fontSize: 9,
          fontWeight: 800,
          letterSpacing: "0.06em",
          marginBottom: 8,
          textTransform: "uppercase",
        }}
      >
        Status do laboratório
      </div>
      <div style={{ color: C.muted, fontSize: 10, lineHeight: 1.6 }}>
        Atualizado em {fmtDate(lastUpdatedAt)}
      </div>
      <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 800, lineHeight: 1.6 }}>
        {uiRevision}
      </div>
      {deployFingerprint && (
        <div
          data-testid="deploy-fingerprint"
          style={{ color: C.text, fontFamily: mono, fontSize: 9, fontWeight: 800, lineHeight: 1.6 }}
        >
          Build {deployFingerprint}
        </div>
      )}
      {sourceApp && (
        <div style={{ color: C.dim, fontFamily: mono, fontSize: 8, lineHeight: 1.45, overflowWrap: "anywhere" }}>
          {sourceApp}
        </div>
      )}
    </section>
  );
}

function SidebarFeedStatus({ feedStatus }) {
  if (feedStatus === "live") return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: withAlpha(C.amber, alpha.glow),
        border: `1px solid ${withAlpha(C.amber, alpha.border)}`,
        borderRadius: 10,
        color: C.amber,
        fontSize: 11,
        lineHeight: 1.45,
        margin: "0 12px 14px",
        padding: "10px 11px",
      }}
    >
      <div
        style={{
          color: C.amber,
          fontFamily: mono,
          fontSize: 9,
          fontWeight: 800,
          letterSpacing: "0.06em",
          marginBottom: 5,
          textTransform: "uppercase",
        }}
      >
        Feed em fallback
      </div>
      Feed temporariamente indisponível. Mantendo o último retrato válido do laboratório.
    </div>
  );
}

export function Sidebar({
  active = "dashboard",
  onSelect,
  feedStatus = "live",
  lastUpdatedAt,
  uiRevision = "UI rev soul-4",
  buildInfo,
}) {
  return (
    <aside
      style={{
        width: 220,
        background: C.panel,
        borderRight: `1px solid ${C.border}`,
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        height: "100vh",
        minHeight: "100vh",
        overflowY: "auto",
        position: "sticky",
        top: 0,
        alignSelf: "flex-start",
      }}
    >
      <div style={{ padding: "22px 20px 18px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <div
            style={{
              width: 32,
              height: 32,
              background: withAlpha(C.gold, alpha.subtle),
              border: `1px solid ${withAlpha(C.gold, "55")}`,
              borderRadius: 9,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: 700,
              color: C.gold,
              fontFamily: mono,
            }}
          >
            G
          </div>
          <div>
            <div style={{ color: C.text, fontSize: 14, fontWeight: 700 }}>
              {"Gr\u00e3o Invest"}
            </div>
            <div
              style={{
                color: C.muted,
                fontSize: 9,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              Motor Halley
            </div>
          </div>
        </div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            background: withAlpha(C.amber, alpha.glow),
            border: `1px solid ${withAlpha(C.amber, alpha.border)}`,
            borderRadius: 6,
            padding: "3px 8px",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: C.amber,
              display: "inline-block",
            }}
          />
          <span
            style={{
              color: C.amber,
              fontSize: 9,
              fontWeight: 600,
              letterSpacing: "0.06em",
            }}
          >
            FASE 1 - LAB
          </span>
        </div>
      </div>
      <nav style={{ padding: "12px 10px 8px", flex: "0 0 auto" }}>
        {primaryNavItems.map((item) => (
          <NavButton key={item.id} item={item} active={active} onSelect={onSelect} />
        ))}
        <div style={{ height: 1, background: C.border, margin: "12px 8px" }} />
        {learningNavItems.map((item) => (
          <NavButton key={item.id} item={item} active={active} onSelect={onSelect} />
        ))}
      </nav>
      <SidebarLabStatus lastUpdatedAt={lastUpdatedAt} uiRevision={uiRevision} buildInfo={buildInfo} />
      <SidebarFeedStatus feedStatus={feedStatus} />
    </aside>
  );
}

export default Sidebar;
