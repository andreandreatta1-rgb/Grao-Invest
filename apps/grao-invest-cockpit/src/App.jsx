import { useCallback, useEffect, useState } from "react";
import { C, Sidebar } from "./components";
import { useFonts } from "./hooks/useFonts.js";
import { fetchCockpitPayloads } from "./data/cockpitHalleyApi.js";
import { normalizeCockpitHalley } from "./data/cockpitHalleyAdapter.js";
import { mockCockpitHalleyPayloads } from "./data/mockCockpitHalley.js";
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

function mergeWithFallback(payloads) {
  return FEED_KEYS.reduce((merged, key) => {
    merged[key] = payloads?.[key] ?? mockCockpitHalleyPayloads[key];
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

export default function App() {
  useFonts();

  const [active, setActive] = useState("dashboard");
  const [tesesEntryMode, setTesesEntryMode] = useState(null);
  const [cockpitData, setCockpitData] = useState(() =>
    withCockpitDataTrust(normalizeCockpitHalley(mockCockpitHalleyPayloads)),
  );
  const [feedStatus, setFeedStatus] = useState("live");
  const [feedHealth, setFeedHealth] = useState(() => buildFeedHealth(mockCockpitHalleyPayloads));

  const refreshCockpitData = useCallback(async (isStillMounted = () => true) => {
    try {
      const payloads = await fetchCockpitPayloads();
      if (!isStillMounted()) return;

      const feedHasErrors = payloads.errors?.length > 0 || hasFeedGap(payloads);
      const mergedPayloads = mergeWithFallback(payloads);

      const nextFeedStatus = feedHasErrors ? "fallback" : "live";
      setCockpitData(withCockpitDataTrust(normalizeCockpitHalley(mergedPayloads), nextFeedStatus));
      setFeedStatus(nextFeedStatus);
      setFeedHealth(buildFeedHealth(payloads));
    } catch {
      if (!isStillMounted()) return;

      setCockpitData(withCockpitDataTrust(normalizeCockpitHalley(mockCockpitHalleyPayloads), "fallback"));
      setFeedStatus("fallback");
      setFeedHealth(buildFeedHealth({}, "Falha na camada de busca"));
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
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        {screens[active] ?? screens.dashboard}
      </div>
    </div>
  );
}
