package com.andreatta.investadvisor

import com.andreatta.investadvisor.network.AuthInterceptor
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AuthInterceptorTest {
    @Test
    fun addsBearerTokenWhenSessionHasToken() {
        val server = MockWebServer()
        server.enqueue(MockResponse().setBody("{}"))
        server.start()
        try {
            val client = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor { "token-123" })
                .build()

            client.newCall(Request.Builder().url(server.url("/health")).build()).execute().close()

            val request = server.takeRequest()
            assertEquals("Bearer token-123", request.getHeader("Authorization"))
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun skipsAuthorizationHeaderWhenTokenIsBlank() {
        val server = MockWebServer()
        server.enqueue(MockResponse().setBody("{}"))
        server.start()
        try {
            val client = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor { " " })
                .build()

            client.newCall(Request.Builder().url(server.url("/health")).build()).execute().close()

            val request = server.takeRequest()
            assertNull(request.getHeader("Authorization"))
        } finally {
            server.shutdown()
        }
    }
}
