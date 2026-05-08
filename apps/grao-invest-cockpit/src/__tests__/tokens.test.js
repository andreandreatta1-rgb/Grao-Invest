import { describe, expect, it } from "vitest";
import { C } from "../components";

describe("tokens", () => {
  it("uses the AGENTS faint color token", () => {
    expect(C.faint).toBe("#0d1630");
  });
});
