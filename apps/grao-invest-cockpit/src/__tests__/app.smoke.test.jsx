import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the Grão Invest dashboard shell", () => {
    render(<App />);
    expect(screen.getByText("Grão Invest")).toBeInTheDocument();
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThan(0);
    expect(screen.queryByText("Cockpit Halley")).not.toBeInTheDocument();
  });

  it("does not render empty cockpit numbers while the official feed is still loading", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));

    render(<App />);

    const dashboard = screen.getByRole("main");
    expect(within(dashboard).getByText(/Carregando laborat.rio cient.fico/i)).toBeInTheDocument();
    expect(within(dashboard).queryByText("Teses testadas")).not.toBeInTheDocument();
  });

  it("keeps laboratory update metadata in the sidebar instead of the dashboard header", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));

    render(<App />);

    expect(await screen.findByText("Teses testadas")).toBeInTheDocument();
    const sidebar = screen.getByRole("complementary");
    const dashboard = screen.getByRole("main");

    expect(within(sidebar).getByText("Status do laboratório")).toBeInTheDocument();
    expect(within(sidebar).getByText("Atualizado em --/--/----")).toBeInTheDocument();
    expect(within(sidebar).getByText("UI rev soul-4")).toBeInTheDocument();
    expect(within(dashboard).queryByText("Atualizado em 03/05/2026")).not.toBeInTheDocument();
    expect(within(dashboard).queryByText("UI rev soul-4")).not.toBeInTheDocument();
  });

  it("keeps the cockpit visible with fallback data when feeds fail", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));

    render(<App />);

    expect(await screen.findByText("Teses testadas")).toBeInTheDocument();
    const sidebar = screen.getByRole("complementary");
    const dashboard = screen.getByRole("main");
    expect(await within(sidebar).findByText(/Feed temporariamente/i)).toBeInTheDocument();
    expect(within(dashboard).queryByText(/Feed temporariamente/i)).not.toBeInTheDocument();
    expect(screen.getByText("B3")).toBeInTheDocument();
    expect(screen.getByText("Cripto")).toBeInTheDocument();
    expect(screen.getByText("Imóveis")).toBeInTheDocument();
  });
});
