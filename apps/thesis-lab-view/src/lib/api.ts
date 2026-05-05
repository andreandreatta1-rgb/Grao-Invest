import type {
  AtivoMercado,
  CockpitResumo,
  DataHealthSnapshot,
  Decisao,
  FonteDados,
  TheseEnvelope,
} from "@/types/domain";
import type { MicrotradesAutopilotLatest } from "./backend-adapters";
import {
  adaptAssistantDecisions,
  adaptCockpitFromData,
  adaptCurrentMonitorTheses,
  adaptDataHealthFromCurrentMonitor,
  adaptFontesFromTeses,
  adaptMarketAssetsFromTeses,
  adaptMicrotradesAutopilotLatest,
  adaptRealEstateCandidates,
  getConfiguredUserId,
  synthesizeDecisionsFromTeses,
  type BackendAssistantDecisionInbox,
  type BackendCurrentMonitorPayload,
  type BackendDashboardSummary,
  type BackendMicrotradesAutopilotLatestPayload,
  type BackendRealEstateCandidatesResponse,
} from "./backend-adapters";
import {
  mockCockpit,
  mockDecisoes,
  mockFontes,
  mockMercado,
  mockMicrotrades,
  mockTeses,
} from "./mocks";

const LS_BASE = "graoinvest.api_base";
const LS_TOKEN = "graoinvest.token";
const LS_USE_MOCK = "graoinvest.use_mock";
const DEFAULT_TIMEOUT_MS = 12_000;

export class ApiError extends Error {
  status: number;
  path: string;
  body?: unknown;

  constructor(path: string, status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.path = path;
    this.status = status;
    this.body = body;
  }
}

function readLS(key: string): string | undefined {
  try {
    const value = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    return value ?? undefined;
  } catch {
    return undefined;
  }
}

export function getApiBase(): string | undefined {
  return readLS(LS_BASE) || (import.meta.env.VITE_API_BASE_URL as string | undefined) || undefined;
}

export function setApiBase(url: string | null) {
  try {
    if (url && url.trim()) window.localStorage.setItem(LS_BASE, url.trim().replace(/\/$/, ""));
    else window.localStorage.removeItem(LS_BASE);
  } catch {
    // noop
  }
}

export function getToken(): string | undefined {
  return readLS(LS_TOKEN);
}

export function setToken(token: string | null) {
  try {
    if (token && token.trim()) window.localStorage.setItem(LS_TOKEN, token.trim());
    else window.localStorage.removeItem(LS_TOKEN);
  } catch {
    // noop
  }
}

export function isForcedMock(): boolean {
  return readLS(LS_USE_MOCK) === "1";
}

export function setForcedMock(on: boolean) {
  try {
    if (on) window.localStorage.setItem(LS_USE_MOCK, "1");
    else window.localStorage.removeItem(LS_USE_MOCK);
  } catch {
    // noop
  }
}

export function isMock(): boolean {
  if (isForcedMock()) return true;
  return !getApiBase();
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const base = getApiBase();
  if (!base) throw new ApiError(path, 0, "VITE_API_BASE_URL nao definido");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };

  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const response = await fetch(`${base}${path}`, {
      ...init,
      headers,
      credentials: "include",
      signal: controller.signal,
    });

    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        // ignore
      }
      throw new ApiError(path, response.status, `API ${path} ${response.status}`, body);
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      throw new ApiError(path, 0, `Timeout (${timeoutMs}ms) em ${path}`);
    }
    if (error instanceof ApiError) {
      throw error;
    }
    const message = error instanceof Error ? error.message : `Falha de rede em ${path}`;
    throw new ApiError(path, 0, message);
  } finally {
    clearTimeout(timeout);
  }
}

async function tryRequest<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T | undefined> {
  try {
    return await request<T>(path, init, timeoutMs);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 405)) {
      return undefined;
    }
    throw error;
  }
}

