package com.andreatta.investadvisor

import com.andreatta.investadvisor.ui.screens.GraoTradeStatus
import com.andreatta.investadvisor.ui.screens.graoPrototypeBottomNavItems
import com.andreatta.investadvisor.ui.screens.graoPrototypeMarketAssets
import com.andreatta.investadvisor.ui.screens.graoPrototypeTabs
import com.andreatta.investadvisor.ui.screens.graoPrototypeTrades
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GraoInvestPrototypeModelsTest {
    @Test
    fun exposesPrototypeTabsNavigationAndMockTrades() {
        assertEquals(listOf("Teses", "Mercado", "Analisar"), graoPrototypeTabs.map { it.label })
        assertEquals(listOf("Teses", "Mercado", "Analisar", "Perfil"), graoPrototypeBottomNavItems.map { it.label })

        assertEquals(3, graoPrototypeTrades.size)
        assertEquals(1595, graoPrototypeTrades.first().id)
        assertEquals("B3SA3", graoPrototypeTrades.first().ticker)
        assertEquals(GraoTradeStatus.Invalid, graoPrototypeTrades.first().status)
        assertEquals("Aberta · Invalidada", graoPrototypeTrades.first().statusLabel)
        assertTrue(graoPrototypeTrades.any { it.status == GraoTradeStatus.Warn })
        assertTrue(graoPrototypeMarketAssets.any { it.name == "Petróleo Brasileiro" })
    }

    @Test
    fun keepsPortugueseAccentsReadableInVisibleCopy() {
        val visibleCopy = buildString {
            graoPrototypeTrades.forEach { trade ->
                appendLine(trade.statusLabel)
                appendLine(trade.description)
                trade.pills.forEach { pill ->
                    appendLine(pill.label)
                    appendLine(pill.value)
                }
            }
            graoPrototypeMarketAssets.forEach { asset ->
                appendLine(asset.name)
            }
        }

        assertTrue(visibleCopy.contains("Atenção"))
        assertTrue(visibleCopy.contains("até"))
        assertTrue(visibleCopy.contains("direção"))
        assertTrue(visibleCopy.contains("Petróleo"))
        assertFalse(visibleCopy.contains("Ã"))
        assertFalse(visibleCopy.contains("Â"))
    }
}
