import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mapDashboardSummaryToRealEstateTrades } from "../src/data/realEstateTheses.ts";

const summary = {
  thesis_open_operations: [
    {
      thesis_id: "imv-001",
      thesis_number: 301,
      front: "imoveis",
      action: "Galpao logistico Campinas",
      status: "Go-live",
      is_open: true,
      expected_result_pct: 12.5,
      moment_result_pct: 4.25,
      entry_price_brl: 500000,
      current_price_brl: 521250,
      operation_plan: "Comprar cota com cap rate acima da media historica.",
      structured_operation: "Renda + valorizacao",
      exit_rule: "Venda se vacancia passar de 12%",
      learning_note: "Vacancia setorial recalibrada.",
      source_url: "https://example.com/imv-001",
    },
    {
      thesis_id: "imv-002",
      thesis_number: 302,
      front: "imoveis",
      action: "Laje corporativa Faria Lima",
      status: "Encerrada",
      is_open: false,
      expected_result_pct: 8,
      moment_result_pct: null,
      entry_price_brl: 250000,
      current_price_brl: 270000,
      operation_plan: "Aguardar fechamento do ciclo de vacancia.",
      structured_operation: "Ganho de capital",
      exit_rule: "Encerrada no alvo",
      learning_note: "Spread comprimido em linha com o ciclo.",
      source_url: "https://example.com/imv-002",
    },
    {
      thesis_id: "b3-001",
      thesis_number: 101,
      front: "b3",
      action: "PETR4",
      status: "Go-live",
      is_open: true,
      expected_result_pct: 4.43,
      moment_result_pct: 2.36,
      entry_price_brl: 40.41,
      current_price_brl: 41.36,
      operation_plan: "Nao deve aparecer na tela de imoveis.",
      structured_operation: "Compra direta",
      exit_rule: "Stop tecnico",
      learning_note: "",
      source_url: "",
    },
  ],
};

describe("real estate thesis mapper", () => {
  it("maps only open real estate operations from dashboard summary into current Trade cards", () => {
    const trades = mapDashboardSummaryToRealEstateTrades(summary, true);

    assert.equal(trades.length, 1);
    assert.equal(trades[0].id, 301);
    assert.equal(trades[0].ticker, "Galpao logistico Campinas");
    assert.equal(trades[0].statusLabel, "Go-live");
    assert.equal(trades[0].resultPct, 4.25);
    assert.equal(trades[0].description, "Comprar cota com cap rate acima da media historica.");
    assert.equal(trades[0].strategy, "Renda + valorizacao");
    assert.equal(trades[0].maxGain, "+12,50%");
    assert.equal(trades[0].riskLabel, "Venda se vacancia passar de 12%");
    assert.equal(trades[0].link, "https://example.com/imv-001");
  });

  it("maps closed real estate operations when the Encerradas tab is selected", () => {
    const trades = mapDashboardSummaryToRealEstateTrades(summary, false);

    assert.equal(trades.length, 1);
    assert.equal(trades[0].id, 302);
    assert.equal(trades[0].ticker, "Laje corporativa Faria Lima");
    assert.equal(trades[0].resultPct, 8);
    assert.equal(trades[0].resultLabel, "esperado");
  });
});
