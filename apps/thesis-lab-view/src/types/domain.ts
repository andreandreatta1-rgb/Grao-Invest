// Tipos centrais do domínio Grão Invest.
// Contrato canônico: TheseEnvelope — toda tese (incluindo microtrades do Lab) segue este envelope.

export type Frente = "B3" | "Cripto" | "Imoveis";
export type FrenteApi = "b3" | "cripto" | "imoveis";

export type Direcao = "long" | "short" | "neutra";

export type StatusTese =
  | "preparando"
  | "confirmando"
  | "monitorando"
  | "validada"
  | "refutada"
  | "encerrada_tempo"
  | "encerrada_inatividade";

export type FreshnessStatus = "fresh" | "partial" | "stale" | "missing";

// Mapa de compatibilidade com o tipo legado SaudeDado usado por componentes existentes.
export type SaudeDado = "atualizado" | "parcial" | "indisponivel";
export const freshnessToSaude = (f: FreshnessStatus): SaudeDado =>
  f === "fresh" ? "atualizado" : f === "missing" ? "indisponivel" : "parcial";

export interface DataQuality {
  freshness_status: FreshnessStatus;
  last_update_at: string;          // ISO
  confidence_in_data_pct: number;  // 0..100
}

export interface Completion {
  is_complete: boolean;
  completion_pct: number;          // 0..100
  missing_fields: string[];
  pending_items: string[];
  next_required_action: string;
}

/**
 * Specifics por frente — campo `specific` do envelope.
 * Cada frente carrega seus atributos próprios; o envelope mantém os campos comuns.
 */
export interface SpecificMicrotrade {
  kind: "microtrade";
  window_min: number;
  expires_at: string;              // ISO
  last_tick_at: string;            // ISO
  is_data_delayed: boolean;
  trigger_pressure_pct: number;    // 0..100
  evidences: string[];
  short_thesis_summary?: string;
}

export type Direction = "long" | "short" | "neutra";

export interface TechSignal {
  label: string;
  value?: string;
  bias: "bull" | "bear" | "neutral";
}

export interface FundamentalItem {
  label: string;
  value: string;
  trend?: "up" | "down" | "flat";
}

export interface NewsItem {
  title: string;
  source: string;
  published_at: string; // ISO
  sentiment?: "positivo" | "negativo" | "neutro";
  url?: string;
}

export interface SpecificB3 {
  kind: "b3";
  ticker: string;
  direction: Direction;
  evidences: string[];
  technicals: TechSignal[];
  fundamentals: FundamentalItem[];
  news: NewsItem[];
  invalidation_detail?: string;
}

export type ImovelStrategy = "flip" | "buy_and_hold" | "renda" | "valorizacao" | "arbitragem";
export type ImovelStatus = "prospeccao" | "diligencia" | "negociacao" | "fechado" | "descartada";
export type DiligenceState = "ok" | "pendente" | "nao_validado" | "faltando" | "alerta";

export interface DiligenceItem {
  label: string;
  state: DiligenceState;
  detail?: string;
}

export interface ImovelScenario {
  label: string;
  sale_value?: number;
  rent_value?: number;
  roi_pct?: number;
  prazo_meses?: number;
}

export interface SpecificImovel {
  kind: "imovel";
  // Resumo
  source_url?: string;
  origin?: string;
  strategy?: ImovelStrategy;
  city?: string;
  neighborhood?: string;
  property_type?: string;
  imovel_status?: ImovelStatus;
  score_pct?: number;       // 0..100
  next_step?: string;

  // Valores
  asking_price?: number;
  appraisal_value?: number;
  market_value_estimate?: number;
  ceiling_price?: number;
  cash_needed?: number;
  renovation_budget?: number;
  carrying_months?: number;
  monthly_carrying_cost?: number;

  // Comparáveis
  sale_comparables_count?: number;
  rent_comparables_count?: number;

  // Cenários
  estimated_sale_conservative?: number;
  estimated_sale_base?: number;
  estimated_sale_optimistic?: number;
  estimated_rent_conservative?: number;
  roi_estimated_pct?: number;
  prazo_estimado_meses?: number;

  // Risco / documentação
  accepts_financing?: boolean;
  financing_validated?: boolean;
  diligence: DiligenceItem[];

  // Plano
  plan_a?: string;
  plan_b?: string;
  plan_c?: string;
  exit_rule?: string;
  notes?: string;
  analysis?: string;

  evidences?: string[];
}

export type TheseSpecific = SpecificMicrotrade | SpecificB3 | SpecificImovel | Record<string, never>;

/**
 * Envelope canônico de uma tese (também usada para microtrades do Lab).
 * Todos os campos seguem snake_case conforme contrato com o backend.
 */
export interface TheseEnvelope {
  id: string;
  front: FrenteApi;
  title: string;
  asset_label: string;
  hypothesis: string;
  status: StatusTese;
  opened_at: string;               // ISO
  updated_at: string;              // ISO
  closed_at?: string;              // ISO

  expected_result_pct: number;     // % esperada
  current_result_pct: number;      // % real corrente
  confidence_pct: number;          // 0..100

  entry_value: number;
  current_value: number;
  target_value: number;
  stop_or_invalidation: string;    // texto descritivo de invalidação
  stop_value?: number;             // opcional, quando aplicável

  suggested_action: string;
  learning_note: string;

  data_quality: DataQuality;
  specific: TheseSpecific;
  completion: Completion;
}

export const CLOSED_THESE_STATUSES: StatusTese[] = [
  "validada",
  "refutada",
  "encerrada_tempo",
  "encerrada_inatividade",
];

export const isClosedStatus = (status: StatusTese): boolean =>
  CLOSED_THESE_STATUSES.includes(status);

export const isOpenStatus = (status: StatusTese): boolean =>
  !isClosedStatus(status);

export const isClosedThesis = (
  thesis: Pick<TheseEnvelope, "status" | "closed_at">,
): boolean => isClosedStatus(thesis.status) || Boolean(thesis.closed_at);

export const isOpenThesis = (
  thesis: Pick<TheseEnvelope, "status" | "closed_at">,
): boolean => !isClosedThesis(thesis);

// Helpers de mapeamento para componentes legados (Frente capitalizada).
export const apiFrenteToFrente = (f: FrenteApi): Frente =>
  f === "b3" ? "B3" : f === "cripto" ? "Cripto" : "Imoveis";

// ---------- Tipos auxiliares (não-tese) ----------

export interface CockpitResumo {
  tesesTestadas: number;
  validacaoHistoricaPct: number;
  expectativaLiquidaMedia: number;
  tesesAtivas: number;
  aprendizadosAplicados: number;
  ultimaAtualizacao: string;
  frentes: Record<Frente, { ativas: number; saude: SaudeDado; ultimaIngestaoEm: string }>;
}

export type DecisaoStatus = "pendente" | "aceita" | "rejeitada" | "em_andamento" | "concluida";
export type DecisaoTipo = "sugestao_tese" | "alerta_revisao" | "confirmacao_hipotese" | "mensagem";

export interface Decisao {
  id: string;
  tipo: DecisaoTipo;
  titulo: string;
  resumo: string;
  criadaEm: string;
  status: DecisaoStatus;
  ativoRelacionado?: string;
  frente?: Frente;
}

export interface AtivoMercado {
  ticker: string;
  nome: string;
  frente: Frente;
  preco: number;
  variacao: number;
  destaque?: boolean;
}

export interface FonteDados {
  nome: string;
  frente: Frente;
  ultimaAtualizacao: string;
  saude: SaudeDado;
}
