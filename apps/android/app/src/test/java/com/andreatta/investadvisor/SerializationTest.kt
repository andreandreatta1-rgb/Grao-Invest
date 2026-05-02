package com.andreatta.investadvisor

import com.andreatta.investadvisor.network.AuthResponse
import com.andreatta.investadvisor.network.NetworkJson
import org.junit.Assert.assertEquals
import org.junit.Test

class SerializationTest {
    @Test
    fun authResponseIgnoresUnknownBackendFields() {
        val payload = """
            {
              "user_id": 42,
              "email": "andre@example.com",
              "access_token": "abc",
              "token_type": "bearer",
              "expires_in": 3600,
              "future_backend_field": {"nested": true}
            }
        """.trimIndent()

        val response = NetworkJson.decodeFromString<AuthResponse>(payload)

        assertEquals(42, response.userId)
        assertEquals("abc", response.accessToken)
        assertEquals("andre@example.com", response.email)
    }
}
