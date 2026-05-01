# Grão Invest — AGENTS.md
# Codex: leia este arquivo inteiro antes de qualquer tarefa neste repositório.

---

## 1. Stack obrigatória

| Camada | Escolha |
|---|---|
| Framework | React 18 (JSX) |
| Gráficos | Recharts |
| Ícones | lucide-react (somente se necessário) |
| Estilo | 100% inline `style={}` — zero CSS externo, zero Tailwind, zero className para visual |
| Fontes | Sora (UI) + JetBrains Mono (números/código) via useEffect |

---

## 2. Design tokens — objeto `C` (nunca hardcode hex fora dele)

```js
const C = {
  bg: "#070b14", panel: "#0c1120", card: "#101828",
  border: "#1a2540", hover: "#141f35", line: "#1e2d4a",
  gold: "#c8a444", goldLight: "#e8c870", goldDim: "#8a6e2c",
  teal: "#00c896", tealDim: "#006b50",
  sky: "#3b9eff",  skyDim: "#1a4d8c",
  coral: "#ff5e5e", coralDim: "#7a2020",
  amber: "#f5a623", amberDim: "#7a4e05",
  green: "#22c55e", greenDim: "#14532d",
  purple: "#a78bfa",
  text: "#e2eaf8", muted: "#5a7090", dim: "#2e4060",
};

const mono = "'JetBrains Mono', 'Fira Code', monospace";
```

---

## 3. Injeção de fontes (obrigatório em todo componente raiz)

```js
useEffect(() => {
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap";
  document.head.appendChild(link);
  return () => link.remove();
}, []);
```

---

## 4. Componentes base — copiar exatamente, nunca reescrever

### Badge

```jsx
function Badge({ label, type = "neutral" }) {
  const styles = {
    open:    { bg: C.teal + "20",  color: C.teal,  border: C.teal + "40" },
    closed:  { bg: C.muted + "20", color: C.muted, border: C.muted + "40" },
    warning: { bg: C.amber + "20", color: C.amber, border: C.amber + "40" },
    success: { bg: C.green + "20", color: C.green, border: C.green + "40" },
    danger:  { bg: C.coral + "20", color: C.coral, border: C.coral + "40" },
    neutral: { bg: C.dim + "60",   color: C.muted, border: C.dim },
    high:    { bg: C.gold + "20",  color: C.gold,  border: C.gold + "40" },
    bull:    { bg: C.teal + "20",  color: C.teal,  border: C.teal + "40" },
    bear:    { bg: C.coral + "20", color: C.coral, border: C.coral + "40" },
    info:    { bg: C.sky + "20",   color: C.sky,   border: C.sky + "40" },
  };
  const s = styles[type] || styles.neutral;
  return (
    <span style={{
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 6,
      letterSpacing: "0.04em", textTransform: "uppercase",
      fontFamily: mono, whiteSpace: "nowrap",
    }}>{label}</span>
  );
}
```

### KPICard

```jsx
function KPICard({ label, value, sub, valueColor, accent, icon }) {
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`,
      borderTop: `2px solid ${accent || C.border}`,
      borderRadius: 14, padding: "18px 20px",
      display: "flex", flexDirection: "column", gap: 6,
      position: "relative", overflow: "hidden",
    }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 80, height: 80, pointerEvents: "none",
        background: `radial-gradient(circle at top right, ${(accent || C.gold) + "18"}, transparent 70%)`,
        borderRadius: "0 14px 0 0" }} />
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
        {icon && <span style={{ fontSize: 13 }}>{icon}</span>}
        <span style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</span>
      </div>
      <span style={{ color: valueColor || C.text, fontSize: 26, fontWeight: 700, fontFamily: mono, letterSpacing: "-0.02em", lineHeight: 1 }}>{value}</span>
      {sub && <span style={{ color: C.muted, fontSize: 11, marginTop: 2 }}>{sub}</span>}
    </div>
  );
}
```

### ThesisCard

```jsx
// borderLeft: teal = normal, amber = alerta de stop
function ThesisCard({ thesis }) {
  const isWarning = thesis.desfecho?.toLowerCase().includes("stop");
  const momentumColor = thesis.momentum >= 0 ? C.teal : C.coral;
  return (
    <div style={{
      background: C.card,
      border: `1px solid ${isWarning ? C.amber + "55" : C.border}`,
      borderLeft: `3px solid ${isWarning ? C.amber : C.teal}`,
      borderRadius: 12, padding: 16,
      display: "flex", flexDirection: "column", gap: 10,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: C.muted, fontSize: 10, fontFamily: mono }}>#{thesis.id}</span>
          <span style={{ color: C.text, fontSize: 15, fontWeight: 700 }}>{thesis.ativo}</span>
          <Badge label={thesis.direcao} type={thesis.direcao === "Alta" ? "bull" : "bear"} />
        </div>
        <Badge label={thesis.desfecho || thesis.status} type={isWarning ? "warning" : "open"} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "Entrada",  value: `R$ ${thesis.entrada}`, color: C.text },
          { label: "Esperado", value: `${thesis.expected > 0 ? "+" : ""}${thesis.expected.toFixed(2)}%`, color: C.sky },
          { label: "Momento",  value: `${thesis.momentum > 0 ? "+" : ""}${thesis.momentum.toFixed(2)}%`, color: momentumColor },
        ].map((m) => (
          <div key={m.label} style={{ background: C.panel, borderRadius: 8, padding: "8px 10px" }}>
            <div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>{m.label}</div>
            <div style={{ color: m.color, fontSize: 13, fontWeight: 700, fontFamily: mono }}>{m.value}</div>
          </div>
        ))}
      </div>
      <div style={{ background: C.panel, borderRadius: 8, padding: "8px 12px" }}>
        <span style={{ color: C.muted, fontSize: 10, marginRight: 8 }}>Estrutura</span>
        <span style={{ color: C.sky, fontSize: 12, fontWeight: 500 }}>{thesis.estrutura}</span>
      </div>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <span style={{ color: C.muted, fontSize: 10 }}>Saída</span>
        <span style={{ color: C.green, fontSize: 11, fontFamily: mono, fontWeight: 600 }}>▲ R$ {thesis.saiGanho}</span>
        <div style={{ width: 1, height: 12, background: C.border }} />
        <span style={{ color: C.coral, fontSize: 11, fontFamily: mono, fontWeight: 600 }}>▼ R$ {thesis.saiStop}</span>
        {thesis.inicio && <span style={{ color: C.muted, fontSize: 10, marginLeft: "auto" }}>go-live {thesis.inicio}</span>}
      </div>
    </div>
  );
}
```

### Tabela padrão (header + hover)

```jsx
<table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
  <thead>
    <tr style={{ background: C.panel }}>
      {cols.map((h) => (
        <th key={h} style={{ padding: "9px 12px", color: C.muted, fontWeight: 600, textAlign: "left",
          fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em",
          borderBottom: `1px solid ${C.border}`, whiteSpace: "nowrap" }}>{h}</th>
      ))}
    </tr>
  </thead>
  <tbody>
    {rows.map((r, i) => (
      <tr key={i} style={{ borderBottom: `1px solid ${C.line}`, transition: "background 0.1s" }}
        onMouseEnter={(e) => e.currentTarget.style.background = C.hover}
        onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
        {/* células */}
      </tr>
    ))}
  </tbody>
