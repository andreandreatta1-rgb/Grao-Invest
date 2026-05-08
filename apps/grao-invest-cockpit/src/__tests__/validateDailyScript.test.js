import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(".");

describe("daily validation command", () => {
  it("exposes a single validate:daily command with test, build and report stages", () => {
    const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
    const scriptPath = resolve(root, "scripts", "validate-daily.mjs");

    expect(packageJson.scripts["validate:daily"]).toBe("node scripts/validate-daily.mjs");
    expect(existsSync(scriptPath)).toBe(true);

    const script = readFileSync(scriptPath, "utf8");
    expect(script).toContain("npm test");
    expect(script).toContain("npm run build");
    expect(script).toContain("daily-validation-report.json");
    expect(script).toContain("screenshots");
  });
});
