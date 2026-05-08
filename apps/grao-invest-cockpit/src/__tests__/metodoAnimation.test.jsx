import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Metodo, { metodoGraoScenes } from "../screens/Metodo.jsx";

describe("Metodo Grao animation player", () => {
  beforeEach(() => {
    vi.spyOn(window.HTMLMediaElement.prototype, "play").mockImplementation(() => undefined);
    vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the nine-scene onboarding as the primary Metodo experience", () => {
    render(<Metodo />);

    expect(metodoGraoScenes).toHaveLength(9);
    expect(screen.getByRole("button", { name: /Começar com áudio/i })).toBeInTheDocument();
    expect(screen.getByText("01/09")).toBeInTheDocument();
    expect(screen.getByText("Sem sinal vazio")).toBeInTheDocument();
    expect(screen.queryByText("O truque em 5 atos")).not.toBeInTheDocument();
    expect(screen.queryByText("Começar pelo método")).not.toBeInTheDocument();

    const navigator = screen.getByTestId("metodo-scene-navigator");
    expect(within(navigator).getAllByRole("button")).toHaveLength(9);
    expect(within(screen.getByTestId("metodo-media-stage")).queryByText("Sem sinal vazio")).not.toBeInTheDocument();
  });

  it("starts with audio from a user gesture and exposes audio/video asset paths", () => {
    render(<Metodo />);

    fireEvent.click(screen.getByRole("button", { name: /Começar com áudio/i }));

    expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled();
    expect(screen.getByText("Iniciando com áudio.")).toBeInTheDocument();

    const stage = screen.getByTestId("metodo-media-stage");
    const video = within(stage).getByTestId("metodo-scene-video");
    const audio = screen.getByTestId("metodo-scene-audio");
    expect(video).toHaveAttribute("src", "/assets/metodo-sequencia-09/video/01.mp4");
    expect(audio).toHaveAttribute("src", "/assets/metodo-sequencia-09/audio/01.mp3");
  });

  it("uses the static scene 03 image until its audio completes", () => {
    render(<Metodo />);

    fireEvent.click(screen.getByRole("button", { name: /Grãos de evidência/i }));

    const stage = screen.getByTestId("metodo-media-stage");
    expect(screen.getByText("03/09")).toBeInTheDocument();
    expect(within(stage).getByTestId("metodo-scene-image")).toHaveAttribute(
      "src",
      "/assets/metodo-sequencia-09/image/03.webp",
    );
    expect(within(stage).queryByTestId("metodo-scene-video")).not.toBeInTheDocument();
    expect(screen.getByTestId("metodo-scene-audio")).toHaveAttribute(
      "src",
      "/assets/metodo-sequencia-09/audio/03.mp3",
    );
  });

  it("keeps a direct path into the app after the presentation", () => {
    const onOpenMethodExample = vi.fn();
    render(<Metodo onOpenMethodExample={onOpenMethodExample} />);

    fireEvent.click(screen.getByRole("button", { name: /Entrar no app/i }));

    expect(onOpenMethodExample).toHaveBeenCalledTimes(1);
  });
});
