package com.andreatta.investadvisor

import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.network.NetworkJson
import com.andreatta.investadvisor.ui.screens.AssetFront
import com.andreatta.investadvisor.ui.screens.ThesisOperationCardModel
import com.andreatta.investadvisor.ui.screens.frontCards
import com.andreatta.investadvisor.ui.screens.homeFrontChoices
import com.andreatta.investadvisor.ui.screens.operationProgressToTarget
import com.andreatta.investadvisor.ui.screens.snapshot
import com.andreatta.investadvisor.ui.screens.thesisOperationsForTab
import com.andreatta.investadvisor.ui.screens.toThesisDashboardModel
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import java.time.LocalDate

class ThesisDashboardModelsTest {
    @Test
    fun initialHomeShowsOnlyThreeInvestmentFrontChoices() {
        val choices = homeFrontChoices()

        assertEquals(listOf(AssetFront.Stocks, AssetFront.Crypto, AssetFront.RealEstate), choices.map { it.front })
        assertEquals(listOf("B3", "Cripto", "Imóveis"), choices.map { it.title })
    }

    @Test
    fun parsesExecutiveThesisDashboardPayload() {
        val yesterday = LocalDate.now().minusDays(1).toString()
        val tomorrow = LocalDate.now().plusDays(1).toString()
        val raw = NetworkJson.parseToJsonElement(
            """
            {
              "generated_at": "2026-05-02T10:00:00+00:00",
              "phase_kickoff_date": "2026-04-27",
              "thesis_history_overview": {
                "total_tested": 1461,
                "success_count": 1110,
                "success_rate_pct": 75.98,
                "avg_result_pct": 2.9989
              },
              "thesis_executive_summary": {
                "historical": {
                  "thesis_count": 1390,
                  "expected_pct": 4.1994,
                  "achieved_pct": 3.0764,
                  "approved_count": 1110
                },
                "current": {
                  "thesis_count": 8,
                  "expected_pct": 0.9091,
                  "achieved_pct": 2.2792,
                  "approved_count": 0
                }
              },
              "thesis_open_operations": [
                {
                  "thesis_number": 1461,
                  "action": "SOLUSDT",
                  "status": "Aberta - Atencao",
                  "expected_result_pct": 0.8524,
                  "moment_result_pct": 2.2566,
                  "entry_price_brl": 83.7,
                  "current_price_brl": 89.42,
                  "open_days": 3,
                  "latest_price_at": "2026-05-04T23:09:59+00:00",
                  "thesis_raised_at": "2026-05-01T23:09:59+00:00",
                  "planned_exit_at": "$tomorrow",
                  "operation_plan": "Neutra ate $tomorrow.",
                  "structured_operation": "Iron Condor",
                  "exit_rule": "Reavaliar na proxima barra.",
                  "thesis_reason": "Preco em faixa estavel.",
                  "learning_note": "Aplicar penalidade aprendida."
                },
                {
                  "thesis_number": 1460,
                  "action": "BTCUSDT",
                  "status": "Aberta - Atencao",
                  "expected_result_pct": 0.50,
                  "moment_result_pct": -0.10,
                  "entry_price_brl": 500000.0,
                  "current_price_brl": 499500.0,
                  "open_days": 4,
                  "latest_price_at": "2026-05-04T23:09:59+00:00",
                  "thesis_raised_at": "2026-05-01T23:09:59+00:00",
                  "planned_exit_at": "$yesterday",
                  "operation_plan": "Compra ate $yesterday.",
                  "structured_operation": "Compra curta",
                  "exit_rule": "Encerrar por tempo.",
                  "thesis_reason": "Teste de tese vencida.",
                  "learning_note": "Nao deveria aparecer aberta."
                },
                {
                  "thesis_number": 10,
                  "action": "PETR4",
                  "status": "Fechada",
                  "moment_result_pct": 3.1
                }
              ]
            }
            """.trimIndent(),
        )

        val model = JsonSummary("Dashboard", emptyList(), raw.jsonObject).toThesisDashboardModel()

        assertNotNull(model)
        requireNotNull(model)
        assertEquals(1461, model.overview.totalTested)
        assertEquals(1110, model.overview.successCount)
        assertEquals(8, model.current.thesisCount)
        assertEquals(1, model.activeOperations.size)
        assertEquals(1461, model.activeOperations.first().thesisNumber)
        assertEquals(83.7, model.activeOperations.first().entryPrice!!, 0.0001)
        assertEquals(89.42, model.activeOperations.first().currentPrice!!, 0.0001)
        assertEquals(3, model.activeOperations.first().openDays)
        assertEquals("2026-05-04", model.activeOperations.first().latestAt)
        assertEquals(tomorrow, model.activeOperations.first().plannedExitAt)
    }

