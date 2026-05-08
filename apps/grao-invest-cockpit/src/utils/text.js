const LEGACY_REPLACEMENTS = Object.freeze({
  "\u00c3\u00a1": "\u00e1",
  "\u00c3\u00a2": "\u00e2",
  "\u00c3\u00a3": "\u00e3",
  "\u00c3\u00a9": "\u00e9",
  "\u00c3\u00aa": "\u00ea",
  "\u00c3\u00ad": "\u00ed",
  "\u00c3\u00b3": "\u00f3",
  "\u00c3\u00b4": "\u00f4",
  "\u00c3\u00b5": "\u00f5",
  "\u00c3\u00ba": "\u00fa",
  "\u00c3\u00a7": "\u00e7",
  "\u00c3\u2021": "\u00c7",
  "\u00e2\u20ac\u201d": "\u2014",
  "\u00e2\u20ac\u201c": "\u2013",
  "\u00e2\u20ac\u2018": "-",
});

function decodeEscapedUnicode(value) {
  return value.replace(/\\u([\da-f]{4})/gi, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

export function cleanText(value) {
  if (value === null || value === undefined) return "";

  let text = decodeEscapedUnicode(String(value));

  for (const [legacy, replacement] of Object.entries(LEGACY_REPLACEMENTS)) {
    text = text.replaceAll(legacy, replacement);
  }

  return text;
}
