export const PlatformType = Object.freeze({
  MACOS: "macos",
  WINDOWS: "windows",
  LINUX: "linux",
  ANDROID: "android",
  IOS: "ios",
  UNKNOWN: "unknown"
});

export const BrowserType = Object.freeze({
  CHROME: "chrome",
  EDGE: "edge",
  FIREFOX: "firefox",
  SAFARI: "safari",
  UNKNOWN: "unknown"
});

export function getPlatformType() {
  const userAgent = navigator.userAgent.toLowerCase();

  if (userAgent.includes("mac")) {
    return PlatformType.MACOS;
  }
  if (userAgent.includes("win")) {
    return PlatformType.WINDOWS;
  }
  if (userAgent.includes("linux")) {
    return PlatformType.LINUX;
  }
  if (userAgent.includes("android")) {
    return PlatformType.ANDROID;
  }
  if (/iphone|ipad|ipod/.test(userAgent)) {
    return PlatformType.IOS;
  }
  return PlatformType.UNKNOWN;
}

export const BROWSER = (() => {
  const userAgent = navigator.userAgent.toLowerCase();

  if (userAgent.includes("edg/")) {
    return BrowserType.EDGE;
  }
  if (userAgent.includes("chrome/")) {
    return BrowserType.CHROME;
  }
  if (userAgent.includes("firefox/")) {
    return BrowserType.FIREFOX;
  }
  if (userAgent.includes("safari/")) {
    return BrowserType.SAFARI;
  }
  return BrowserType.UNKNOWN;
})();


export const browserAPI = (() => {
  const platform = getPlatformType();

  if (BrowserType.CHROME === BROWSER || BrowserType.EDGE === BROWSER) {
    return {
      platform,
      browserName: BROWSER,
      runtime: chrome.runtime,
      declarativeNetRequest: chrome.declarativeNetRequest
    };
  }

  if (BrowserType.FIREFOX === BROWSER) {
    return {
      platform,
      browserName: BROWSER,
      runtime: browser.runtime,
      declarativeNetRequest: browser.declarativeNetRequest
    };
  }

  if (BrowserType.SAFARI === BROWSER) {
    return {
      platform,
      browserName: BROWSER,
      runtime: browser.runtime,
      declarativeNetRequest: browser.declarativeNetRequest
    };
  }

  throw new Error("Unsupported browser");
})();


export const getRequestResourceTypes = (browserType) => {
    const typesMap = {
        [BrowserType.CHROME]: ["main_frame", "sub_frame", "stylesheet", "script", "image", "font", "object", "xmlhttprequest",
            "ping", "csp_report", "media", "websocket"],
        [BrowserType.EDGE]: ["main_frame", "sub_frame", "stylesheet", "script", "image", "font", "object", "xmlhttprequest",
            "ping", "csp_report", "media", "websocket"],
        [BrowserType.FIREFOX]: ["main_frame", "sub_frame", "stylesheet", "script", "image", "font", "object", "xmlhttprequest",
            "ping", "csp_report", "media", "websocket"],
        [BrowserType.SAFARI]: ["main_frame", "sub_frame", "stylesheet", "script", "image", "font", "xmlhttprequest", "ping",
            "media", "websocket"]
    };

    return typesMap[browserType] || [];
};
