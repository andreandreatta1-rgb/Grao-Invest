# Instruções para o Codex — Portfolio redesign
> Referência visual: `portfolio_mockup_reference.html` (entregue junto com este arquivo)
> App base: `index.html` + `styles.css` v2.4.195

---

## Como usar este documento

1. Abra `portfolio_mockup_reference.html` no browser — ela é a **fonte da verdade visual**
2. Siga as instruções abaixo para mapear cada elemento do mockup ao código existente
3. Não invente nada — se um elemento não existir no app, crie copiando **exatamente** o HTML e CSS do arquivo de referência

---

## 1. Design tokens — primeiro passo obrigatório

Adicione este bloco no início de `styles.css`, **antes** de qualquer outra regra:

```css
:root {
  --color-bg:            #060E1E;
  --color-surface:       #0C1A30;
  --color-surface-2:     #0A1829;
  --color-border:        rgba(255,255,255,0.10);
  --color-border-strong: rgba(255,255,255,0.20);
  --color-ink:           #EDF4FF;
  --color-ink-2:         #A8C4E0;
  --color-ink-3:         #5A7A9A;
  --color-cyan:          #22D3EE;
  --color-amber:         #FCD34D;
  --color-emerald:       #34D399;
  --color-rose:          #F87171;
  --radius-sm:    10px;
  --radius-md:    14px;
  --radius-lg:    20px;
  --radius-xl:    26px;
  --tracking-label:  0.24em;
  --tracking-kicker: 0.34em;
}
```

---

## 2. Topbar

### O que mudar
O topbar atual tem múltiplas seções empilhadas. Substituir por **uma única barra de 52px**.

### CSS alvo (copiar do mockup)
```css
.ptp-topbar {
  background: rgba(12, 26, 48, 0.95);
  border-bottom: 0.5px solid var(--color-border);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 52px;
  position: sticky;
  top: 0;
  z-index: 10;
  backdrop-filter: blur(12px);
}
```

### Ordem dos elementos dentro do topbar (esquerda → direita)
1. Logo 32×32 (`.ptp-topbar-logo`)
2. Nome "Prospect to Project" (`.ptp-topbar-appname`)
3. Divisor vertical 0.5px (`.ptp-topbar-divider`)
4. Pill do cliente ativo — avatar 20px + nome (`.ptp-topbar-client`)
5. `margin-left: auto` a partir daqui
6. Stack de avatares do time (`.ptp-team-stack` com `.ptp-team-av`)
7. Pill OpenAI com dot de status (`.ptp-conn-pill`)
8. Pill NetSuite com dot de status (`.ptp-conn-pill`)
9. Versão texto (`.ptp-version`)

### IDs a preservar (app.js usa estes)
| ID atual | Novo ID/classe | Observação |
|---|---|---|
| `#hero-client-focus` | `#ptp-topbar-client` | Manter lógica de show/hide |
| `#hero-client-name` | `#ptp-topbar-client-name` | Manter binding de texto |
| `#hero-openai-pill` | `.ptp-conn-pill` (OpenAI) | Manter dot e label internos |
| `#hero-netsuite-pill` | `.ptp-conn-pill` (NetSuite) | Idem |
| `#hero-release-badge` | `#ptp-version` | Manter binding de versão |

---

## 3. Context/action bar

Criar uma segunda barra logo abaixo do topbar com todos os controles de contexto numa linha só.

### CSS alvo
```css
.ptp-ctxbar {
  background: rgba(10, 24, 41, 0.92);
  border-bottom: 0.5px solid var(--color-border);
  padding: 8px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
```

### Ordem dos elementos (esquerda → direita)
1. Mode switcher segmented control com 3 botões: "Central base" | "Imported" | "My portfolio"
2. Scope pill (quando ativo: fundo azul claro)
3. Filter input (flex: 1, max-width: 300px)
4. `margin-left: auto`
5. Botões: Save · New · Refresh · Export SP report

### Segmented control
```css
.ptp-mode-switcher {
  display: flex; gap: 2px;
  background: rgba(255,255,255,0.04);
  border: 0.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 3px;
}
.ptp-mode-btn { padding: 5px 12px; border-radius: 7px; font-size: 11px; font-weight: 500; color: var(--color-ink-3); background: transparent; border: none; cursor: pointer; }
.ptp-mode-btn.is-active { background: rgba(255,255,255,0.08); color: var(--color-ink); box-shadow: 0 0 0 0.5px var(--color-border); }
```

---

## 4. KPI row

