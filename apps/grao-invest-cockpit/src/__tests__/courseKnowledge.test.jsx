import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

describe("course knowledge area", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("exposes the auction course lesson control from the sidebar", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Radar Imobiliário" }));
    await user.click(await screen.findByRole("button", { name: "Conhecimento" }));
    await user.click(screen.getByRole("button", { name: /Milh.o com leil.o/i }));

    const main = await screen.findByTestId("radar-imobiliario-conhecimento-milhao-com-leilao");
    expect(within(main).getByText("Curso 1 Milhao com Leilao")).toBeInTheDocument();
    expect(within(main).getByText("https://grupo-primo.circle.so/c/leilao/")).toBeInTheDocument();
    expect(within(main).getByText("4 modulos")).toBeInTheDocument();
    expect(within(main).getByText("25 aulas")).toBeInTheDocument();
    expect(within(main).getByText("14h22")).toBeInTheDocument();
    expect(within(main).getByText("0 pendentes")).toBeInTheDocument();
    expect(within(main).getByText("25 analisadas")).toBeInTheDocument();
    expect(main).toHaveTextContent("docs/domain/radar-imobiliario/curso-1-milhao-com-leilao.md");
    expect(main).toHaveTextContent("docs/domain/radar-imobiliario/curso-1-milhao-com-leilao-playbook-operacional.md");
    expect(main).toHaveTextContent("docs/domain/radar-imobiliario/curso-1-milhao-com-leilao-captura-validada.md");
    expect(within(main).getByRole("button", { name: /MODULO 01/i })).toBeInTheDocument();
    expect(within(main).getByText("Caderno storytelling")).toBeInTheDocument();
    expect(within(main).getByText("Contexto - o que esta aula resolve")).toBeInTheDocument();
    expect(within(main).getByText("Caso operacional")).toBeInTheDocument();
    expect(within(main).getByText("Como aplicar na pratica")).toBeInTheDocument();
    expect(within(main).getByText("Armadilhas comuns")).toBeInTheDocument();
    expect(within(main).getByText("Como entra no Radar Imobiliario")).toBeInTheDocument();
    expect(within(main).getByText("Aula 1 - Construcao de base de Leiloes para arrematacao")).toBeInTheDocument();
    await user.click(within(main).getByRole("button", { name: /03 - Leilao Extrajudicial/i }));
    expect(within(main).getByText(/Marina acha um apartamento em Guarulhos/i)).toBeInTheDocument();
    expect(within(main).getByText(/Olhar apenas percentual de desconto/i)).toBeInTheDocument();
    expect(within(main).getByText("Cena visual")).toBeInTheDocument();
    expect(within(main).getByText(/Extrajudicial pede leitura fria da tela/i)).toBeInTheDocument();
    expect(
      within(main).getByRole("img", {
        name: /Tela de lote de leilao com lance inicial, leiloeiro oficial e regra extrajudicial/i,
      })
    ).toHaveAttribute("src", "/assets/demo/siteleiloes-portal-cantareira.png");
    expect(main).not.toHaveTextContent("Cenario operacional: surge");
    expect(main).not.toHaveTextContent("O aluno so deve avancar");

    expect(within(main).getByText("O Fim do Curso, O Inicio do Seu Primeiro Milhao")).toBeInTheDocument();
    expect(within(main).getAllByText("Analise resumida").length).toBeGreaterThan(0);
    expect(within(main).getAllByText("Aplicacao pratica na app").length).toBeGreaterThan(0);
    expect(within(main).getAllByText(/Descricao completa capturada/i).length).toBeGreaterThan(0);
    expect(within(main).getAllByText("Descricao nao exposta pelo Circle").length).toBeGreaterThan(0);
    expect(within(main).getAllByText(/Resumo da aula - transcricao analisada/i).length).toBeGreaterThan(0);
    expect(within(main).getAllByText("Resumo da aula - conteudo textual analisado").length).toBeGreaterThan(0);

    await user.click(within(main).getByRole("button", { name: /MODULO 03/i }));
    expect(within(main).getByText("Arrematacao & Engenharia da Compra")).toBeInTheDocument();
    await user.click(within(main).getByRole("button", { name: /02 - Arrematar sem ou com pouco dinheiro/i }));
    expect(within(main).getAllByText("Aula 2 - Arrematar sem ou com pouco dinheiro").length).toBeGreaterThan(0);
  });
});
