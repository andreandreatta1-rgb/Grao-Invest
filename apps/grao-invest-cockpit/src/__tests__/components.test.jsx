import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  AppLayout,
  AppTopbar,
  Badge,
  C,
  FrontCard,
  KPICard,
  LearningLoopCard,
  PatrickJane,
  PatrickJaneMini,
  Sidebar,
  ThesisCard,
  fmt,
  mono,
} from "../components";

const sampleThesis = {
  id: 162,
  front: "B3",
  asset: "PETR4",
  direction: "Alta",
  hypothesis: "A hipótese sugere continuidade do ciclo após confirmação técnica.",
  evidence: ["Volume confirmou o movimento", "Suporte histórico respeitado"],
  entryPrice: 40.12,
  currentPrice: 41.3,
  targetPrice: 43.5,
  stopPrice: 38.9,
  expectedPct: 4.82,
  currentPct: 2.94,
  daysOpen: 4,
  openedAt: "2026-04-29T12:00:00Z",
  status: "monitoring",
  learning: "Manter confirmação de volume antes de elevar score.",
  operation: "Compra estruturada com risco definido.",
  invalidation: "Sai se perder R$ 38,90 ou vencer a janela da tese.",
};

describe("base cockpit components", () => {
  it("exports the canonical design system surface from src/components", () => {
    expect(C.gold).toBe("#c8a444");
    expect(mono).toContain("JetBrains Mono");
    expect(fmt(3.1415)).toBe("+3.14%");
    expect(Badge).toBeTypeOf("function");
    expect(KPICard).toBeTypeOf("function");
    expect(ThesisCard).toBeTypeOf("function");
    expect(Sidebar).toBeTypeOf("function");
    expect(AppLayout).toBeTypeOf("function");
    expect(AppTopbar).toBeTypeOf("function");
    expect(PatrickJane).toBeTypeOf("function");
  });

  it("renders an info badge", () => {
    render(<Badge label="Observando" type="info" />);

    expect(screen.getByText("Observando")).toBeInTheDocument();
  });

  it("renders Patrick Jane with the method asset, state badge, size and supplied message", () => {
    render(
      <PatrickJane
        state="reporting"
        size="lg"
        message="O plano foi seguido. Aprendizado registrado."
      />,
    );

    expect(screen.getByText("Patrick Jane")).toBeInTheDocument();
    expect(screen.getByText("Reportando")).toBeInTheDocument();
    expect(screen.getByText("Porta-voz do laboratório Grão Invest")).toBeInTheDocument();
    const image = screen.getByAltText("Patrick Jane");
    expect(image).toHaveAttribute("src", "/assets/metodo/01.webp");
    expect(image).toHaveStyle({
      width: "auto",
      height: "108px",
      borderRadius: "12px",
    });
    expect(image.getAttribute("style")).toContain("2px solid");
    expect(
      screen.getByText("O plano foi seguido. Aprendizado registrado."),
    ).toBeInTheDocument();
  });

  it("uses the screen-specific method PNG directly without generated avatar fallback", () => {
    render(<PatrickJane state="observing" screen="teses" message="Hipotese em observacao." />);

    expect(screen.getByAltText("Patrick Jane")).toHaveAttribute("src", "/assets/metodo/02.webp");
    expect(screen.queryByText("PJ")).not.toBeInTheDocument();
    expect(screen.getByText("Observando")).toBeInTheDocument();
  });

  it("can promote the Metodo image to a protagonist visual panel", () => {
    render(
      <PatrickJane
        hero
        state="reporting"
        screen="metodo"
        message="O método aparece primeiro pela imagem, depois pelo comentário."
      />,
    );

    expect(screen.getByTestId("patrick-jane-visual")).toHaveStyle({
      aspectRatio: "16 / 9",
      minWidth: "220px",
    });
    expect(screen.getByAltText("Patrick Jane")).toHaveAttribute("src", "/assets/metodo/08.webp");
    expect(screen.getByAltText("Patrick Jane")).toHaveStyle({
      width: "100%",
      height: "100%",
      objectFit: "contain",
    });
  });

  it("renders PatrickJaneMini for compact thesis insights", () => {
    render(
      <PatrickJaneMini
        state="testing"
        message="O motor recalibra com base no padrao observado."
      />,
    );

    expect(screen.getByText("Patrick Jane · Testando")).toBeInTheDocument();
    expect(
      screen.getByText("O motor recalibra com base no padrao observado."),
    ).toBeInTheDocument();
  });

  it("renders a B3 front summary", () => {
    render(
      <FrontCard
        front="B3"
        tested={100}
        goLive={8}
        validatedPct={67.5}
        status="atualizado"
      />,
    );

    expect(screen.getByText("B3")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("+67,50%")).toBeInTheDocument();
    expect(screen.getByText("atualizado")).toBeInTheDocument();
  });

  it("renders a front summary from a front object", () => {
    render(
      <FrontCard
        front={{
          id: "real-estate",
          label: "Imóveis",
          tested: 24,
          goLive: 3,
          validatedPct: 50,
          status: "em teste",
        }}
      />,
    );

    expect(screen.getByText("Imóveis")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("+50,00%")).toBeInTheDocument();
    expect(screen.getByText("em teste")).toBeInTheDocument();
  });

  it("explains repeated crypto range plans without calling the range center an alvo", () => {
    render(
      <ThesisCard
        thesis={{
          ...sampleThesis,
          id: "TH-BTCUSDT-range-0001",
          front: "Cripto",
          asset: "BTCUSDT",
          direction: "Neutra",
          entryPrice: 81212.04,
          currentPrice: 81212.04,
          targetPrice: 81212.04,
          stopPrice: 79993.86,
          expectedPct: 0.7,
          currentPct: 2.4,
          daysOpen: 0,
          hoursOpen: 17,
          rangeLowerPrice: 79993.86,
          rangeUpperPrice: 82430.22,
          operation: "Iron Condor em range",
        }}
      />,
    );

    const trigger = screen.getByRole("button", { name: /Tese TH-BTCUSDT-range-0001 BTCUSDT/i });

    expect(trigger).toHaveTextContent("Entrada/Centro");
    expect(trigger).toHaveTextContent("Faixa");
    expect(trigger).toHaveTextContent("R$ 79.993,86");
    expect(trigger).toHaveTextContent("R$ 82.430,22");
    expect(trigger).toHaveTextContent("Quebra");
    expect(trigger).toHaveTextContent("fora da faixa");
    expect(trigger).not.toHaveTextContent("Alvo");
    expect(trigger).toHaveTextContent("17 h");
  });

  it("shows the thesis reason, operation, entry date and exit rule before expansion", () => {
    render(<ThesisCard thesis={sampleThesis} />);

    const trigger = screen.getByRole("button", { name: /Tese 162 PETR4/i });

    expect(trigger).toHaveTextContent("Motivo");
    expect(trigger).toHaveTextContent(sampleThesis.hypothesis);
    expect(trigger).toHaveTextContent("Operação");
    expect(trigger).toHaveTextContent(sampleThesis.operation);
    expect(trigger).toHaveTextContent("Aberta em 29/04/2026");
    expect(trigger).toHaveTextContent("Saída");
    expect(trigger).toHaveTextContent(sampleThesis.invalidation);
  });

  it("shows thesis coverage notes before expansion", () => {
    render(
      <ThesisCard
        thesis={{
          ...sampleThesis,
          coverageNotes: [
            "Tese tecnica com mercado fresco.",
            "Faltam noticias recentes para confirmar contexto.",
            "Fundamentos nao se aplicam a este par cripto.",
            "Confianca reduzida por lacunas de confirmacao.",
          ],
        }}
      />,
    );

    const trigger = screen.getByRole("button", { name: /Tese 162 PETR4/i });

    expect(trigger).toHaveTextContent("Tese tecnica com mercado fresco.");
    expect(trigger).toHaveTextContent("Faltam noticias recentes para confirmar contexto.");
    expect(trigger).not.toHaveTextContent("50%");
  });

  it("renders a learning loop from a loop object", () => {
    render(
      <LearningLoopCard
        loop={{
          pain: "Entrada antes da confirmação completa.",
          remedy: "Esperar fechamento acima do nível validado.",
          expectedImpact: "Reduzir falso rompimento nas próximas teses.",
        }}
      />,
    );

    expect(screen.getByText("Dor observada")).toBeInTheDocument();
    expect(screen.getByText("Remédio aplicado")).toBeInTheDocument();
    expect(screen.getByText("Impacto esperado")).toBeInTheDocument();
    expect(
      screen.getByText("Reduzir falso rompimento nas próximas teses."),
    ).toBeInTheDocument();
  });

  it("keeps thesis details collapsed until toggled", async () => {
    const user = userEvent.setup();
    render(<ThesisCard thesis={sampleThesis} />);

    const trigger = screen.getByRole("button", { name: /Tese 162 PETR4/i });

    expect(trigger).toBeInTheDocument();
    expect(screen.queryByText("Volume confirmou o movimento")).not.toBeInTheDocument();

    await user.click(trigger);
    expect(screen.getAllByText(sampleThesis.hypothesis).length).toBeGreaterThan(1);
    expect(screen.getByText("Volume confirmou o movimento")).toBeInTheDocument();
    expect(screen.getByText(sampleThesis.learning)).toBeInTheDocument();

    await user.click(trigger);
    expect(screen.queryByText("Volume confirmou o movimento")).not.toBeInTheDocument();
  });

  it("wraps long thesis text safely when expanded", async () => {
    const user = userEvent.setup();
    const longText = "LONGTEXT".repeat(40);
    render(
      <ThesisCard
        thesis={{
          ...sampleThesis,
          asset: longText,
          hypothesis: longText,
          evidence: [longText],
          operation: longText,
          invalidation: longText,
          learning: longText,
        }}
      />,
    );

    const trigger = screen.getByRole("button", { name: /Tese 162/i });
    expect(trigger).toHaveStyle({
      minWidth: "0",
      overflowWrap: "anywhere",
    });

    await user.click(trigger);

    const details = screen.getByTestId("thesis-expanded-details");
    expect(details).toHaveStyle({
      minWidth: "0",
      overflowWrap: "anywhere",
    });
    expect(screen.getAllByText(longText).length).toBeGreaterThan(1);
  });
});