function shouldFallbackToMock(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

async function withFallback<T>(label: string, fallback: T, loader: () => Promise<T>): Promise<T> {
  if (isMock()) return fallback;

  try {
    return await loader();
  } catch (error) {
    if (shouldFallbackToMock(error)) {
      console.warn(`[api] fallback mock em ${label}:`, (error as Error).message);
      return fallback;
    }
    throw error;
  }
}

async function loadDashboardSummary(): Promise<BackendDashboardSummary | undefined> {
  const userId = getConfiguredUserId();
  return tryRequest<BackendDashboardSummary>(`/api/dashboard/summary/${userId}`);
}

async function loadCurrentMonitor(): Promise<BackendCurrentMonitorPayload | undefined> {
  return tryRequest<BackendCurrentMonitorPayload>("/api/theses/current-monitor/latest");
}

async function loadRealEstateCandidates(): Promise<BackendRealEstateCandidatesResponse | undefined> {
  return tryRequest<BackendRealEstateCandidatesResponse>("/api/real-estate/candidates");
}

async function loadAdaptedTeses(): Promise<TheseEnvelope[]> {
  const [monitorPayload, realEstatePayload] = await Promise.all([
    loadCurrentMonitor(),
    loadRealEstateCandidates(),
  ]);

  const monitorTeses = monitorPayload ? adaptCurrentMonitorTheses(monitorPayload) : [];
  const realEstateTeses = realEstatePayload ? adaptRealEstateCandidates(realEstatePayload) : [];

  return [...monitorTeses, ...realEstateTeses].sort((a, b) =>
    new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

async function loadAdaptedDecisoes(): Promise<Decisao[]> {
  const canonical = await tryRequest<Decisao[]>("/decisoes");
  if (canonical?.length) return canonical;

  const inbox = await tryRequest<BackendAssistantDecisionInbox>("/api/assistant/decisions");
  const adapted = adaptAssistantDecisions(inbox);
  if (adapted.length) return adapted;

  const teses = await loadAdaptedTeses();
  return synthesizeDecisionsFromTeses(teses);
}

async function loadCockpitResumo(): Promise<CockpitResumo> {
  const canonical = await tryRequest<CockpitResumo>("/cockpit/resumo");
  if (canonical) return canonical;

  const [dashboard, teses] = await Promise.all([loadDashboardSummary(), loadAdaptedTeses()]);
  if (dashboard || teses.length) return adaptCockpitFromData(dashboard, teses);

  return mockCockpit();
}

async function loadAllTeses(): Promise<TheseEnvelope[]> {
  const canonical = await tryRequest<TheseEnvelope[]>("/teses");
  if (canonical?.length) return canonical;

  const adapted = await loadAdaptedTeses();
  return adapted.length ? adapted : mockTeses();
}

async function loadMicrotrades(): Promise<TheseEnvelope[]> {
  const canonical = await tryRequest<TheseEnvelope[]>("/microtrades/ativos");
  if (canonical?.length) return canonical;

  const monitorPayload = await loadCurrentMonitor();
  const adapted = monitorPayload
    ? adaptCurrentMonitorTheses(monitorPayload).filter((item) => item.front === "cripto")
    : [];

  return adapted.length ? adapted : mockMicrotrades();
}

async function loadMicrotradesAutopilotLatest(): Promise<MicrotradesAutopilotLatest | undefined> {
  const payload = await tryRequest<BackendMicrotradesAutopilotLatestPayload>("/api/microtrades/autopilot/latest");
  return adaptMicrotradesAutopilotLatest(payload);
}

async function loadMercado(): Promise<AtivoMercado[]> {
  const canonical = await tryRequest<AtivoMercado[]>("/mercado/ativos");
  if (canonical?.length) return canonical;

  const teses = await loadAllTeses();
  const adapted = adaptMarketAssetsFromTeses(teses);
  return adapted.length ? adapted : mockMercado();
}

async function loadFontes(): Promise<FonteDados[]> {
  const canonical = await tryRequest<FonteDados[]>("/mercado/fontes");
  if (canonical?.length) return canonical;

  const teses = await loadAllTeses();
  const adapted = adaptFontesFromTeses(teses);
  return adapted.length ? adapted : mockFontes();
}

async function loadDataHealth(): Promise<DataHealthSnapshot> {
  const monitor = await loadCurrentMonitor();
  return adaptDataHealthFromCurrentMonitor(monitor);
}

export const api = {
  cockpit: () => withFallback("/cockpit/resumo", mockCockpit(), loadCockpitResumo),

  teses: () => withFallback("/teses", mockTeses(), loadAllTeses),

  tese: async (id: string) =>
    withFallback<TheseEnvelope | undefined>(`/teses/${id}`, [...mockTeses(), ...mockMicrotrades()].find((item) => item.id === id), async () => {
      const canonical = await tryRequest<TheseEnvelope>(`/teses/${id}`);
      if (canonical) return canonical;
      const teses = await loadAllTeses();
      return teses.find((item) => item.id === id);
    }),

  microtrades: () => withFallback("/microtrades/ativos", mockMicrotrades(), loadMicrotrades),

  microtradesAutopilotLatest: () =>
    withFallback<MicrotradesAutopilotLatest | undefined>(
      "/api/microtrades/autopilot/latest",
      undefined,
      loadMicrotradesAutopilotLatest,
    ),

  decisoes: () => withFallback("/decisoes", mockDecisoes(), async () => {
    const adapted = await loadAdaptedDecisoes();
    return adapted;
  }),

  mercado: () => withFallback("/mercado/ativos", mockMercado(), loadMercado),

  fontes: () => withFallback("/mercado/fontes", mockFontes(), loadFontes),

  dataHealth: () => withFallback(
    "/api/theses/current-monitor/latest",
    adaptDataHealthFromCurrentMonitor(undefined),
    loadDataHealth,
  ),

  ping: async (): Promise<{ ok: boolean; latencyMs: number; status?: number; error?: string }> => {
    const startedAt = performance.now();
    try {
      await request<unknown>("/health", undefined, 5_000);
      return { ok: true, latencyMs: Math.round(performance.now() - startedAt) };
    } catch (error) {
      const apiError = error as ApiError;
      return {
        ok: false,
        latencyMs: Math.round(performance.now() - startedAt),
        status: apiError.status,
        error: apiError.message,
      };
    }
  },
};
