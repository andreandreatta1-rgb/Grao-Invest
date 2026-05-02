package com.andreatta.investadvisor

import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.ui.UiState
import com.andreatta.investadvisor.ui.viewmodel.DashboardViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun refreshLoadsDashboardSummary() = runTest {
        val repository = FakeRepository(
            dashboard = JsonSummary(
                title = "Resumo",
                rows = listOf("Perfil: moderado", "Sinais: 2"),
                raw = JsonObject(mapOf("investor_profile" to JsonPrimitive("moderado"))),
            ),
        )
        val viewModel = DashboardViewModel(repository)

        viewModel.refresh(7)
        advanceUntilIdle()

        val state = viewModel.state.value
        assertTrue(state is UiState.Success)
        assertEquals("Resumo", (state as UiState.Success).data.title)
    }

    @Test
    fun refreshShowsErrorWhenRepositoryFails() = runTest {
        val viewModel = DashboardViewModel(FakeRepository(error = IllegalStateException("offline")))

        viewModel.refresh(7)
        advanceUntilIdle()

        val state = viewModel.state.value
        assertTrue(state is UiState.Error)
        assertEquals("offline", (state as UiState.Error).message)
    }

    private class FakeRepository(
        private val dashboard: JsonSummary? = null,
        private val error: Throwable? = null,
    ) : InvestmentRepository {
        override suspend fun dashboardSummary(userId: Int): JsonSummary {
            error?.let { throw it }
            return dashboard ?: error("missing dashboard")
        }
    }
}
