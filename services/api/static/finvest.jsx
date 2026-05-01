(() => {
  if (!window.React || !window.ReactDOM || !window.Recharts || !window.LucideReact) {
    return;
  }

  const { useEffect, useMemo, useState } = window.React;
  const {
    ResponsiveContainer,
    AreaChart,
    Area,
    CartesianGrid,
    XAxis,
    YAxis,
    Tooltip,
    PieChart,
    Pie,
    Cell,
    BarChart,
    Bar,
  } = window.Recharts;
  const {
    LayoutDashboard,
    PiggyBank,
    Radar,
    ShieldCheck,
    BarChart3,
    Wallet,
    ArrowUpRight,
    Activity,
    Target,
  } = window.LucideReact;

  const C = Object.freeze({
    bg: "#06090f",
    card: "#0b1020",
    border: "#182038",
    hover: "#111929",
    faint: "#0d1630",
    gold: "#c8a444",
    goldLight: "#e8c870",
    teal: "#00b896",
    purple: "#8b7fff",
    coral: "#ff6b6b",
    sky: "#4a9eff",
    text: "#dce4f0",
    muted: "#546880",
    dim: "#3a4e68",
    green: "#22c55e",
    red: "#ef4444",
    amber: "#f59e0b",
    tooltipBg: "#0d1325",
  });

  const fmt = (n) => {
    if (n >= 1e6) return `R$ ${(n / 1e6).toFixed(2).replace(".", ",")}M`;
    if (n >= 1e3) return `R$ ${(n / 1e3).toFixed(1).replace(".", ",")}K`;
    return `R$ ${Math.round(n).toLocaleString("pt-BR")}`;
  };

  const fmtK = (n) =>
    n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(0)}K` : Math.round(n);

  function Card({ children, style = {} }) {
    return (
      <div
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 16,
          padding: 20,
          ...style,
        }}
      >
        {children}
      </div>
    );
  }

  function MetricCard({ label, value, sub, color = C.text, large = false }) {
    return (
      <Card style={{ padding: "16px 20px" }}>
        <p
          style={{
            color: C.muted,
            fontSize: 10,
            margin: "0 0 8px",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          {label}
        </p>
        <p
          style={{
            color,
            fontSize: large ? 30 : 20,
            fontWeight: 700,
            margin: "0 0 3px",
            fontFamily: "Space Mono, monospace",
            letterSpacing: "-0.02em",
          }}
        >
          {value}
        </p>
        {sub && <p style={{ color: C.muted, fontSize: 11, margin: 0 }}>{sub}</p>}
      </Card>
    );
  }

  function Bar2({ pct, color = C.gold, h = 6 }) {
    return (
      <div style={{ background: C.faint, borderRadius: 99, height: h, overflow: "hidden" }}>
        <div
          style={{
            width: `${Math.min(100, Math.max(0, pct))}%`,
            height: "100%",
            background: color,
            borderRadius: 99,
            transition: "width 0.7s cubic-bezier(.4,0,.2,1)",
          }}
        />
      </div>
    );
  }

  function Tag({ color, children }) {
    return (
      <span
        style={{
          background: `${color}28`,
          color,
          fontSize: 10,
          fontWeight: 700,
          padding: "3px 7px",
          borderRadius: 6,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        {children}
      </span>
    );
  }

  const TooltipBox = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div
        style={{
          background: C.tooltipBg,
          border: `1px solid ${C.border}`,
          borderRadius: 10,
          padding: "10px 14px",
          fontSize: 12,
        }}
      >
        {label && <p style={{ color: C.muted, margin: "0 0 6px" }}>{label}</p>}
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color || C.gold, margin: "2px 0", fontWeight: 600 }}>
            {p.name ? `${p.name}: ` : ""}
            {typeof p.value === "number" && p.value > 5000 ? fmt(p.value) : p.value}
          </p>
        ))}
      </div>
    );
  };

  function Slider({ label, value, min, max, step, onChange, display }) {
    return (
      <div style={{ marginBottom: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ color: C.muted, fontSize: 12 }}>{label}</span>
          <span
            style={{
              color: C.gold,
              fontSize: 14,
              fontWeight: 700,
              fontFamily: "Space Mono, monospace",
            }}
          >
            {display(value)}
          </span>
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(+e.target.value)}
          style={{ width: "100%", accentColor: C.gold, cursor: "pointer", height: 4 }}
        />
      </div>
    );
  }

  function SidebarItem({ icon: Icon, label, active, onClick }) {
    return (
      <button
        onClick={onClick}
        type="button"
        style={{
          background: active ? `${C.gold}22` : "transparent",
          border: `1px solid ${active ? `${C.gold}66` : C.border}`,
          borderRadius: 12,
          color: active ? C.gold : C.muted,
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 12px",
          fontSize: 12,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        <Icon size={14} />
        <span>{label}</span>
      </button>
    );
  }

  function Finvest() {
    const [width, setWidth] = useState(window.innerWidth || 1200);
    const [tab, setTab] = useState("visao");
    const [monthlyExpense, setMonthlyExpense] = useState(4500);
    const [reserveNow, setReserveNow] = useState(17800);

    useEffect(() => {
      const el = document.createElement("link");
      el.rel = "stylesheet";
      el.href =
        "https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap";
      document.head.appendChild(el);
      return () => el.remove();
    }, []);

    useEffect(() => {
      const onResize = () => setWidth(window.innerWidth || 1200);
      window.addEventListener("resize", onResize);
      return () => window.removeEventListener("resize", onResize);
    }, []);

    const compact = width < 1024;
    const stack = width < 820;

    const reserveTarget = useMemo(() => monthlyExpense * 6, [monthlyExpense]);
    const reservePct = useMemo(() => (reserveTarget > 0 ? (reserveNow / reserveTarget) * 100 : 0), [reserveNow, reserveTarget]);
    const estMonths = useMemo(() => {
      const gap = Math.max(0, reserveTarget - reserveNow);
      return gap === 0 ? 0 : Math.ceil(gap / 2200);
    }, [reserveNow, reserveTarget]);

    const wealthSeries = [
      { mes: "Nov", v: 101000 },
      { mes: "Dez", v: 104500 },
      { mes: "Jan", v: 108900 },
      { mes: "Fev", v: 106800 },
      { mes: "Mar", v: 112400 },
      { mes: "Abr", v: 118300 },
    ];

    const cashFlow = [
      { mes: "Nov", entradas: 8200 },
      { mes: "Dez", entradas: 9100 },
      { mes: "Jan", entradas: 8700 },
      { mes: "Fev", entradas: 9000 },
      { mes: "Mar", entradas: 9600 },
      { mes: "Abr", entradas: 10100 },
    ];

    const theses = [
      { tese: "Macro Brasil", conv: 74, retorno: 13 },
      { tese: "Commodities", conv: 62, retorno: 9 },
      { tese: "Consumo", conv: 55, retorno: 7 },
      { tese: "Financeiro", conv: 69, retorno: 11 },
    ];

    const alocacao = [
      { nome: "Acoes BR", pct: 46, color: C.gold },
      { nome: "Renda Fixa", pct: 31, color: C.teal },
      { nome: "Caixa", pct: 14, color: C.sky },
      { nome: "Internacional", pct: 9, color: C.purple },
    ];

    const reserveHints = [
      { nome: "Tesouro Selic", prazo: "D+1", risco: "baixo", cor: C.teal },
      { nome: "CDB D+1", prazo: "D+1", risco: "baixo", cor: C.sky },
      { nome: "Conta remunerada", prazo: "D+0", risco: "baixo", cor: C.gold },
    ];

    const modules = [
      { id: "visao", label: "Visao Geral", icon: LayoutDashboard },
      { id: "reserva", label: "Reserva", icon: PiggyBank },
      { id: "teses", label: "Teses", icon: Radar },
      { id: "risco", label: "Risco", icon: ShieldCheck },
      { id: "metricas", label: "Metricas", icon: BarChart3 },
    ];

    const reserveState =
      reservePct < 40
        ? { background: `${C.amber}18`, border: `1px solid ${C.amber}44`, color: C.amber, label: "Abaixo da faixa sugerida" }
        : reservePct < 80
          ? { background: `${C.teal}18`, border: `1px solid ${C.teal}44`, color: C.teal, label: "Progresso consistente" }
          : { background: `${C.gold}22`, border: `1px solid ${C.gold}66`, color: C.gold, label: "Reserva em faixa robusta" };

    return (
      <div
        style={{
          display: "flex",
          flexDirection: compact ? "column" : "row",
          background: `radial-gradient(circle at 14% 8%, ${C.faint} 0%, ${C.bg} 60%)`,
          minHeight: 640,
          fontFamily: "Sora, system-ui, sans-serif",
          color: C.text,
          borderRadius: 20,
          overflow: "hidden",
          border: `1px solid ${C.border}`,
        }}
      >
        <aside
          style={{
            width: compact ? "100%" : 210,
            background: C.card,
            borderRight: compact ? "none" : `1px solid ${C.border}`,
            borderBottom: compact ? `1px solid ${C.border}` : "none",
            padding: compact ? 14 : 16,
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
          <div
            style={{
              border: `1px solid ${C.border}`,
              borderRadius: 14,
              background: C.faint,
              padding: "12px 12px",
            }}
          >
            <p style={{ margin: 0, color: C.goldLight, fontSize: 12, fontWeight: 700, letterSpacing: "0.08em" }}>GRÃO INVEST</p>
            <p style={{ margin: "4px 0 0", color: C.muted, fontSize: 11 }}>Suite de simulacao e tese</p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: compact ? "repeat(3, minmax(0, 1fr))" : "1fr",
              gap: 8,
            }}
          >
            {modules.map((item) => (
              <SidebarItem key={item.id} icon={item.icon} label={item.label} active={tab === item.id} onClick={() => setTab(item.id)} />
            ))}
          </div>

          <Card style={{ padding: 12, marginTop: compact ? 0 : "auto" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Activity size={14} color={C.teal} />
              <p style={{ margin: 0, color: C.muted, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" }}>Status</p>
            </div>
            <p style={{ margin: 0, color: C.text, fontSize: 12 }}>Dados sincronizados ate 09:30 BRT</p>
          </Card>
        </aside>

        <main style={{ flex: 1, overflow: "auto", padding: compact ? "18px 16px 26px" : "28px 28px 40px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: stack ? "flex-start" : "center", gap: 10, marginBottom: 18, flexDirection: stack ? "column" : "row" }}>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: C.text, margin: 0 }}>Painel de Planejamento e Teses</h2>
              <p style={{ margin: "5px 0 0", color: C.muted, fontSize: 12 }}>Visao integrada de patrimonio, reserva e acompanhamento das hipoteses.</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.green, fontSize: 12, fontWeight: 600 }}>
              <ArrowUpRight size={14} />
              <span>Capital em alta no mes</span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: stack ? "1fr" : "1fr 1fr 1fr", gap: 12, marginBottom: 18 }}>
            <MetricCard label="Patrimonio Atual" value={fmt(118300)} sub="Fechamento parcial do mes" large />
            <MetricCard label="PnL MTD" value={fmt(5900)} sub="Variacao acumulada em abril" color={C.green} />
            <MetricCard label="Caixa Disponivel" value={fmt(16500)} sub={`Cobertura de ${fmtK(reservePct)}% da reserva alvo`} color={C.teal} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: stack ? "1fr" : "1fr 1.5fr", gap: 18, marginBottom: 18 }}>
            <Card>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.text }}>Reserva de Emergencia</h3>
                <Tag color={reserveState.color}>6x despesas</Tag>
              </div>

              <Slider label="Despesas mensais" value={monthlyExpense} min={1000} max={15000} step={100} onChange={setMonthlyExpense} display={fmt} />
              <Slider
                label="Reserva atual"
                value={reserveNow}
                min={0}
                max={Math.max(20000, reserveTarget * 2)}
                step={100}
                onChange={setReserveNow}
                display={fmt}
              />

              <MetricCard label="Valor alvo da reserva" value={fmt(reserveTarget)} sub={`Aporte estimado para concluir em ${fmtK(estMonths)} meses`} color={C.gold} />

              <div style={{ marginTop: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, color: C.muted, fontSize: 12 }}>
                  <span>Progresso</span>
                  <span style={{ color: C.gold, fontFamily: "Space Mono, monospace" }}>{fmtK(reservePct)}%</span>
                </div>
                <Bar2 pct={reservePct} color={reservePct >= 100 ? C.green : C.gold} h={8} />
              </div>

              <div style={{ marginTop: 14, borderRadius: 10, padding: "10px 12px", ...reserveState }}>
                <p style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>{reserveState.label}</p>
              </div>

              <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
                {reserveHints.map((item) => (
                  <Card key={item.nome} style={{ padding: "10px 12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                      <div>
                        <p style={{ margin: 0, color: C.text, fontSize: 13, fontWeight: 600 }}>{item.nome}</p>
                        <p style={{ margin: "2px 0 0", color: C.muted, fontSize: 12 }}>Liquidez {item.prazo} · Risco {item.risco}</p>
                      </div>
                      <Tag color={item.cor}>Liquidez</Tag>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>

            <Card style={{ minHeight: 360 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.text }}>Evolucao do Patrimonio</h3>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: C.gold, fontSize: 12 }}>
                  <Wallet size={14} />
                  <span>{fmt(wealthSeries[wealthSeries.length - 1].v)}</span>
                </div>
              </div>
              <div style={{ height: 290 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={wealthSeries} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="grad-patrimonio" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={C.gold} stopOpacity={0.4} />
                        <stop offset="100%" stopColor={C.gold} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
                    <XAxis dataKey="mes" tick={{ fill: C.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={fmtK} />
                    <Tooltip content={<TooltipBox />} />
                    <Area type="monotone" dataKey="v" stroke={C.gold} strokeWidth={2.5} fill="url(#grad-patrimonio)" dot={false} name="Patrimonio" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: stack ? "1fr" : "1fr 1fr", gap: 18 }}>
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.text }}>Alocacao Atual</h3>
                <Tag color={C.sky}>Carteira</Tag>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: stack ? "1fr" : "220px 1fr", gap: 8, alignItems: "center" }}>
                <div style={{ display: "flex", justifyContent: "center" }}>
                  <PieChart width={200} height={200}>
                    <Pie data={alocacao} cx={100} cy={100} innerRadius={52} outerRadius={88} dataKey="pct" paddingAngle={3} nameKey="nome">
                      {alocacao.map((item, i) => (
                        <Cell key={i} fill={item.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<TooltipBox />} formatter={(value) => [`${fmtK(value)}%`]} />
                  </PieChart>
                </div>
                <div style={{ display: "grid", gap: 10 }}>
                  {alocacao.map((item) => (
                    <div key={item.nome}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ color: C.muted, fontSize: 12 }}>{item.nome}</span>
                        <span style={{ color: item.color, fontSize: 12, fontFamily: "Space Mono, monospace" }}>{fmtK(item.pct)}%</span>
                      </div>
                      <Bar2 pct={item.pct} color={item.color} />
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            <Card style={{ minHeight: 290 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.text }}>Radar de Teses</h3>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: C.teal, fontSize: 12 }}>
                  <Target size={14} />
                  <span>Cenarios em observacao</span>
                </div>
              </div>
              <div style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={theses} margin={{ top: 0, right: 12, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
                    <XAxis dataKey="tese" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={fmtK} />
                    <Tooltip content={<TooltipBox />} />
                    <Bar dataKey="conv" name="Conviccao" fill={C.sky} radius={[6, 6, 0, 0]} />
                    <Bar dataKey="retorno" name="Retorno esp." fill={C.teal} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card style={{ marginTop: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.text }}>Fluxo de Entradas Simulado</h3>
              <div style={{ display: "flex", alignItems: "center", gap: 6, color: C.purple, fontSize: 12 }}>
                <Activity size={14} />
                <span>Media mensal {fmt(9283)}</span>
              </div>
            </div>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cashFlow} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="grad-cashflow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={C.teal} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={C.teal} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
                  <XAxis dataKey="mes" tick={{ fill: C.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={fmtK} />
                  <Tooltip content={<TooltipBox />} />
                  <Area type="monotone" dataKey="entradas" stroke={C.teal} strokeWidth={2.5} fill="url(#grad-cashflow)" dot={false} name="Entradas" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </main>
      </div>
    );
  }

  const rootNode = document.getElementById("finvest-root");
  if (!rootNode) {
    return;
  }
  const root = window.ReactDOM.createRoot(rootNode);
  root.render(<Finvest />);
})();
