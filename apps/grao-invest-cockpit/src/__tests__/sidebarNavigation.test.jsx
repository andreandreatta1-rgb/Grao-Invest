import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "../components";

describe("Sidebar contextual navigation", () => {
  it("shows thesis workspace subareas under Teses", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <Sidebar
        active="teses"
        activeSubsection="ativos"
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("button", { name: "Ativos" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Mesa de decisão" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Imóveis" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Histórico" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Mesa de decisão" }));

    expect(onSelect).toHaveBeenCalledWith("teses/mesa");
  });

  it("shows contextual subareas under the active real estate radar area", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <Sidebar
        active="radar-imobiliario"
        activeSubsection="garimpo"
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("button", { name: "Visão geral" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Garimpo estruturado" })).toHaveAttribute("aria-current", "page");

    await user.click(screen.getByRole("button", { name: "Candidatos abertos" }));

    expect(onSelect).toHaveBeenCalledWith("radar-imobiliario/candidatos");
  });
});