### CSS alvo
```css
.ptp-kpi-row { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 7px; }
.ptp-kpi { background: rgba(12,26,48,0.80); border: 0.5px solid var(--color-border); border-radius: var(--radius-lg); padding: 10px 13px; }
.ptp-kpi.is-warn   { border-left: 2px solid #EF9F27; }
.ptp-kpi.is-danger { border-left: 2px solid #F87171; }
.ptp-kpi-label { font-size: 9px; font-weight: 500; letter-spacing: 0.24em; color: var(--color-ink-3); text-transform: uppercase; display: block; margin-bottom: 4px; }
.ptp-kpi-value { font-size: 22px; font-weight: 500; line-height: 1; color: var(--color-ink); display: block; }
.ptp-kpi.is-warn   .ptp-kpi-value { color: #FCD34D; }
.ptp-kpi.is-danger .ptp-kpi-value { color: #FCA5A5; }
.ptp-kpi-sub { font-size: 10px; color: var(--color-ink-3); display: block; margin-top: 3px; line-height: 1.4; }
```

### Quais tiles recebem `is-warn`
Aplicar dinamicamente via app.js quando o valor > 0:
- Revisões vencidas → `is-warn`
- Sem dados operacionais → `is-warn`
- Action items vencidas → `is-warn`
- Cases críticos → `is-danger`

---

## 5. Main row: prioridade + cockpit

### Layout
```css
.ptp-main-row { display: grid; grid-template-columns: 280px minmax(0,1fr); gap: 10px; align-items: start; }
```

### 5a. Priority list (coluna esquerda, 280px fixos)
Container: `.ptp-panel` com header + lista de itens.

```css
.ptp-panel { background: rgba(12,26,48,0.80); border: 0.5px solid var(--color-border); border-radius: var(--radius-xl); overflow: hidden; }
.ptp-panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px 10px; border-bottom: 0.5px solid var(--color-border); }
.ptp-panel-title { font-size: 12px; font-weight: 500; color: var(--color-ink); }
.ptp-panel-meta  { font-size: 10px; color: var(--color-ink-3); }
.ptp-priority-item { display: flex; align-items: center; gap: 10px; padding: 8px 16px; border-bottom: 0.5px solid var(--color-border); }
.ptp-priority-item:last-child { border-bottom: none; }
.ptp-priority-av { width: 26px; height: 26px; border-radius: 7px; background: rgba(240,149,149,0.18); border: 0.5px solid rgba(240,149,149,0.30); display: flex; align-items: center; justify-content: center; font-size: 7px; font-weight: 700; color: #FCA5A5; flex-shrink: 0; }
.ptp-priority-name { font-size: 11px; font-weight: 500; color: var(--color-ink); line-height: 1.35; }
.ptp-priority-sub  { font-size: 10px; color: var(--color-ink-3); }
.ptp-ai-chip { font-size: 9px; padding: 2px 7px; border-radius: 999px; background: rgba(127,119,221,0.18); border: 0.5px solid rgba(127,119,221,0.35); color: #C4BFFE; font-weight: 500; flex-shrink: 0; }
```

### 5b. Cockpit operacional (coluna direita, expansível)
Tabela com 5 colunas via CSS Grid com `display: contents`.

```css
.ptp-cockpit-grid { display: grid; grid-template-columns: minmax(0,1fr) 100px 70px 70px 100px; }
.ptp-cockpit-head > div { font-size: 9px; font-weight: 500; letter-spacing: 0.24em; color: var(--color-ink-3); text-transform: uppercase; padding: 8px 14px; background: rgba(255,255,255,0.02); border-bottom: 0.5px solid var(--color-border); }
.ptp-cockpit-row > div { padding: 10px 14px; border-bottom: 0.5px solid var(--color-border); font-size: 11px; color: var(--color-ink-2); display: flex; align-items: flex-start; }
.ptp-cockpit-row:last-child > div { border-bottom: none; }
.ptp-cockpit-project-name { font-size: 12px; font-weight: 500; color: var(--color-ink); display: block; margin-bottom: 3px; }
.ptp-ck-num { font-size: 13px; font-weight: 500; color: var(--color-ink); justify-content: center; width: 100%; }
.ptp-ck-num.is-warn { color: #FCD34D; }
.ptp-ck-num.is-zero { color: var(--color-ink-3); }
.ptp-ck-date { color: var(--color-ink-3); font-size: 10px; }
```

---

## 6. Project table