</table>
```

---

## 5. Cor semântica (sempre aplicar)

| Contexto | Token |
|---|---|
| Valor positivo / alta | `C.teal` |
| Valor negativo / queda | `C.coral` |
| Alerta / stop próximo | `C.amber` |
| Sucesso / aprovado | `C.green` |
| Neutro / informativo | `C.sky` |
| Destaque / marca | `C.gold` |
| Todos os números | `fontFamily: mono` |

---

## 6. Layout raiz

```jsx
<div style={{ display: "flex", background: C.bg, minHeight: 640,
  fontFamily: "Sora, system-ui, sans-serif", color: C.text,
  borderRadius: 18, overflow: "hidden", border: `1px solid ${C.border}` }}>
  <Sidebar active={activeNav} setActive={setActiveNav} />
  <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
    {/* Topbar: background C.panel, borderBottom C.border, padding "14px 28px" */}
    {/* Conteúdo: padding "24px 28px 40px", display flex, flexDirection column, gap 24 */}
  </div>
</div>
```

---

## 7. Grids canônicos

```js
"repeat(5, 1fr)", gap: 12   // KPIs
"1fr 1fr 1fr",    gap: 14   // ThesisCards
"1fr 1fr",        gap: 14   // painéis lado a lado
"1fr 1fr 1fr",    gap: 8    // mini métricas dentro de card
"1fr 1fr 1fr 1fr",gap: 12   // 4 métricas em painel de exercício
```

---

## 8. Tipografia

| Elemento | size | weight | family |
|---|---|---|---|
| Título de tela | 17px | 700 | Sora |
| Título de seção | 14–15px | 700 | Sora |
| Label uppercase | 10px | 600 | Sora + letterSpacing 0.08em |
| Valor KPI | 26px | 700 | mono |
| Célula de tabela | 11px | 400 | mono para números |
| Sub/caption | 11px | 400 | Sora |

---

## 9. Proibições absolutas

- ❌ Hex hardcoded fora do objeto `C`
- ❌ `className` para qualquer estilo visual
- ❌ Fundos claros ou brancos (dark theme absoluto)
- ❌ `box-shadow` decorativo
- ❌ `position: fixed`
- ❌ Números sem formatar exibidos na tela
- ❌ Reescrever Badge, KPICard ou ThesisCard — apenas reutilizar
- ❌ Fontes: Arial, Inter, Roboto, system-ui como principal

---

## 10. Modelo de task bem formada

> "Crie a tela `Mercado` seguindo AGENTS.md.
> Mostre: topbar com título 'Mercado', 5 KPICards (Ibovespa, variação dia,
> variação semana, volume médio, volatilidade — cada um com `accent` na cor semântica certa),
> e uma tabela de ativos (PETR4, MGLU3, RENT3, VALE3, WEGE3) com colunas:
> Ativo, Preço, Var. dia, Var. semana, Volume, Tendência (Badge bull/bear/neutral),
> Teses ativas (Badge info). Positivos em C.teal, negativos em C.coral.
> Hover nas linhas conforme padrão da tabela no AGENTS.md."

---

## 11. Referência de código

O componente completo em produção está em `grao-dashboard.jsx`.
Leia-o antes de criar qualquer nova tela para entender a estrutura real.
