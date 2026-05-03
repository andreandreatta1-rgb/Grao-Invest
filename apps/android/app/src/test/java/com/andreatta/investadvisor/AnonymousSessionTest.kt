package com.andreatta.investadvisor

import com.andreatta.investadvisor.data.AppSession
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AnonymousSessionTest {
    @Test
    fun defaultSessionOpensAnonymousAccess() {
        val session = AppSession()

        assertTrue(session.isAuthenticated)
        assertEquals(1, session.userId)
        assertEquals("acesso.anonimo@grao.local", session.email)
    }
}