### CSS alvo
```css
.ptp-proj-table { background: rgba(12,26,48,0.80); border: 0.5px solid var(--color-border); border-radius: var(--radius-xl); overflow: hidden; }
.ptp-proj-grid { display: grid; grid-template-columns: minmax(0,2fr) 110px 140px 120px 54px 120px 100px; }
.ptp-proj-th { font-size: 9px; font-weight: 500; letter-spacing: 0.24em; color: var(--color-ink-3); text-transform: uppercase; padding: 8px 14px; background: rgba(255,255,255,0.02); border-bottom: 0.5px solid var(--color-border); }
.ptp-proj-td { padding: 11px 14px; border-bottom: 0.5px solid var(--color-border); font-size: 11px; color: var(--color-ink-2); display: flex; align-items: flex-start; }
.ptp-proj-row.is-last .ptp-proj-td { border-bottom: none; }
.ptp-proj-name    { font-size: 12px; font-weight: 500; color: var(--color-ink); display: block; margin-bottom: 2px; }
.ptp-proj-id      { font-size: 10px; color: var(--color-ink-3); display: block; margin-bottom: 3px; }
.ptp-proj-warning { font-size: 10px; color: #FCD34D; line-height: 1.45; display: block; }
.ptp-proj-cov     { font-size: 10px; color: var(--color-ink-3); display: block; margin-top: 2px; }
.ptp-status-pill  { font-size: 10px; padding: 3px 9px; border-radius: 999px; background: rgba(55,138,221,0.15); border: 0.5px solid rgba(133,183,235,0.30); color: #93C5FD; display: inline-block; }
.ptp-rev-never    { font-size: 9px; padding: 3px 9px; border-radius: 999px; background: rgba(252,199,117,0.12); border: 0.5px solid rgba(252,199,117,0.28); color: #FCD34D; font-weight: 500; cursor: pointer; display: inline-block; }
.ptp-rev-ok       { font-size: 9px; padding: 3px 9px; border-radius: 999px; background: rgba(52,211,153,0.12); border: 0.5px solid rgba(52,211,153,0.28); color: #6EE7B7; font-weight: 500; display: inline-block; }
.alta-inline { font-size: 9px; padding: 1px 6px; border-radius: 999px; background: rgba(240,149,149,0.15); border: 0.5px solid rgba(240,149,149,0.28); color: #FCA5A5; font-weight: 500; margin-left: 6px; flex-shrink: 0; }
.ptp-row-actions { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.ptp-ra-btn { font-size: 10px; padding: 4px 8px; border-radius: 6px; border: 0.5px solid var(--color-border-strong); background: rgba(255,255,255,0.03); color: var(--color-ink-2); cursor: pointer; text-align: center; font-family: var(--font-sans); }
.ptp-ra-btn-mark { background: rgba(52,211,153,0.10); border-color: rgba(52,211,153,0.30); color: #6EE7B7; }
.ptp-ra-btn-open { background: rgba(55,138,221,0.10); border-color: rgba(133,183,235,0.30); color: #93C5FD; }
```

---

## 7. Elementos a REMOVER

| O que remover | Seletor / ID | Motivo |
|---|---|---|
| 3 blur balls no body | `body > div[aria-hidden]` | Ruído visual |
| 2 blur balls no header | `header > div[aria-hidden]` (internos) | Idem |
| Painel "Distribuição por status" | container do gráfico de barras | Sem utilidade identificada |
| Painel "Carga por SP" | container com SP load | Sem utilidade identificada |
| Painel "Projetos por SP" | container separado | Absorvido pelo cockpit |
| Connection pills expandidas | `.hero-connection-pill` (versão 126px) | Substituído por dots compactos |

---

## 8. O que NÃO tocar

- Todo o JavaScript em `app.js` — zero alterações
- IDs usados para data binding no `app.js`
- Outras seções da app (Roteiro, Cases, Customização, Pre Plan, etc.)
- Sistema de save/load/import/export

---

## 9. Checklist final

- [ ] Topbar em uma linha, altura 52px
- [ ] KPI row: 7 tiles em grid horizontal sem quebra
- [ ] Tiles com problema têm borda esquerda colorida
- [ ] Layout principal: 280px (prioridade) + flex (cockpit)
- [ ] Cockpit: tabela com 5 colunas alinhadas
- [ ] "Distribuição por status" removido
- [ ] "Carga por SP" removido
- [ ] Tabela de projetos: 7 colunas, grid alinhado no header e linhas
- [ ] Botões de ação: Save / Mark reviewed / Open empilhados
- [ ] Nenhum `!important` novo introduzido
- [ ] Todos os IDs do app.js preservados
