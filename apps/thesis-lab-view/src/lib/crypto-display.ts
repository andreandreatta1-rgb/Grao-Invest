const QUOTE_SUFFIXES = ["USDT", "USDC", "BUSD", "FDUSD", "BTC", "ETH"] as const;

const CRYPTO_META: Record<string, { name: string; symbol: string }> = {
  BTC: { name: "Bitcoin", symbol: "BTC" },
  ETH: { name: "Ethereum", symbol: "ETH" },
  SOL: { name: "Solana", symbol: "SOL" },
  BNB: { name: "BNB", symbol: "BNB" },
  XRP: { name: "XRP", symbol: "XRP" },
  ADA: { name: "Cardano", symbol: "ADA" },
  DOGE: { name: "Dogecoin", symbol: "DOGE" },
  AVAX: { name: "Avalanche", symbol: "AVAX" },
  LINK: { name: "Chainlink", symbol: "LINK" },
  LTC: { name: "Litecoin", symbol: "LTC" },
};

function cleanText(value?: string) {
  return (value ?? "").trim();
}

export function cryptoBaseSymbol(instrument: string): string {
  const clean = cleanText(instrument).toUpperCase();
  for (const suffix of QUOTE_SUFFIXES) {
    if (clean.endsWith(suffix) && clean.length > suffix.length) {
      return clean.slice(0, clean.length - suffix.length);
    }
  }
  const parenMatch = clean.match(/\(([A-Z0-9]{2,10})\)/);
  if (parenMatch?.[1]) return parenMatch[1];
  return clean.replace(/[^A-Z0-9]/g, "");
}

export function cryptoAssetLabel(instrument: string): string {
  const symbol = cryptoBaseSymbol(instrument);
  const meta = CRYPTO_META[symbol];
  if (!symbol) return cleanText(instrument).toUpperCase();
  if (!meta) return `${symbol} (${symbol})`;
  return `${meta.name} (${meta.symbol})`;
}

export function cryptoSymbolFromText(text: string): string | undefined {
  const explicit = cryptoBaseSymbol(text);
  if (explicit && CRYPTO_META[explicit]) return explicit;
  return undefined;
}

export function cryptoInstrumentFromText(text: string): string | undefined {
  const symbol = cryptoSymbolFromText(text);
  return symbol ? `${symbol}USDT` : undefined;
}

export function cryptoQuoteLabel(): string {
  return "USD";
}

export function formatCryptoScope(
  instruments: string[],
  options?: { separator?: string; maxItems?: number },
): string {
  const separator = options?.separator ?? ", ";
  const maxItems = options?.maxItems ?? 3;
  const labels = instruments.map(cryptoAssetLabel).filter(Boolean);
  if (labels.length <= maxItems) return labels.join(separator);
  return `${labels.slice(0, maxItems).join(separator)} +${labels.length - maxItems}`;
}