    @Test
    fun buildsHubCardsForStocksCryptoAndRealEstateWithReadableAccents() {
        val tomorrow = LocalDate.now().plusDays(1).toString()
        val raw = NetworkJson.parseToJsonElement(
            """
            {
              "generated_at": "2026-05-02T10:00:00+00:00",
              "phase_kickoff_date": "2026-04-27",
              "thesis_history_overview": {
                "total_tested": 3,
                "success_count": 2,
                "success_rate_pct": 66.67,
                "avg_result_pct": 1.25
              },
              "thesis_open_operations": [
                {
                  "thesis_number": 3,
                  "action": "PETR4",
                  "status": "Aberta - AtenÃ§Ã£o",
                  "phase": "pos_go_live",
                  "is_open": true,
                  "planned_exit_at": "$tomorrow",
                  "operation_plan": "Compra atÃ© $tomorrow.",
                  "thesis_reason": "AÃ§Ãµes com preÃ§o perto do suporte.",
                  "learning_note": "NÃ£o abrir sem confirmaÃ§Ã£o de volume."
                },
                {
                  "thesis_number": 2,
                  "action": "BTCUSDT",
                  "status": "Aberta",
                  "phase": "pos_go_live",
                  "is_open": true,
                  "planned_exit_at": "$tomorrow"
                },
                {
                  "thesis_number": 1,
                  "front": "imoveis",
                  "action": "Apartamento Vila Mariana",
                  "status": "Em estudo",
                  "phase": "pos_go_live",
                  "is_open": true,
                  "planned_exit_at": "$tomorrow"
                }
              ]
            }
            """.trimIndent(),
        )

        val model = JsonSummary("Dashboard", emptyList(), raw.jsonObject).toThesisDashboardModel()

        assertNotNull(model)
        requireNotNull(model)
        assertEquals("Ações B3", AssetFront.Stocks.label)
        assertEquals("Imóveis", AssetFront.RealEstate.label)
        assertEquals(1, model.snapshot(AssetFront.RealEstate).activeOperations.size)

        val stockOperation = model.snapshot(AssetFront.Stocks).activeOperations.first()
        assertEquals("Aberta - Atenção", stockOperation.status)
        assertEquals("Compra até $tomorrow.", stockOperation.operationPlan)
        assertEquals("Ações com preço perto do suporte.", stockOperation.thesisReason)
        assertEquals("Não abrir sem confirmação de volume.", stockOperation.learningNote)

        val cards = model.frontCards()
        assertEquals(listOf(AssetFront.Stocks, AssetFront.Crypto, AssetFront.RealEstate), cards.map { it.front })
        assertEquals(listOf("B3", "₿", "IM"), cards.map { it.iconLabel })
        assertEquals("Ações B3", cards[0].title)
        assertEquals("Cripto", cards[1].title)
        assertEquals("Imóveis", cards[2].title)
    }

    @Test
    fun computesProgressTowardExpectedReturnForOpenOperations() {
        assertEquals(50, operationProgressToTarget(operation(expectedPct = 4.0, resultPct = 2.0)).progressPct)
        assertEquals("50% da meta", operationProgressToTarget(operation(expectedPct = 4.0, resultPct = 2.0)).label)
        assertEquals(100, operationProgressToTarget(operation(expectedPct = 4.0, resultPct = 8.0)).progressPct)
        assertEquals(0, operationProgressToTarget(operation(expectedPct = 4.0, resultPct = -1.0)).progressPct)
        assertEquals(50, operationProgressToTarget(operation(expectedPct = -2.0, resultPct = -1.0)).progressPct)
        assertEquals(0, operationProgressToTarget(operation(expectedPct = null, resultPct = 1.0)).progressPct)
    }

    @Test
    fun filtersThesisOperationsByTabAndSearchText() {
        val operations = listOf(
            operation(thesisNumber = 1595, action = "B3SA3", isOpen = true, thesisReason = "Queda tecnica"),
            operation(thesisNumber = 1594, action = "SUZB3", isOpen = false, thesisReason = "Alta com volume"),
            operation(thesisNumber = 1593, action = "BPAC11", isOpen = true, thesisReason = "Banco com momentum"),
        )

        assertEquals(listOf(1595, 1593), thesisOperationsForTab(operations, query = "", openOnly = true).map { it.thesisNumber })
        assertEquals(listOf(1594), thesisOperationsForTab(operations, query = "", openOnly = false).map { it.thesisNumber })
        assertEquals(listOf(1593), thesisOperationsForTab(operations, query = "banco", openOnly = true).map { it.thesisNumber })
        assertEquals(listOf(1595), thesisOperationsForTab(operations, query = "B3SA3", openOnly = true).map { it.thesisNumber })
    }

    private fun operation(
        thesisNumber: Int = 1,
        action: String = "PETR4",
        isOpen: Boolean = true,
        expectedPct: Double? = 3.0,
        resultPct: Double? = 1.0,
        thesisReason: String = "Motivo de teste",
    ) = ThesisOperationCardModel(
        thesisNumber = thesisNumber,
        action = action,
        phase = "pos_go_live",
        front = AssetFront.Stocks,
        status = if (isOpen) "Aberta" else "Fechada",
        outcome = "",
        expectedPct = expectedPct,
        resultPct = resultPct,
        entryPrice = 10.0,
        currentPrice = 11.0,
        openDays = if (isOpen) 2 else 10,
        raisedAt = "2026-05-01",
        latestAt = "2026-05-02",
        plannedExitAt = "2026-05-05",
        isOpen = isOpen,
        operationPlan = "Compra ate 2026-05-05.",
        structuredOperation = "Compra direta",
        exitRule = "Sair se perder suporte.",
        thesisReason = thesisReason,
        learningNote = "Aprendizado de teste.",
    )
}
