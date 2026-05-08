import { describe, expect, it } from "vitest";
import { cleanText } from "../utils/text";

describe("cleanText", () => {
  it("preserves correctly encoded Portuguese text", () => {
    expect(cleanText("Ações, Operações, Imóveis, Hipótese")).toBe("Ações, Operações, Imóveis, Hipótese");
  });

  it("repairs common legacy mojibake sequences", () => {
    const brokenLegacyText = "Pr\\u00c3\\u00b3xima: exigir confirma\\u00c3\\u00a7\\u00c3\\u00a3o de volume";

    expect(cleanText(brokenLegacyText)).toBe("Próxima: exigir confirmação de volume");
  });

  it("repairs real mojibake found in Portuguese labels", () => {
    expect(cleanText("AÃ§Ãµes, OperaÃ§Ãµes, ImÃ³veis, HipÃ³tese")).toBe("Ações, Operações, Imóveis, Hipótese");
    expect(cleanText("PrÃ³xima: exigir confirmaÃ§Ã£o de volume")).toBe("Próxima: exigir confirmação de volume");
  });
});
