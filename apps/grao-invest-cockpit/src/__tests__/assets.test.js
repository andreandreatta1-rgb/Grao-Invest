import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("visual identity assets", () => {
  it("ships the nine Metodo images used by the interface", () => {
    for (const fileName of ["01.png", "02.png", "03.png", "04.png", "05.png", "06.png", "07.png", "08.png", "09.png"]) {
      const assetPath = path.resolve("public/assets/metodo", fileName);

      expect(fs.existsSync(assetPath)).toBe(true);
      expect(fs.statSync(assetPath).size).toBeGreaterThan(1000);
    }
  });
});
