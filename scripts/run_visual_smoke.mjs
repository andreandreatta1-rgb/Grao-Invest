import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const require = createRequire(import.meta.url);

function loadPlaywright() {
  try {
    return require("playwright");
  } catch (error) {
    const hint = [
      "Playwright nao foi encontrado.",
      "Local: rode scripts/run_visual_smoke.ps1, que aponta para o runtime empacotado.",
      "CI: rode npm install --no-save playwright && npx playwright install chromium.",
      `Erro original: ${error instanceof Error ? error.message : String(error)}`,
    ].join(" ");
    throw new Error(hint);
  }
}

const { chromium } = loadPlaywright();

const baseUrl = (process.env.VISUAL_SMOKE_BASE_URL || "https://grao-invest.vercel.app").replace(/\/$/, "");
const outputDir = path.resolve(
  process.env.VISUAL_SMOKE_OUTPUT_DIR || "data/reports/visual-smoke",
);
const maxScreens = Number(process.env.VISUAL_SMOKE_MAX_SCREENS || 0);
const strictMobile = process.env.VISUAL_SMOKE_STRICT_MOBILE === "1";
const appReadyTimeoutMs = Number(process.env.VISUAL_SMOKE_READY_TIMEOUT_MS || 60_000);

const viewports = [
  { id: "desktop", width: 1366, height: 768, required: true },
  { id: "notebook", width: 1280, height: 720, required: true },
  { id: "mobile", width: 390, height: 844, required: strictMobile },
];

const screens = [
  {
    id: "dashboard",
    labels: [],
    expectedAny: ["Teses testadas", "Placar científico", "879"],
    requiredAll: ["879"],
    forbidden: ["1.727", "total_tested:1727"],
  },
  {
    id: "teses",
    labels: ["Teses"],
    expectedAny: ["Lista de teses", "Ficha completa", "thesis_open_operations", "Teses"],
  },
  {
    id: "mercado",
    labels: ["Mercado"],
    expectedAny: ["Confiança Halley", "Mesa", "Ativos monitorados", "Mercado"],
  },
  {
    id: "backtest",
    labels: ["Backtest", "Validação"],
    expectedAny: ["Laboratório do Método", "Evolução do método", "Cal.18", "Validação"],
  },
  {
    id: "risco",
    labels: ["Risco"],
    expectedAny: ["Exposição", "Limite total", "corda bamba", "Risco"],
  },
  {
    id: "alertas",
    labels: ["Alertas"],
    expectedAny: ["Primeiro movimento", "Partitura", "alerta crítico", "Alertas"],
  },
  {
    id: "aprendizado",
    labels: ["Aprendizado"],
    expectedAny: ["Grande Obra", "Gap", "Cal.18", "Aprendizado"],
  },
  {
    id: "metodo",
    labels: ["Método", "Metodo"],
    expectedAny: ["Método", "Jornada", "Marca", "Grão"],
  },
];

const globalForbidden = [
  "Monitor congelado",
  "Feed temporariamente indisponível",
  "Application error",
  "Cannot read properties",
  "Minified React error",
  "undefined",
  "NaN",
];

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function hasToken(text, token) {
  return normalizeText(text).includes(normalizeText(token));
}

function slug(value) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

async function textIncludesAny(page, candidates) {
  const body = await page.locator("body").innerText({ timeout: 10_000 });
  return candidates.some((candidate) => hasToken(body, candidate));
}

async function bodyText(page) {
  return page.locator("body").innerText({ timeout: 10_000 }).catch(() => "");
}

