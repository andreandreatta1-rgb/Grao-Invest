import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { C } from "../components";
import Backtest, { accuracyCycles } from "../screens/Backtest.jsx";

describe("Backtest", () => {
  it("frames validation as a complete Method laboratory cycle", () => {
    render(<Backtest />);

    expect(screen.getByText("Como eu sei que o Método Grão aprende com os erros e melhora com o tempo?")).toBeInTheDocument();
    expect(screen.getByText("Laboratório do Método")).toBeInTheDocument();
    expect(screen.getByText("O que é calibração?")).toBeInTheDocument();
    expect(screen.getByText(/Calibrar é medir o erro, entender a causa e ajustar a próxima regra/i)).toBeInTheDocument();
    expect(screen.getByText(/847 simulações concluídas\. O padrão resiste, mas ainda está sendo testado/i)).toBeInTheDocument();
    expect(screen.getByText("Hipótese testada")).toBeInTheDocument();
    expect(screen.getByText("Resultado histórico")).toBeInTheDocument();
    expect(screen.getByText("Gap observado")).toBeInTheDocument();
    expect(screen.getByText("Aprendizado registrado")).toBeInTheDocument();
    expect(screen.getByText("Nova regra do método")).toBeInTheDocument();
    expect(screen.getByText("Método calibrado")).toBeInTheDocument();
    expect(screen.getByText(/O método testa, erra, aprende e volta mais calibrado/i)).toBeInTheDocument();
    expect(screen.getByTestId("validation-cycle-flow")).toBeInTheDocument();
  });

  it("renders all 11 calibration accuracy cycles from Cal.08 to Cal.18", () => {
    render(<Backtest />);

    expect(accuracyCycles).toHaveLength(11);
    expect(accuracyCycles.map((item) => item.ciclo)).toEqual([
      "Cal.08",
      "Cal.09",
      "Cal.10",
      "Cal.11",
      "Cal.12",
      "Cal.13",
      "Cal.14",
      "Cal.15",
      "Cal.16",
      "Cal.17",
      "Cal.18",
    ]);
    expect(accuracyCycles.every((item) => item.taxa >= 55 && item.taxa <= 67.52)).toBe(true);
    expect(screen.getAllByTestId(/^accuracy-cycle-/)).toHaveLength(11);
    expect(screen.getAllByTestId(/^calibration-timeline-/)).toHaveLength(11);
    expect(screen.queryByTestId("strata-layer")).not.toBeInTheDocument();
    expect(screen.getAllByText("67,52%").length).toBeGreaterThan(0);
  });

  it("shows realistic method metrics instead of a perfect approval rate", () => {
    render(<Backtest data={{ backtest: { calibrations: [{ id: 1, data: "go-live", teses: 1, esperado: 0, alcancado: 0, aprovadas: 0 }] } }} />);

    expect(screen.getByText("Acerto direcional")).toBeInTheDocument();
    expect(screen.getAllByText("67,52%").length).toBeGreaterThan(0);
    expect(screen.getByText("Variação desde Cal.08")).toBeInTheDocument();
    expect(screen.getByText("+12,52 p.p.")).toBeInTheDocument();
    expect(screen.getByText("Gap de expectativa")).toBeInTheDocument();
    expect(screen.getAllByText(/−1,02pp|−1,02 p\.p\./).length).toBeGreaterThan(0);
    expect(screen.getByText("Acerto mede direção. Gap mede precisão entre esperado e realizado.")).toBeInTheDocument();
    expect(screen.queryByText("Taxa de aprovação")).not.toBeInTheDocument();
    expect(screen.queryByText("98,9%")).not.toBeInTheDocument();
  });

  it("treats reversed calibration cycles as chronological before showing variation", () => {
    render(
      <Backtest
        data={{
          backtest: {
            accuracyCycles: [...accuracyCycles].reverse(),
          },
        }}
      />,
    );

    expect(screen.getByText("Acerto direcional")).toBeInTheDocument();
    expect(screen.getByText("Variação desde Cal.08")).toBeInTheDocument();
    expect(screen.getAllByText("67,52%").length).toBeGreaterThan(0);
    expect(screen.getByText("+12,52 p.p.")).toBeInTheDocument();
    expect(screen.queryByText("Melhora desde Cal.08")).not.toBeInTheDocument();
  });

  it("shows a negative calibration variation as an alert, not a green improvement", () => {
    const fallingCycles = accuracyCycles.map((item, index) => ({
      ...item,
      taxa: Number((67.52 - (9.3 * index) / 10).toFixed(2)),
    }));

    render(<Backtest data={{ backtest: { accuracyCycles: fallingCycles } }} />);

    const label = screen.getByText("Variação desde Cal.08");
    const value = label.parentElement.nextElementSibling;

    expect(value).toHaveTextContent("−9,30 p.p.");
    expect(value).toHaveStyle({ color: C.coral });
    expect(screen.getByText("queda no ciclo atual")).toBeInTheDocument();
  });

  it("explains when deterioration is driven by a large recent sample and synthetic calibration history", () => {
    render(
      <Backtest
        data={{
          scientificSummary: { testedTheses: 2543 },
          backtest: {
            accuracyCycleSource: "synthetic",
            accuracyCycles: accuracyCycles.map((item, index) => ({
              ...item,
              taxa: Number((55 - (8.3 * index) / 10).toFixed(2)),
            })),
            calibrations: [
              { id: 1, data: "Semana 1", teses: 9, esperado: 4.43, alcancado: 3.83, aprovadas: 8 },
              { id: 2, data: "Semana 2", teses: 144, esperado: 4.43, alcancado: 3.01, aprovadas: 135 },
              { id: 3, data: "Semana 3", teses: 2390, esperado: 4.43, alcancado: 1.87, aprovadas: 1024 },
            ],
            sampleQuality: {
              duplicate_case_study_events_excluded: 516,
              current_monitor_snapshots_excluded: 190,
            },
          },
        }}
      />,
    );

    expect(screen.getByText(/Dados parciais/i)).toBeInTheDocument();
    expect(screen.getByText(/Performance em deterioração nesta calibração/i)).toBeInTheDocument();
    expect(screen.getByText(/Semana 3 concentra 2\.390 de 2\.543 testes/i)).toBeInTheDocument();
    expect(screen.getByText(/516 replays e 190 snapshots/i)).toBeInTheDocument();
    expect(screen.getByText(/Série de calibração estimada/i)).toBeInTheDocument();
  });

  it("merges the calibration relationship and graph into one compact evolution lab", () => {
    render(<Backtest />);

    const lab = screen.getByTestId("calibration-evolution-lab");
    expect(within(lab).getByTestId("calibration-evolution-chart")).toHaveStyle({ minHeight: "260px" });
    expect(within(lab).getByTestId("calibration-timeline")).toBeInTheDocument();
    expect(within(lab).getByTestId("calibration-summary")).toBeInTheDocument();
    expect(within(lab).getByText("Observado na Cal.17")).toBeInTheDocument();
    expect(within(lab).getByText("Regra ajustada")).toBeInTheDocument();
    expect(within(lab).getByText("Comprovado na Cal.18?")).toBeInTheDocument();
    expect(within(lab).getByText(/Parcialmente/i)).toBeInTheDocument();
  });

  it("turns audit into evidence cards with error, rule, result and status", () => {
    render(<Backtest />);

    expect(screen.getByText("Evidências auditáveis")).toBeInTheDocument();
    expect(screen.getAllByText("Erro observado").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Resultado observado").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Regra ajustada").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Status").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/alvo agressivo/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/parcial/i).length).toBeGreaterThan(0);
  });
});
