import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import { FrenteBadge } from "@/components/FrenteBadge";
import { CompletionRing } from "@/components/CompletionRing";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { fmtRelative } from "@/lib/format";
import { apiFrenteToFrente, isClosedThesis } from "@/types/domain";
import { B3Panel } from "@/components/panels/B3Panel";
import { CriptoPanel } from "@/components/panels/CriptoPanel";
import { ImovelDossie } from "@/components/panels/ImovelDossie";

export default function TeseDetalhe() {
  const { id = "" } = useParams();
  const { data: t, isLoading } = useQuery({ queryKey: ["tese", id], queryFn: () => api.tese(id) });

  if (isLoading) return <div className="h-64 rounded-xl bg-surface-1 animate-pulse" />;
  if (!t) return <div className="glass-card p-6">Tese nao encontrada.</div>;

  const timingLabel = isClosedThesis(t)
    ? `encerrada ${fmtRelative(t.closed_at ?? t.updated_at)}`
    : `aberta ${fmtRelative(t.opened_at)}`;

  return (
    <div className="space-y-5 animate-fade-up">
      <Link to="/teses" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="w-4 h-4" /> Teses
      </Link>

      <header className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <h1 className="font-display text-2xl font-semibold truncate">{t.asset_label}</h1>
            <FrenteBadge frente={apiFrenteToFrente(t.front)} />
          </div>
          <CompletionRing pct={t.completion.completion_pct} size={32} />
        </div>
        {t.title && <p className="text-sm text-muted-foreground">{t.title}</p>}
        <div className="flex items-center justify-between">
          <StatusPill status={t.status} />
          <span className="text-xs text-muted-foreground">{timingLabel}</span>
        </div>
        <FreshnessBadge
          status={t.data_quality.freshness_status}
          lastUpdateAt={t.data_quality.last_update_at}
          confidencePct={t.data_quality.confidence_in_data_pct}
        />
      </header>

      {t.front === "b3" && <B3Panel t={t} />}
      {t.front === "cripto" && <CriptoPanel t={t} />}
      {t.front === "imoveis" && <ImovelDossie t={t} />}

      {t.suggested_action && (
        <div className="rounded-lg bg-primary/8 border border-primary/30 p-3 text-sm text-primary">
          <span className="text-[10px] uppercase tracking-wider opacity-80 block mb-0.5">Acao sugerida</span>
          {t.suggested_action}
        </div>
      )}
    </div>
  );
}
