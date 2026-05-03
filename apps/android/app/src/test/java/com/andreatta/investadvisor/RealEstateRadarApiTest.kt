package com.andreatta.investadvisor

import com.andreatta.investadvisor.network.ApiClientFactory
import com.andreatta.investadvisor.network.RealEstateCandidateRequest
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RealEstateRadarApiTest {
    @Test
    fun listsCreatesAndUpdatesRealEstateCandidates() = runTest {
        val server = MockWebServer()
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(
                    """
                    {
                      "summary": {"total": 1, "status_counts": {"Aberto com pendencias": 1}},
                      "items": [{
                        "id": 7,
                        "title": "Apto Sao Miguel Caixa",
                        "source_url": "https://example.com/anuncio-real",
                        "origin": "Leilao Caixa",
                        "strategy": "Revenda rapida",
                        "city": "Sao Paulo",
                        "neighborhood": "Sao Miguel Paulista",
                        "asking_price": 139015.11,
                        "status": "Aberto com pendencias",
                        "analysis": {
                          "score": 70,
                          "confidence": 30,
                          "suggested_status": "Aberto com pendencias",
                          "next_action": "Confirmar ocupacao",
                          "cash_needed": 85000,
                          "max_purchase_price": 152300,
                          "price_gap_to_ceiling": -13284.89,
                          "price_ceiling_status": "Dentro do teto",
                          "target_roi_pct": 20,
                          "pending_items": [
                            {"title": "Confirmar ocupacao", "priority": "P0", "status": "aberta"}
                          ],
                          "scenarios": {
                            "base": {"sale_price": 200000, "net_profit": 18500, "roi_pct": 21.76}
                          }
                        }
                      }]
                    }
                    """.trimIndent(),
                ),
        )
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(
                    """
                    {
                      "id": 8,
                      "title": "Casa retrofit leve",
                      "origin": "Venda direta vendedor",
                      "strategy": "Retrofit",
                      "status": "Em estudo",
                      "analysis": {"score": 76, "confidence": 45, "pending_items": []}
                    }
                    """.trimIndent(),
                ),
        )
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(
                    """
                    {
                      "id": 7,
                      "title": "Apto Sao Miguel Caixa",
                      "status": "Diligencia",
                      "analysis": {"score": 82, "confidence": 75, "pending_items": []}
                    }
                    """.trimIndent(),
                ),
        )
        server.start()
        try {
            val api = ApiClientFactory.create(
                baseUrl = server.url("/").toString(),
                tokenProvider = { "token" },
                debug = false,
            )

            val listResponse = api.realEstateCandidates().body()!!
            val candidate = listResponse.items.first()
            assertEquals(7, candidate.id)
            assertEquals("https://example.com/anuncio-real", candidate.sourceUrl)
            assertEquals("Confirmar ocupacao", candidate.analysis.nextAction)
            assertEquals(152300.0, candidate.analysis.maxPurchasePrice ?: 0.0, 0.001)
            assertEquals("Dentro do teto", candidate.analysis.priceCeilingStatus)
            assertEquals("P0", candidate.analysis.pendingItems.first().priority)
            assertEquals(18500.0, candidate.analysis.scenarios.base?.netProfit ?: 0.0, 0.001)

            api.createRealEstateCandidate(
                RealEstateCandidateRequest(
                    title = "Casa retrofit leve",
                    origin = "Venda direta vendedor",
                    strategy = "Retrofit",
                    askingPrice = 420000.0,
                ),
            )
            api.updateRealEstateCandidate(
                7,
                buildJsonObject {
                    put("occupancy_status", "desocupado")
                    put("has_registration", true)
                },
            )

            assertEquals("GET", server.takeRequest().method)
            val createRequest = server.takeRequest()
            assertEquals("POST", createRequest.method)
            assertEquals("/api/real-estate/candidates", createRequest.path)
            assertTrue(createRequest.body.readUtf8().contains("Casa retrofit leve"))
            val updateRequest = server.takeRequest()
            assertEquals("PATCH", updateRequest.method)
            assertEquals("/api/real-estate/candidates/7", updateRequest.path)
            assertEquals("Bearer token", updateRequest.getHeader("Authorization"))
        } finally {
            server.shutdown()
        }
    }
}
