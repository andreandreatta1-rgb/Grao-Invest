package com.andreatta.investadvisor

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class AppNavigationTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun firstLaunchShowsLoginAndDisclaimer() {
        composeRule.onNodeWithText("Entrar").assertIsDisplayed()
        composeRule.onNodeWithText("Conteudo educacional; nao e recomendacao de investimento.").assertIsDisplayed()
    }
}
