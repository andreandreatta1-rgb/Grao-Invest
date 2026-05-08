import { useCallback, useEffect, useState } from "react";
import { C, mono, Sidebar } from "./components";
import { useFonts } from "./hooks/useFonts.js";
import { fetchCockpitPayloads } from "./data/cockpitHalleyApi.js";
import { normalizeCockpitHalley } from "./data/cockpitHalleyAdapter.js";
import { withCockpitDataTrust } from "./data/dataTrust.js";
import Alertas from "./screens/Alertas.jsx";
import Aprendizado from "./screens/Aprendizado.jsx";
import Backtest from "./screens/Backtest.jsx";
import CockpitHalley from "./screens/CockpitHalley.jsx";
import Metodo from "./screens/Metodo.jsx";
import Mercado from "./screens/Mercado.jsx";
import Risco from "./screens/Risco.jsx";
import Saude from "./screens/Saude.jsx";
import Teses from "./screens/Teses.jsx";

const FEED_KEYS = ["dashboardSummary", "currentMonitor", "realEstateCandidates", "realEstateStrategyTerritoryCandidates"];
const UI_REVISION = "UI rev soul-4";
const BUILD_INFO_URL = "/api/frontend/version";
const DEFAULT_BUILD_INFO = Object.freeze({
  uiRevision: UI_REVISION,
  sourceApp: "apps/grao-invest-cockpit",
  gitCommit: "",
  gitCommitShort: "",
  entryAsset: "",
  builtAt: "",
});
const HERO_IMAGE_URLS = [
  "/assets/metodo/01.webp",
  "/assets/metodo/02.webp",
  "/assets/metodo/03.webp",
  "/assets/metodo/04.webp",
  "/assets/metodo/05.webp",
  "/assets/metodo/06.webp",
  "/assets/metodo/07.webp",
  "/assets/metodo/08.webp",
  "/assets/metodo/09.webp",
];
const FEED_DEFINITIONS = Object.freeze([
  {
    key: "dashboardSummary",
    label: "Resumo científico",
    endpoint: "/api/dashboard/summary/1",
    officialArray: "thesis_open_operations",
  },
  {
    key: "currentMonitor",
    label: "Monitor atual",
    endpoint: "/api/theses/current-monitor/latest",
    officialArray: "theses",
  },
  {
    key: "realEstateCandidates",
    label: "Radar de imóveis",
    endpoint: "/api/real-estate/candidates",
    officialArray: "candidates",
  },
  {
    key: "realEstateStrategyTerritoryCandidates",
    label: "Briefs imobiliÃ¡rios",
    endpoint: "/api/real-estate/strategy-territory-candidates",
    officialArray: "matrix_briefs",
  },
]);

function buildFeedHealth(payloads, thrownMessage) {
  const errorsByFeed = new Map(
    (payloads?.errors ?? []).map((error) => [error.feed, error.message || "Feed indisponível"]),
  );

  return FEED_DEFINITIONS.map((feed) => {
    const hasPayload = Boolean(payloads?.[feed.key]);
    const errorMessage = thrownMessage || errorsByFeed.get(feed.key);

    return {
      ...feed,
      status: hasPayload && !errorMessage ? "live" : "fallback",
      labelStatus: hasPayload && !errorMessage ? "API real" : "Fallback ativo",
      message: hasPayload && !errorMessage
        ? "Feed oficial respondendo. Dados reais aplicados ao laboratório."
        : `Endpoint em fallback${errorMessage ? `: ${errorMessage}` : ""}. Mantendo retrato operacional para conferência.`,
    };
  });
}

function mergeAvailablePayloads(payloads) {
  return FEED_KEYS.reduce((merged, key) => {
    if (payloads?.[key]) merged[key] = payloads[key];
    return merged;
  }, {});
}

function hasFeedGap(payloads) {
  return FEED_KEYS.some((key) => !payloads?.[key]);
}

function preloadHeroImages() {
  HERO_IMAGE_URLS.slice(1).forEach((src) => {
    const image = new Image();
    image.decoding = "async";
    image.src = src;
  });
}

function normalizeBuildInfo(payload) {
  if (!payload || typeof payload !== "object") return DEFAULT_BUILD_INFO;

  return {
    uiRevision: payload.ui_revision || payload.uiRevision || DEFAULT_BUILD_INFO.uiRevision,
    sourceApp: payload.source_app || payload.sourceApp || DEFAULT_BUILD_INFO.sourceApp,
    gitCommit: payload.deployed_git_commit || payload.git_commit || payload.gitCommit || "",
    gitCommitShort: payload.deployed_git_commit_short || payload.git_commit_short || payload.gitCommitShort || "",
    entryAsset: payload.entry_asset || payload.entryAsset || "",
    builtAt: payload.built_at || payload.builtAt || "",
  };
}

