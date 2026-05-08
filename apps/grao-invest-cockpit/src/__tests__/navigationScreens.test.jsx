import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

describe("navigation screens", () => {
  beforeEach(() => {
    vi.spyOn(window.HTMLMediaElement.prototype, "play").mockImplementation(() => undefined);
    vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("opens Teses, Mercado, Validacao, Risco, Alertas and Aprendizado from the sidebar", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: /Teses/i }));
    expect(await screen.findByText(/Esse padr.o apareceu 97 vezes/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Abrir lista completa/i }));
    await user.click(screen.getAllByText("PETR4")[0]);
    expect(screen.getByText("Ficha completa da tese")).toBeInTheDocument();
    expect(screen.getByText("Resultado vs esperado")).toBeInTheDocument();
    expect(screen.getAllByText("Aprendizado registrado").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /Mercado/i }));
    expect(screen.getByText(/contexto que alimenta o motor/i)).toBeInTheDocument();
    expect(screen.getByText("Ativos cobertos")).toBeInTheDocument();
    expect(screen.queryByText("Com tese ativa")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Confian.a Halley/i).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /Valida/i }));
    expect(screen.getAllByText(/simula..es conclu.das/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Laborat.rio do M.todo/i)).toBeInTheDocument();
    expect(screen.getByText(/Como o m.todo foi calibrado/i)).toBeInTheDocument();
    expect(screen.getByText(/Evolu..o ap.s cada calibra..o/i)).toBeInTheDocument();
    expect(screen.getByText(/ltimos ciclos audit.veis/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Risco/i }));
    expect(screen.getByText(/A exposi..o est. em/i)).toBeInTheDocument();
    expect(screen.getByText("Exposição total")).toBeInTheDocument();
    expect(screen.getByText("Alertas de risco ativos")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Alertas/i }));
    expect(screen.getByText(/Primeiro movimento.*hoje/i)).toBeInTheDocument();
    expect(screen.getByText(/Partitura completa.*hist.rico/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Aprendizado/i }));
    expect(screen.getByText(/aprendizados aplicados/i)).toBeInTheDocument();
    expect(screen.getByText(/A Grande Obra.*gap/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /M.todo/i }));
    expect(screen.getByText("Sem sinal vazio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Come.ar com .udio/i })).toBeInTheDocument();
  }, 20000);

  it("does not repeat the active sidebar label as a top content heading", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    for (const { button, heading } of [
      { button: /Dashboard/i, heading: "Dashboard" },
      { button: /Teses/i, heading: "Teses" },
      { button: /Mercado/i, heading: "Mercado" },
      { button: /Valida/i, heading: "Validação" },
      { button: /Risco/i, heading: "Risco" },
      { button: /Alertas/i, heading: "Alertas" },
      { button: /Aprendizado/i, heading: "Aprendizado" },
      { button: /M.todo/i, heading: "Método" },
      { button: /Sa.de/i, heading: "Saúde" },
    ]) {
      await user.click(screen.getByRole("button", { name: button }));
      expect(screen.queryByRole("heading", { name: heading })).not.toBeInTheDocument();
    }
  });

  it("bridges Metodo into a selected thesis example", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: /M.todo/i }));
    await user.click(screen.getByRole("button", { name: /Entrar no app/i }));

    expect(screen.getAllByText(/Radar imobili.rio/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Ficha completa da tese")).toBeInTheDocument();

    const detail = screen.getByText("Ficha completa da tese");
    const table = screen.getByTestId("teses-table");
    expect(detail.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