async function warmDashboardApi() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20_000);
  try {
    const response = await fetch(`${baseUrl}/api/dashboard/summary/1?visual_smoke=${Date.now()}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    const payload = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      total_tested: payload?.thesis_history_overview?.total_tested ?? null,
      open_operations: Array.isArray(payload?.thesis_open_operations)
        ? payload.thesis_open_operations.length
        : null,
    };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function waitForAppReady(page, screen) {
  const startedAt = Date.now();
  let latestBody = "";

  while (Date.now() - startedAt < appReadyTimeoutMs) {
    latestBody = await bodyText(page);
    const loading = hasToken(latestBody, "Carregando laboratório científico");
    if (!loading) return;
    await page.waitForTimeout(500);
  }

  throw new Error(
    `Tela ficou em loading por ${Math.round(appReadyTimeoutMs / 1000)}s. ` +
      `Trecho visivel: ${latestBody.slice(0, 260).replace(/\s+/g, " ")}`,
  );
}

async function activateScreen(page, screen) {
  if (!screen.labels.length) return;

  for (const label of screen.labels) {
    const locator = page.getByText(label, { exact: true });
    if ((await locator.count()) > 0) {
      await locator.first().click({ timeout: 5_000 });
      return;
    }
  }

  throw new Error(`Nao encontrei navegacao para a tela ${screen.id}`);
}

async function waitForScreen(page, screen) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 20_000) {
    if (await textIncludesAny(page, screen.expectedAny)) return;
    await page.waitForTimeout(300);
  }
  throw new Error(
    `A tela ${screen.id} nao exibiu nenhum texto esperado: ${screen.expectedAny.join(", ")}`,
  );
}

async function collectLayoutDiagnostics(page) {
  return page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const rows = [...document.querySelectorAll("*")]
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return {
          tag: el.tagName.toLowerCase(),
          id: el.id || "",
          className: typeof el.className === "string" ? el.className.slice(0, 120) : "",
          text: (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 120),
          rect: {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          overflowX: style.overflowX,
          position: style.position,
        };
      })
      .filter((row) => row.rect.width > viewportWidth + 4 || row.scrollWidth > row.clientWidth + 4)
      .sort((a, b) => Math.max(b.rect.width, b.scrollWidth) - Math.max(a.rect.width, a.scrollWidth))
      .slice(0, 10);

    return {
      viewportWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      widest: rows,
    };
  });
}

async function inspectPage(page, screen) {
  const body = await page.locator("body").innerText({ timeout: 10_000 });
  const forbidden = [...globalForbidden, ...(screen.forbidden || [])]
    .filter((token) => hasToken(body, token));
  if (forbidden.length) {
    throw new Error(`Texto proibido encontrado em ${screen.id}: ${forbidden.join(", ")}`);
  }

  const missing = (screen.requiredAll || []).filter((token) => !hasToken(body, token));
  if (missing.length) {
    throw new Error(`Texto obrigatorio ausente em ${screen.id}: ${missing.join(", ")}`);
  }

  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    bodyClientWidth: document.body.clientWidth,
  }));
  const overflow = Math.max(layout.scrollWidth - layout.clientWidth, layout.bodyScrollWidth - layout.bodyClientWidth);
  if (overflow > 4) {
    const error = new Error(`Overflow horizontal de ${overflow}px em ${screen.id}`);
    error.diagnostics = await collectLayoutDiagnostics(page);
    throw error;
  }

  return {
    bodyLength: body.length,
    overflow,
  };
}

async function run() {
  await mkdir(outputDir, { recursive: true });
  const apiWarmup = await warmDashboardApi();
  const browser = await chromium.launch({ headless: true });
  const report = {
    status: "ok",
    baseUrl,
    outputDir,
    generatedAt: new Date().toISOString(),
    apiWarmup,
    results: [],
  };

  const selectedScreens = maxScreens > 0 ? screens.slice(0, maxScreens) : screens;

  try {
    for (const viewport of viewports) {
      const page = await browser.newPage({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: 1,
        isMobile: viewport.id === "mobile",
      });
      page.setDefaultTimeout(12_000);
      const consoleEvents = [];
      const requestFailures = [];
      page.on("console", (message) => {
        if (["error", "warning", "warn"].includes(message.type())) {
          consoleEvents.push({
            type: message.type(),
            text: message.text().slice(0, 300),
          });
        }
      });
      page.on("requestfailed", (request) => {
        requestFailures.push({
          url: request.url().slice(0, 300),
          failure: request.failure()?.errorText || "request failed",
        });
      });
      await page.addInitScript(() => {
        window.localStorage.setItem("graoinvest.metodo_onboarding_seen", "1");
      });

      for (const screen of selectedScreens) {
        const result = {
          viewport: viewport.id,
          screen: screen.id,
          status: "ok",
          severity: viewport.required ? "required" : "warning",
          screenshot: "",
          error: "",
          checks: {},
          diagnostics: {},
        };

        try {
          consoleEvents.length = 0;
          requestFailures.length = 0;
          await page.goto(`${baseUrl}/?visual-smoke=${Date.now()}-${viewport.id}-${screen.id}`, {
            waitUntil: "domcontentloaded",
            timeout: 30_000,
          });
          await page.waitForLoadState("load", { timeout: 30_000 });
          await waitForAppReady(page, screen);

          await activateScreen(page, screen);
          await waitForScreen(page, screen);
          result.checks = await inspectPage(page, screen);
          result.checks.consoleWarnings = consoleEvents.length;
          result.checks.requestFailures = requestFailures.length;

          const filename = `${viewport.id}-${slug(screen.id)}.png`;
          const screenshotPath = path.join(outputDir, filename);
          await page.screenshot({ path: screenshotPath, fullPage: true });
          result.screenshot = screenshotPath;
        } catch (error) {
          result.status = viewport.required ? "fail" : "warn";
          result.error = error instanceof Error ? error.message : String(error);
          result.diagnostics = {
            consoleEvents: consoleEvents.slice(-10),
            requestFailures: requestFailures.slice(-10),
            layout: error?.diagnostics || (await collectLayoutDiagnostics(page).catch(() => null)),
          };
          if (viewport.required) {
            report.status = "fail";
          }
          const filename = `${viewport.id}-${slug(screen.id)}-error.png`;
          const screenshotPath = path.join(outputDir, filename);
          await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
          result.screenshot = screenshotPath;
        }

        report.results.push(result);
      }

      await page.close();
    }
  } finally {
    await browser.close();
  }

  const reportPath = path.join(outputDir, "visual-smoke-report.json");
  await writeFile(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify({ ...report, reportPath }, null, 2));

  if (report.status !== "ok") {
    process.exitCode = 1;
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
