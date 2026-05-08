import { C } from "./tokens.js";
import Sidebar from "./Sidebar.jsx";

export function AppTopbar({ title = "Dashboard", subtitle, children, right }) {
  return (
    <div
      style={{
        borderBottom: `1px solid ${C.border}`,
        padding: "14px 28px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: C.panel,
        flexShrink: 0,
      }}
    >
      <div>
        <div
          style={{
            color: C.text,
            fontSize: 17,
            fontWeight: 700,
            letterSpacing: "-0.02em",
          }}
        >
          {title}
        </div>
        {subtitle && (
          <div style={{ color: C.muted, fontSize: 11, marginTop: 1 }}>
            {subtitle}
          </div>
        )}
      </div>
      {right || children}
    </div>
  );
}

export function AppLayout({
  activeNav = "dashboard",
  setActiveNav,
  children,
  topbar,
}) {
  return (
    <div
      style={{
        display: "flex",
        background: C.bg,
        minHeight: 640,
        fontFamily: "Sora, system-ui, sans-serif",
        color: C.text,
        borderRadius: 18,
        overflow: "hidden",
        border: `1px solid ${C.border}`,
      }}
    >
      <Sidebar active={activeNav} setActive={setActiveNav} />
      <div
        style={{
          flex: 1,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {topbar}
        {children}
      </div>
    </div>
  );
}

export default AppLayout;
