package com.andreatta.investadvisor

import com.andreatta.investadvisor.network.ApiClientFactory
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Test

class ThesisAiAnalysisApiTest {
    @Test
    fun postsAiThesisAnalysisToBackend() = runTest {
        val server = MockWebServer()
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(
                    """
                    {
                      "instrument": "PETR4",
                      "provider": "local_fallback",
                      "education_disclaimer": "Conteudo educacional; nao e recomendacao."
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

            api.aiThesisAnalysis(
                buildJsonObject {
                    put("user_id", 7)
                    put("instrument", "PETR4")
                    put("question", "Quais pontos observar?")
                    put("horizon_days", 20)
                },
            )

            val request = server.takeRequest()
            assertEquals("POST", request.method)
            assertEquals("/api/theses/ai-analysis", request.path)
            assertEquals("Bearer token", request.getHeader("Authorization"))
        } finally {
            server.shutdown()
        }
    }
}
