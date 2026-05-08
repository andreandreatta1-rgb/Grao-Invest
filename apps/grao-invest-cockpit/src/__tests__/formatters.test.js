import { describe, expect, it } from "vitest";
import { fmtDate, fmtDays, fmtMoney, fmtPct } from "../utils/formatters";

describe("formatters", () => {
  it("formats money values for Brazilian currency display", () => {
    expect(fmtMoney(42.3)).toBe("R$ 42,30");
    expect(fmtMoney(null)).toBe("R$ --");
  });

  it("formats percentages with sign and comma decimals", () => {
    expect(fmtPct(3.14159)).toBe("+3,14%");
    expect(fmtPct(-2)).toBe("-2,00%");
    expect(fmtPct(undefined)).toBe("--%");
  });

  it("rounds day counts for compact display", () => {
    expect(fmtDays(4.91)).toBe("5 d");
  });

  it("formats ISO timestamps as Brazilian dates", () => {
    expect(fmtDate("2026-04-27T12:00:00Z")).toBe("27/04/2026");
  });

  it("formats midnight UTC timestamps on the Sao Paulo calendar day", () => {
    expect(fmtDate("2026-05-07T00:25:00+00:00")).toBe("06/05/2026");
  });
});
