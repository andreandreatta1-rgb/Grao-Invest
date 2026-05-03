(() => {
  if (!window.React || !window.ReactDOM) return;
  const { useEffect, useMemo, useState } = window.React;
  const C = {
    bg: "#070b14", panel: "#0c1120", card: "#101828", border: "#1a2540",
    line: "#1e2d4a", gold: "#c8a444", teal: "#00c896", sky: "#3b9eff",
    coral: "#ff5e5e", amber: "#f5a623", green: "#22c55e", text: "#e2eaf8",
    muted: "#5a7090", dim: "#2e4060",
  };
  const mono = "'JetBrains Mono', 'Fira Code', monospace";
  const emptyForm = {
    title: "", source_url: "", origin: "Venda direta vendedor", strategy: "House flipping",
    city: "", neighborhood: "", property_type: "Apartamento", asking_price: "",
    appraisal_value: "", market_value_estimate: "", estimated_sale_conservative: "",
    estimated_sale_base: "", estimated_sale_optimistic: "", estimated_rent_conservative: "",
    renovation_type: "leve", renovation_budget: "", carrying_months: "6",
    monthly_carrying_cost: "", acquisition_costs: "", selling_commission_pct: "6",
    cash_needed: "", occupancy_status: "desconhecido", has_registration: false,
    condo_debt_known: false, iptu_debt_known: false, accepts_financing: false,
    financing_validated: false, sale_comparables_count: "0", rent_comparables_count: "0",
    first_operation: true, plan_a: "Revender apos validacao e ajuste leve.", plan_b: "",
    plan_c: "Sair no zero se a tese nao se confirmar.", notes: "",
  };
  const inputStyle = { background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, color: C.text, padding: "10px 11px", fontSize: 12, outline: "none", fontFamily: "inherit" };
  const buttonStyle = { background: C.gold, color: "#120d05", border: "none", borderRadius: 10, padding: "10px 14px", fontSize: 12, fontWeight: 800, cursor: "pointer", fontFamily: "inherit" };
  const toNumber = (value) => Number(String(value || "0").replace(",", ".")) || 0;
  const money = (value) => Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const scoreColor = (score) => score >= 80 ? C.green : score >= 60 ? C.amber : C.coral;
  const statusTone = (status) => {
    const value = String(status || "").toLowerCase();
    if (value.includes("forte") || value.includes("diligencia")) return "success";
    if (value.includes("descart")) return "danger";
    if (value.includes("pend")) return "warning";
    return "info";
  };
  const authHeaders = () => {
    const token = window.localStorage?.getItem("ia_session_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };
  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { Accept: "application/json", "Content-Type": "application/json", ...authHeaders(), ...(options.headers || {}) },
    });
    if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
    return response.json();
  }
  function Badge({ label, tone = "neutral" }) {
    const tones = {
      success: { bg: C.green + "20", color: C.green, border: C.green + "44" },
      warning: { bg: C.amber + "20", color: C.amber, border: C.amber + "44" },
      danger: { bg: C.coral + "20", color: C.coral, border: C.coral + "44" },
      info: { bg: C.sky + "20", color: C.sky, border: C.sky + "44" },
      neutral: { bg: C.dim + "60", color: C.muted, border: C.dim },
    };
    const s = tones[tone] || tones.neutral;
    return <span style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}`, fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 8, letterSpacing: "0.04em", textTransform: "uppercase", fontFamily: mono, whiteSpace: "nowrap" }}>{label}</span>;
  }
  function Field({ label, name, form, setForm, children }) {
    return <label style={{ display: "flex", flexDirection: "column", gap: 6, color: C.muted, fontSize: 11 }}>{label}{children || <input value={form[name]} onChange={(event) => setForm((current) => ({ ...current, [name]: event.target.value }))} style={inputStyle} />}</label>;
  }
  function CandidateCard({ candidate, onRefresh }) {
    const analysis = candidate.analysis || {};
    const pending = Array.isArray(analysis.pending_items) ? analysis.pending_items : [];
    const base = analysis.scenarios?.base || {};
    const patch = async (body) => { await api(`/api/real-estate/candidates/${candidate.id}`, { method: "PATCH", body: JSON.stringify(body) }); await onRefresh(); };
    const discard = async () => { await api(`/api/real-estate/candidates/${candidate.id}/discard`, { method: "POST", body: JSON.stringify({ reason: "Descartado pelo Radar durante triagem." }) }); await onRefresh(); };
    return <article style={{ background: C.card, border: `1px solid ${C.border}`, borderLeft: `3px solid ${scoreColor(analysis.score || 0)}`, borderRadius: 14, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div><div style={{ color: C.text, fontSize: 15, fontWeight: 800 }}>{candidate.title}</div><div style={{ color: C.muted, fontSize: 11, marginTop: 4 }}>{[candidate.origin, candidate.strategy, candidate.neighborhood || candidate.city].filter(Boolean).join(" | ")}</div></div>
        <Badge label={candidate.status || analysis.suggested_status || "Radar"} tone={statusTone(candidate.status || analysis.suggested_status)} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 }}>
        {[{ label: "Score", value: `${analysis.score || 0}/100`, color: scoreColor(analysis.score || 0) }, { label: "Confianca", value: `${analysis.confidence || 0}%`, color: C.sky }, { label: "Lucro base", value: money(base.net_profit), color: Number(base.net_profit || 0) >= 0 ? C.teal : C.coral }, { label: "Caixa", value: money(analysis.cash_needed), color: C.gold }].map((item) => <div key={item.label} style={{ background: C.panel, borderRadius: 10, padding: "9px 10px" }}><div style={{ color: C.muted, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>{item.label}</div><div style={{ color: item.color, fontSize: 14, fontWeight: 800, fontFamily: mono, marginTop: 4 }}>{item.value}</div></div>)}
      </div>
      <div style={{ background: C.panel, borderRadius: 10, padding: "10px 12px" }}><div style={{ color: C.gold, fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase" }}>Proxima acao</div><div style={{ color: C.text, fontSize: 13, marginTop: 5 }}>{analysis.next_action || "Comparar com outros candidatos"}</div></div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {pending.length ? pending.slice(0, 4).map((item) => <div key={`${candidate.id}-${item.title}`} style={{ display: "flex", justifyContent: "space-between", gap: 8, color: C.muted, fontSize: 11, borderBottom: `1px solid ${C.line}`, paddingBottom: 6 }}><span>{item.title}</span><Badge label={item.priority} tone={item.priority === "P0" ? "danger" : "warning"} /></div>) : <div style={{ color: C.green, fontSize: 12 }}>Sem pendencias P0/P1 abertas.</div>}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" style={{ ...buttonStyle, background: C.sky, color: "#06101f" }} onClick={() => patch({ occupancy_status: "desocupado" })}>Confirmar desocupado</button>
        <button type="button" style={{ ...buttonStyle, background: C.teal, color: "#03150f" }} onClick={() => patch({ has_registration: true, condo_debt_known: true, iptu_debt_known: true })}>Docs/dividas OK</button>
        <button type="button" style={{ ...buttonStyle, background: C.coral, color: "#190606" }} onClick={discard}>Descartar</button>
      </div>
    </article>;
  }
  function RealEstateRadar() {
    const [form, setForm] = useState(emptyForm);
    const [payload, setPayload] = useState({ summary: { total: 0 }, items: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    useEffect(() => {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap";
      document.head.appendChild(link);
      return () => link.remove();
    }, []);
    const load = async () => { setLoading(true); try { setPayload(await api("/api/real-estate/candidates")); setError(""); } catch (err) { setError(String(err?.message || "Falha ao carregar Radar")); } finally { setLoading(false); } };
    useEffect(() => { void load(); }, []);
    const candidates = Array.isArray(payload.items) ? payload.items : [];
    const summary = useMemo(() => {
      const strong = candidates.filter((item) => String(item.status || "").toLowerCase().includes("forte")).length;
      const discarded = candidates.filter((item) => String(item.status || "").toLowerCase().includes("descart")).length;
      const avgScore = candidates.length ? Math.round(candidates.reduce((acc, item) => acc + Number(item.analysis?.score || 0), 0) / candidates.length) : 0;
      return { total: candidates.length, strong, discarded, avgScore };
    }, [candidates]);
    const fillExample = () => setForm({ ...emptyForm, title: "Apto Sao Miguel Caixa", source_url: "https://www.leilaoimovel.com.br/", origin: "Leilao Caixa", strategy: "Revenda rapida", city: "Sao Paulo", neighborhood: "Sao Miguel Paulista", asking_price: "139015.11", appraisal_value: "230000", market_value_estimate: "200000", estimated_sale_conservative: "180000", estimated_sale_base: "200000", renovation_budget: "12000", monthly_carrying_cost: "1500", acquisition_costs: "8500", cash_needed: "85000", sale_comparables_count: "1", plan_b: "Alugar se a venda demorar." });
    const submit = async (event) => {
      event.preventDefault();
      const body = { ...form, asking_price: toNumber(form.asking_price), appraisal_value: toNumber(form.appraisal_value), market_value_estimate: toNumber(form.market_value_estimate), estimated_sale_conservative: toNumber(form.estimated_sale_conservative), estimated_sale_base: toNumber(form.estimated_sale_base), estimated_sale_optimistic: toNumber(form.estimated_sale_optimistic), estimated_rent_conservative: toNumber(form.estimated_rent_conservative), renovation_budget: toNumber(form.renovation_budget), carrying_months: toNumber(form.carrying_months), monthly_carrying_cost: toNumber(form.monthly_carrying_cost), acquisition_costs: toNumber(form.acquisition_costs), selling_commission_pct: toNumber(form.selling_commission_pct), cash_needed: toNumber(form.cash_needed), sale_comparables_count: toNumber(form.sale_comparables_count), rent_comparables_count: toNumber(form.rent_comparables_count) };
      await api("/api/real-estate/candidates", { method: "POST", body: JSON.stringify(body) });
      setForm(emptyForm);
      await load();
    };
    return <div style={{ background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 18, padding: 22, fontFamily: "Sora, system-ui, sans-serif", display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div><div style={{ color: C.gold, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", fontWeight: 800 }}>Imoveis e Projetos</div><h2 style={{ margin: "8px 0 6px", fontSize: 26, letterSpacing: "-0.03em" }}>Radar Imobiliario</h2><p style={{ color: C.muted, fontSize: 13, lineHeight: 1.5, margin: 0, maxWidth: 760 }}>Cadastre candidatos, veja score parcial, confianca e pendencias que impedem uma decisao real.</p></div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}><button type="button" style={{ ...buttonStyle, background: C.panel, color: C.gold, border: `1px solid ${C.gold}44` }} onClick={fillExample}>Usar exemplo</button><button type="button" style={buttonStyle} onClick={load}>Atualizar</button></div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 10 }}>
        {[{ label: "Candidatos", value: summary.total, color: C.text }, { label: "Score medio", value: `${summary.avgScore}/100`, color: scoreColor(summary.avgScore) }, { label: "Fortes", value: summary.strong, color: C.green }, { label: "Descartados", value: summary.discarded, color: C.coral }].map((item) => <div key={item.label} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: "14px 16px" }}><div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>{item.label}</div><div style={{ color: item.color, fontFamily: mono, fontWeight: 800, fontSize: 24, marginTop: 6 }}>{item.value}</div></div>)}
      </div>
      <form onSubmit={submit} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 16, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        <Field label="Nome do candidato" name="title" form={form} setForm={setForm} />
        <Field label="Link" name="source_url" form={form} setForm={setForm} />
        <Field label="Origem" name="origin" form={form} setForm={setForm}><select value={form.origin} onChange={(event) => setForm((current) => ({ ...current, origin: event.target.value }))} style={inputStyle}>{["Leilao Caixa", "Leilao judicial", "Banco / venda direta", "Venda direta vendedor", "Imovel na planta", "Off-market", "Outro"].map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Estrategia" name="strategy" form={form} setForm={setForm}><select value={form.strategy} onChange={(event) => setForm((current) => ({ ...current, strategy: event.target.value }))} style={inputStyle}>{["Revenda rapida", "House flipping", "Retrofit", "Aluguel", "Patrimonial", "Planta / ciclo medio", "Estudo apenas"].map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Cidade" name="city" form={form} setForm={setForm} />
        <Field label="Bairro" name="neighborhood" form={form} setForm={setForm} />
        <Field label="Preco compra" name="asking_price" form={form} setForm={setForm} />
        <Field label="Valor mercado" name="market_value_estimate" form={form} setForm={setForm} />
        <Field label="Venda conservadora" name="estimated_sale_conservative" form={form} setForm={setForm} />
        <Field label="Venda base" name="estimated_sale_base" form={form} setForm={setForm} />
        <Field label="Reforma" name="renovation_budget" form={form} setForm={setForm} />
        <Field label="Caixa necessario" name="cash_needed" form={form} setForm={setForm} />
        <Field label="Ocupacao" name="occupancy_status" form={form} setForm={setForm}><select value={form.occupancy_status} onChange={(event) => setForm((current) => ({ ...current, occupancy_status: event.target.value }))} style={inputStyle}><option value="desconhecido">desconhecido</option><option value="desocupado">desocupado</option><option value="ocupado">ocupado</option></select></Field>
        <Field label="Comparaveis venda" name="sale_comparables_count" form={form} setForm={setForm} />
        <Field label="Plano B" name="plan_b" form={form} setForm={setForm} />
        <div style={{ display: "flex", alignItems: "end" }}><button type="submit" style={{ ...buttonStyle, width: "100%" }}>Cadastrar candidato</button></div>
      </form>
      {error && <div style={{ color: C.coral, background: C.coral + "12", border: `1px solid ${C.coral}44`, borderRadius: 10, padding: 12 }}>{error}</div>}
      {loading && <div style={{ color: C.muted, fontSize: 12 }}>Carregando Radar...</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(330px, 1fr))", gap: 12 }}>{candidates.length ? candidates.map((candidate) => <CandidateCard key={candidate.id} candidate={candidate} onRefresh={load} />) : <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 18, color: C.muted }}>Nenhum candidato cadastrado ainda. Use o exemplo ou cadastre um imovel real para iniciar o funil.</div>}</div>
    </div>;
  }
  const rootNode = document.getElementById("real-estate-root");
  if (!rootNode) return;
  window.ReactDOM.createRoot(rootNode).render(<RealEstateRadar />);
})();
