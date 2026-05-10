import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

describe("Jornada da Tese investor demo", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("opens a guided IA investigator story from the sidebar", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: /Jornada da Tese/i }));

    expect(screen.getByText(/IA investigadora de teses/i)).toBeInTheDocument();
    expect(screen.getAllByText(/observa o mundo real/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Selic/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/simula antes de arriscar capital/i).length).toBeGreaterThan(0);

    const sourceRadar = screen.getByTestId("source-radar");
    expect(within(sourceRadar).getByText(/O radar não olha só ativos/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/B3 · PETR4/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/Cripto · BTCUSDT/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/Macro · Selic/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/CVM · Fato relevante/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/Prefeitura · Retrofit/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/Território · Perdizes/i)).toBeInTheDocument();
    expect(within(sourceRadar).getByText(/Commodities · Petróleo/i)).toBeInTheDocument();
    expect(within(sourceRadar).getAllByText(/Sinal detectado|Hipótese formada|Em validação|Tese aberta|Bloqueado por P0|Aprendizado registrado/i).length).toBeGreaterThan(5);

    expect(screen.queryByTestId("perdizes-main-case")).not.toBeInTheDocument();

    const portfolio = screen.getByTestId("perdizes-case-portfolio");
    expect(within(portfolio).getByText(/Rua Turiassú, 362/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Av\. Francisco Matarazzo, 43/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Rua Caiubí, 91/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Edifício Saquarema/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Perdizes Best Place/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Tocha \/ farol/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Indústria/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/Mata verde/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/2ª praça futura/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/2ª praça já passou/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getByText(/arrematado\/vendido/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByRole("button", { name: /Abrir/i })).toHaveLength(8);
    expect(within(portfolio).queryByText(/O tamanho impressiona/i)).not.toBeInTheDocument();
    expect(within(portfolio).queryByText(/Resultado simulado vs renda fixa/i)).not.toBeInTheDocument();
  });

  it("keeps candidate cards compact and expands one detailed story at a time", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    window.history.replaceState(null, "", "/#jornada");
    const user = userEvent.setup();

    render(<App />);

    const portfolio = await screen.findByTestId("perdizes-case-portfolio");
    expect(within(portfolio).queryByText(/O tamanho impressiona/i)).not.toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Rua Turiassú, 362/i }));
    expect(within(portfolio).getByText(/Agora sim existe uma pergunta boa/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Mapa de concorrentes/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Resultado simulado vs renda fixa/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Custo final estimado/i).length).toBeGreaterThan(0);

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Rua Caiubí, 91/i }));
    expect(within(portfolio).queryByText(/Agora sim existe uma pergunta boa/i)).not.toBeInTheDocument();
    expect(within(portfolio).getByText(/O tamanho impressiona/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Caiubí carrega referência/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Ficha do imóvel/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Evidência visual do imóvel/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Mapa de concorrentes/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Demanda de saída/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Números da triagem/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Resultado simulado vs renda fixa/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Custo final estimado/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getByText(/P0 \/ prova antes de convicção/i)).toBeInTheDocument();
    expect(within(portfolio).getAllByText(/Como confirmar/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getByText(/Abrir fonte/i)).toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Av\. Francisco Matarazzo, 43/i }));
    expect(within(portfolio).queryByText(/O tamanho impressiona/i)).not.toBeInTheDocument();
    expect(within(portfolio).getByText(/Hoje é só calendário/i)).toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Abrir Edifício Saquarema/i }));
    expect(within(portfolio).getAllByText(/compra direta/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/renda urbana/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getAllByText(/aluguel real/i).length).toBeGreaterThan(0);
    expect(within(portfolio).getByText(/localização não paga conta sozinha/i)).toBeInTheDocument();
  });

  it("lets the Turiassú card collapse and reopen like every other candidate", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    window.history.replaceState(null, "", "/#jornada");
    const user = userEvent.setup();

    render(<App />);

    const portfolio = await screen.findByTestId("perdizes-case-portfolio");
    const toggle = within(portfolio).getByRole("button", { name: /Abrir Rua Turiassú, 362/i });

    expect(within(portfolio).queryByText(/Evidência visual do imóvel/i)).not.toBeInTheDocument();

    await user.click(toggle);
    expect(within(portfolio).getByText(/Evidência visual do imóvel/i)).toBeInTheDocument();

    await user.click(within(portfolio).getByRole("button", { name: /Fechar Rua Turiassú, 362/i }));
    expect(within(portfolio).queryByText(/Evidência visual do imóvel/i)).not.toBeInTheDocument();
  });

  it("opens the guided story directly from the #jornada deep link", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    window.history.replaceState(null, "", "/#jornada");

    render(<App />);

    expect(await screen.findByText(/IA investigadora de teses/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Jornada da Tese/i })).toHaveStyle({
      color: "rgb(200, 164, 68)",
    });
  });
});