function InitialCockpitLoading() {
  return (
    <main
      style={{
        background: C.bg,
        color: C.text,
        display: "flex",
        flexDirection: "column",
        fontFamily: "Sora, system-ui, sans-serif",
        gap: 18,
        justifyContent: "center",
        minHeight: "100vh",
        padding: "24px 28px 40px",
      }}
    >
      <section
        aria-label="Carregando laboratorio"
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 16,
          maxWidth: 620,
          padding: "22px 24px",
        }}
      >
        <div
          style={{
            color: C.gold,
            fontFamily: mono,
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: "0.08em",
            marginBottom: 10,
            textTransform: "uppercase",
          }}
        >
          Motor Halley
        </div>
        <h1 style={{ color: C.text, fontSize: 22, margin: "0 0 10px" }}>
          Carregando laboratório científico
        </h1>
        <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.7, margin: 0 }}>
          O retrato oficial está sendo buscado na API. Nenhum placar é exibido antes da evidência chegar.
        </p>
      </section>
    </main>
  );
}

export default function App() {
  useFonts();

  const [active, setActive] = useState("dashboard");
  const [tesesEntryMode, setTesesEntryMode] = useState(null);
  const [buildInfo, setBuildInfo] = useState(DEFAULT_BUILD_INFO);
  const [isInitialCockpitLoad, setIsInitialCockpitLoad] = useState(true);
  const [cockpitData, setCockpitData] = useState(() =>
    withCockpitDataTrust(normalizeCockpitHalley({})),
  );
  const [feedStatus, setFeedStatus] = useState("live");
  const [feedHealth, setFeedHealth] = useState(() => buildFeedHealth({}));

  const refreshCockpitData = useCallback(async (isStillMounted = () => true) => {
    try {
      const payloads = await fetchCockpitPayloads();
      if (!isStillMounted()) return;

      const feedHasErrors = payloads.errors?.length > 0 || hasFeedGap(payloads);
      const mergedPayloads = mergeAvailablePayloads(payloads);

      const nextFeedStatus = feedHasErrors ? "fallback" : "live";
      setCockpitData(withCockpitDataTrust(normalizeCockpitHalley(mergedPayloads), nextFeedStatus));
      setFeedStatus(nextFeedStatus);
      setFeedHealth(buildFeedHealth(payloads));
    } catch {
      if (!isStillMounted()) return;

      setCockpitData(withCockpitDataTrust(normalizeCockpitHalley({}), "fallback"));
      setFeedStatus("fallback");
      setFeedHealth(buildFeedHealth({}, "Falha na camada de busca"));
    } finally {
      if (isStillMounted()) setIsInitialCockpitLoad(false);
    }
  }, []);

  function handleNavSelect(nextScreen) {
    setTesesEntryMode(null);
    setActive(nextScreen);
  }

  function openMethodExample() {
    setTesesEntryMode("method-demo");
    setActive("teses");
  }

  useEffect(() => {
    let isMounted = true;

    refreshCockpitData(() => isMounted);

    return () => {
      isMounted = false;
    };
  }, [refreshCockpitData]);

  useEffect(() => {
    let isMounted = true;

    fetch(BUILD_INFO_URL, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (isMounted) setBuildInfo(normalizeBuildInfo(payload));
      })
      .catch(() => {
        if (isMounted) setBuildInfo(DEFAULT_BUILD_INFO);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    if ("requestIdleCallback" in window) {
      const idleId = window.requestIdleCallback(preloadHeroImages, { timeout: 2500 });
      return () => window.cancelIdleCallback?.(idleId);
    }

    const timeoutId = window.setTimeout(preloadHeroImages, 1200);
    return () => window.clearTimeout(timeoutId);
  }, []);

  const screens = {
    dashboard: <CockpitHalley data={cockpitData} />,
    teses: <Teses data={cockpitData} feedStatus={feedStatus} onRefresh={() => refreshCockpitData()} entryMode={tesesEntryMode} />,
    mercado: <Mercado data={cockpitData} />,
    backtest: <Backtest data={cockpitData} />,
    risco: <Risco data={cockpitData} />,
    alertas: <Alertas data={cockpitData} />,
    aprendizado: <Aprendizado data={cockpitData} />,
    metodo: <Metodo onOpenMethodExample={openMethodExample} />,
    saude: <Saude data={cockpitData} feedStatus={feedStatus} feedHealth={feedHealth} />,
  };

  return (
    <div
      style={{
        background: C.bg,
        color: C.text,
        display: "flex",
        fontFamily: "Sora, system-ui, sans-serif",
        minHeight: "100vh",
      }}
    >
      <Sidebar
        active={active}
        onSelect={handleNavSelect}
        feedStatus={feedStatus}
        lastUpdatedAt={cockpitData?.scientificSummary?.lastUpdatedAt}
        uiRevision={UI_REVISION}
        buildInfo={buildInfo}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        {isInitialCockpitLoad ? <InitialCockpitLoading /> : (screens[active] ?? screens.dashboard)}
      </div>
    </div>
  );
}
