import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  api, getApiBase, setApiBase, getToken, setToken,
  isForcedMock, setForcedMock, isMock,
} from "@/lib/api";
import { ArrowLeft, CheckCircle2, Plug, RefreshCw, ShieldAlert, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Configuracao() {
  const qc = useQueryClient();
  const [base, setBase] = useState(getApiBase() ?? "");
  const [token, setTokenState] = useState(getToken() ?? "");
  const [forceMock, setForceMockState] = useState(isForcedMock());
  const [pingState, setPingState] = useState<
    | { status: "idle" }
    | { status: "loading" }
    | { status: "ok"; latencyMs: number }
    | { status: "fail"; latencyMs: number; httpStatus?: number; error: string }
  >({ status: "idle" });

  function persist() {
    setApiBase(base || null);
    setToken(token || null);
    setForcedMock(forceMock);
    qc.invalidateQueries();
  }

  async function testar() {
    persist();
    setPingState({ status: "loading" });
    const r = await api.ping();
    if (r.ok) setPingState({ status: "ok", latencyMs: r.latencyMs });
    else setPingState({ status: "fail", latencyMs: r.latencyMs, httpStatus: r.status, error: r.error ?? "erro" });
  }

  const modoAtual = isMock() ? "Dados simulados (mock)" : "Backend real";

  return (
    <div className="space-y-5 animate-fade-up">
      <div className="flex items-center justify-between">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-4 h-4" /> Cockpit
        </Link>
        <Link to="/instalar" className="inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary-glow">
          Instalar app →
        </Link>
      </div>

      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold">Configuração da API</h1>
        <p className="text-sm text-muted-foreground">
          Conecte o app ao seu backend FastAPI. Use um túnel (cloudflared, ngrok, tailscale)
          se o backend ainda não tem URL pública.
        </p>
      </header>

      {/* Status atual */}
      <section className="glass-card p-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Modo atual</span>
          <span className={cn(
            "pill text-[11px]",
            isMock() ? "bg-accent/15 text-accent" : "bg-validated/15 text-validated"
          )}>
            <Plug className="w-3 h-3" /> {modoAtual}
          </span>
        </div>
        <div className="text-xs font-mono tabular text-foreground/80 break-all">
          {getApiBase() || "— sem URL configurada —"}
        </div>
      </section>

      {/* Form */}
      <section className="glass-card p-4 space-y-4">
        <div className="space-y-1.5">
          <label className="text-[10px] uppercase tracking-widest text-muted-foreground">URL base do backend</label>
          <input
            type="url"
            inputMode="url"
            placeholder="https://meu-backend.exemplo.com"
            value={base}
            onChange={(e) => setBase(e.target.value)}
            className="w-full rounded-lg bg-surface-1 border border-border/60 px-3 py-2.5 text-sm font-mono tabular focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <p className="text-[11px] text-muted-foreground">
            Sem barra final. Endpoints esperados: <span className="font-mono">/cockpit/resumo</span>, <span className="font-mono">/teses</span>, <span className="font-mono">/teses/:id</span>, <span className="font-mono">/microtrades/ativos</span>, <span className="font-mono">/decisoes</span>, <span className="font-mono">/mercado/ativos</span>, <span className="font-mono">/mercado/fontes</span>, <span className="font-mono">/health</span>.
          </p>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] uppercase tracking-widest text-muted-foreground">Token (Bearer JWT)</label>
          <input
            type="password"
            placeholder="opcional — eyJhbGciOi..."
            value={token}
            onChange={(e) => setTokenState(e.target.value)}
            className="w-full rounded-lg bg-surface-1 border border-border/60 px-3 py-2.5 text-sm font-mono tabular focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <p className="text-[11px] text-muted-foreground">
            Enviado como <span className="font-mono">Authorization: Bearer ...</span>. Cookies httpOnly também são enviados via <span className="font-mono">credentials: include</span>.
          </p>
        </div>

        <label className="flex items-start gap-3 rounded-lg bg-surface-1 border border-border/60 p-3 cursor-pointer">
          <input
            type="checkbox"
            checked={forceMock}
            onChange={(e) => setForceMockState(e.target.checked)}
            className="mt-1 accent-primary"
          />
          <span className="text-sm">
            Forçar modo mock
            <span className="block text-[11px] text-muted-foreground">
              Útil para demonstrar o app sem depender do backend.
            </span>
          </span>
        </label>

        <div className="flex gap-2">
          <button
            onClick={testar}
            className="flex-1 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold flex items-center justify-center gap-1.5 hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Testar conexão
          </button>
          <button
            onClick={() => { persist(); }}
            className="flex-1 py-2.5 rounded-lg bg-surface-2 text-foreground text-sm font-semibold hover:bg-surface-3 transition-colors"
          >
            Salvar
          </button>
        </div>

        {/* Resultado do ping */}
        {pingState.status !== "idle" && (
          <div className={cn(
            "rounded-lg border p-3 text-sm",
            pingState.status === "loading" && "bg-surface-1 border-border/60 text-muted-foreground",
            pingState.status === "ok" && "bg-validated/8 border-validated/30 text-validated",
            pingState.status === "fail" && "bg-refuted/8 border-refuted/30 text-refuted",
          )}>
            {pingState.status === "loading" && (
              <span className="flex items-center gap-2"><RefreshCw className="w-4 h-4 animate-spin" /> Testando /health…</span>
            )}
            {pingState.status === "ok" && (
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> Conectado · {pingState.latencyMs}ms
              </span>
            )}
            {pingState.status === "fail" && (
              <div className="space-y-1">
                <span className="flex items-center gap-2 font-semibold">
                  <XCircle className="w-4 h-4" /> Falhou {pingState.httpStatus ? `· HTTP ${pingState.httpStatus}` : ""}
                </span>
                <span className="block text-[12px] font-mono tabular text-foreground/70 break-all">{pingState.error}</span>
                <span className="block text-[11px] text-muted-foreground">
                  Verifique CORS no FastAPI ({"Access-Control-Allow-Origin"}), URL acessível e (se usar cookies) <span className="font-mono">allow_credentials=True</span>.
                </span>
              </div>
            )}
          </div>
        )}
      </section>

      {/* CORS guide */}
      <section className="glass-card p-4 space-y-2">
        <h3 className="flex items-center gap-2 font-display text-sm font-semibold">
          <ShieldAlert className="w-4 h-4 text-pending" /> Lembretes para o backend
        </h3>
        <ul className="text-xs text-muted-foreground leading-relaxed space-y-1.5 list-disc pl-5">
          <li>Habilitar CORS no FastAPI permitindo a origem deste app (preview Lovable e domínio publicado).</li>
          <li>Endpoint <span className="font-mono text-foreground/80">GET /health</span> retornando 200 para o teste de conexão.</li>
          <li>Respostas devem seguir o envelope <span className="font-mono text-foreground/80">TheseEnvelope</span> (snake_case).</li>
          <li>Para túnel local: <span className="font-mono">cloudflared tunnel --url http://localhost:8000</span>.</li>
        </ul>
      </section>
    </div>
  );
}
