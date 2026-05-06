import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, setApiBase, setForcedMock } from "./api";

describe("api cockpit loading", () => {
  beforeEach(() => {
    window.localStorage.clear();
    setForcedMock(false);
    setApiBase("https://grao-invest.vercel.app");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("continues to dashboard API when a legacy route returns the SPA html", async () => {
    const requestedUrls: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      requestedUrls.push(url);
      if (url.endsWith("/cockpit/resumo")) {
        return new Response("<!doctype html><div id=\"root\"></div>", {
          status: 200,
          headers: { "Content-Type": "text/html" },
        });
      }
      if (url.endsWith("/api/dashboard/summary/1")) {
        return Response.json({
          thesis_history_overview: {
            total_tested: 879,
            success_rate_pct: 67.5,
            expectancy_net_pct: 1.2,
            event_count: 1597,
          },
          historical_analysis_summary: {
            thesis_count: 879,
          },
        });
      }
      if (
        url.endsWith("/api/theses/current-monitor/latest") ||
        url.endsWith("/api/real-estate/candidates")
      ) {
        return Response.json({ detail: "not found" }, { status: 404 });
      }
      throw new Error(`Unexpected URL in test: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const cockpit = await api.cockpit();

    expect(cockpit.tesesTestadas).toBe(879);
    expect(cockpit.validacaoHistoricaPct).toBe(0.675);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://grao-invest.vercel.app/api/dashboard/summary/1",
      expect.any(Object),
    );
    expect(requestedUrls.some((url) => url.endsWith("/api/theses/current-monitor/latest"))).toBe(false);
  });

  it("does not replace a production cockpit timeout with mock data", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cockpit/resumo")) {
        return new Response("<!doctype html><div id=\"root\"></div>", {
          status: 200,
          headers: { "Content-Type": "text/html" },
        });
      }
      if (url.endsWith("/api/dashboard/summary/1")) {
        const error = new Error("aborted");
        error.name = "AbortError";
        throw error;
      }
      throw new Error(`Unexpected URL in test: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.cockpit()).rejects.toThrow("Timeout");
  });
});
