import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import Aprendizado from "../screens/Aprendizado.jsx";

describe("Validation laboratory experience", () => {
  it("renames the old Backtest navigation to Validação and opens the Method laboratory", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    expect(screen.queryByRole("button", { name: /Backtest/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Validação/i }));

    expect(screen.getByText("Laboratório do Método")).toBeInTheDocument();
    expect(screen.getByText(/Hipótese testada/i)).toBeInTheDocument();
    expect(screen.getByText(/Método calibrado/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Validação" })).not.toBeInTheDocument();
  });

  it("connects Aprendizado to validation gaps and method rules", () => {
    render(<Aprendizado />);

    expect(screen.getByText("Conexão com validação")).toBeInTheDocument();
    expect(screen.getByText("Gap medido")).toBeInTheDocument();
    expect(screen.getByText("Regra ajustada")).toBeInTheDocument();
    expect(screen.getByText("Próximo ciclo")).toBeInTheDocument();
    expect(screen.getByText(/cada aprendizado nasce de um erro medido/i)).toBeInTheDocument();
  });
});
