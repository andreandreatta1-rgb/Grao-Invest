import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import { PerdizesCasePortfolio } from "../screens/JornadaTese.jsx";

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

  it("opens real source links from each competitor-map sale reference when provided", async () => {
    const user = userEvent.setup();
    const item = {
      id: "#LINK-01",
      title: "REAL TARGET - Pinheiros Capote Valente 33m 1q",
      role: "Caso real aberto",
      strategy: "Leilão extrajudicial + HF leve",
      sourceUrl: "https://example.com/candidato",
      area: "33 m²",
      firstAuctionDate: "20/05/2026",
      secondAuctionDate: "22/05/2026",
      temporalStatus: "P0 aberto",
      temporalType: "warning",
      firstAuction: 339846,
      secondAuction: 350000,
      purchasePrice: 339846,
      comparator: 566409,
      saleBase: 566409,
      auctioneerFee: 0,
      acquisitionCosts: 12000,
      renovationCosts: 28000,
      carryingCosts: 9000,
      sellingCosts: 34000,
      score: 70,
      confidence: 43,
      color: "#c8a444",
      icon: "T",
      iconLabel: "Target",
      iconBasis: "Caso de teste com referências reais.",
      decision: "Investigar",
      whyRadar: "Validar saída por comparáveis reais antes de qualquer lance.",
      p0: ["Validar valor de saída"],
      quote: "Referência sem fonte não sustenta decisão.",
      saleComparables: [
        { price: 566409, source: "Viva Real", sourceUrl: "https://example.com/ref-01", note: "comparável base" },
        { price: 594730, source: "QuintoAndar", sourceUrl: "https://example.com/ref-02", note: "faixa alta" },
        { price: 532425, source: "Zap", sourceUrl: "https://example.com/ref-03", note: "faixa baixa" },
      ],
    };

    render(<PerdizesCasePortfolio dataTestId="linked-refs-portfolio" items={[item]} title="Teste de links" intro="Teste" />);

    const portfolio = screen.getByTestId("linked-refs-portfolio");
    await user.click(within(portfolio).getByRole("button", { name: /Abrir REAL TARGET - Pinheiros Capote Valente/i }));

    const links = within(portfolio).getAllByRole("link", { name: /Abrir link real da Ref\. venda/i });
    expect(links).toHaveLength(3);
    expect(links[0]).toHaveAttribute("href", "https://example.com/ref-01");
    expect(links[1]).toHaveAttribute("href", "https://example.com/ref-02");
    expect(links[2]).toHaveAttribute("href", "https://example.com/ref-03");
    expect(within(portfolio).getByText(/3 links reais/i)).toBeInTheDocument();
    expect(within(portfolio).queryByText(/sem link real/i)).not.toBeInTheDocument();
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

  it("recomputes expanded financial outcome from the visible live cost lines", async () => {
    const user = userEvent.setup();
    const item = {
      id: "#IM-FOLHA-FRAZAO-SAUDE-37528",
      title: "Frazão Itaú Saúde Rua Abagiba 74m2",
      role: "Caso real aberto · Aberta - Atencao",
      strategy: "Leilão + HF",
      score: 71,
      confidence: 44,
      color: "#69e58f",
      icon: "⚖",
      iconLabel: "Leilão / Caixa",
      iconBasis: "Preço com edital, praça, ocupação, matrícula e débitos como P0.",
      temporalStatus: "3 P0 abertos",
      temporalType: "warning",
      sourceValidation: { label: "Fonte validada", type: "success" },
      decision: "Aberto com pendências",
      whyRadar: "Comparável aderente elevou a saída base, mas ainda há P0.",
      sourceUrl: "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528",
      sourceOrigin: "Frazao Leiloes / Itau",
      area: "74.14",
      floor: "andar a validar",
      bedrooms: "3",
      bathrooms: "banheiros a validar",
      parking: "2",
      building: "Rua Abagiba",
      firstAuctionDate: "18/05/2026",
      secondAuctionDate: "Confirmar ocupação",
      firstBadgeLabel: "Radar",
      secondBadgeLabel: "Próx.",
      firstAuction: 388700,
      secondAuction: 414859,
      purchasePrice: 388700,
      comparator: 600000,
      saleBase: 600000,
      auctioneerFee: 19435,
      acquisitionCosts: 3887,
      renovationCosts: 28000,
      carryingCosts: 17600,
      sellingCosts: 36000,
      totalCost: 512779,
      netProfit: 12378,
      roiPct: 7.5,
      fixedIncomePct: 6.5,
      purchaseCostLabel: "Preço do lote",
      firstPriceLabel: "Preço entrada",
      firstPriceNote: "preço observado",
      secondPriceLabel: "Teto Halley",
      secondPriceNote: "limite disciplinado",
      salePriceLabel: "Saída base",
      salePriceNote: "comparável anunciado",
      p0: ["Confirmar ocupação"],
      p0Actions: [{
        title: "Confirmar ocupação",
        action: "Validar ocupação e desocupação.",
        validationRoute: ["Abrir edital e laudo.", "Confirmar com leiloeiro."],
        validationExitCriteria: "Ocupacao comprovada ou candidato fechado.",
        requiresUserAccess: true,
      }],
      quote: "Ainda não é compra. É candidato vivo enquanto a prova melhora a confiança.",
      isLiveCandidate: true,
      isRealCandidate: true,
      canDiscard: false,
    };

    render(<PerdizesCasePortfolio items={[item]} />);

    const portfolio = screen.getByTestId("perdizes-case-portfolio");
    await user.click(within(portfolio).getByRole("button", { name: /Abrir Frazão Itaú Saúde/i }));

    expect(within(portfolio).getByText("R$ 493.622")).toBeInTheDocument();
    expect(within(portfolio).getByText("R$ 106.378")).toBeInTheDocument();
    expect(within(portfolio).getByText(/21,6%/i)).toBeInTheDocument();
    expect(within(portfolio).getByText("Roteiro de validacao")).toBeInTheDocument();
    expect(within(portfolio).getByText(/Abrir edital e laudo/i)).toBeInTheDocument();
    expect(within(portfolio).getByText(/Se pedir cadastro\/login/i)).toBeInTheDocument();
    expect(within(portfolio).queryByText("R$ 512.779")).not.toBeInTheDocument();
    expect(within(portfolio).queryByText("R$ 12.378")).not.toBeInTheDocument();
  });
});
