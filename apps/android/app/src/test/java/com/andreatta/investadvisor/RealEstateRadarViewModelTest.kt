package com.andreatta.investadvisor

import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.network.RealEstateCandidate
import com.andreatta.investadvisor.network.RealEstateCandidateAnalysis
import com.andreatta.investadvisor.network.RealEstateCandidatesResponse
import com.andreatta.investadvisor.network.RealEstateSummary
import com.andreatta.investadvisor.ui.viewmodel.RealEstateRadarViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.JsonObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class RealEstateRadarViewModelTest {
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
    fun refreshLoadsRealEstateCandidates() = runTest {
        val repository = FakeRepository(
            response = RealEstateCandidatesResponse(
                summary = RealEstateSummary(total = 1, statusCounts = mapOf("Em estudo" to 1)),
                items = listOf(candidate(id = 3, score = 76)),
            ),
        )
        val viewModel = RealEstateRadarViewModel(repository)

        viewModel.refresh()
        advanceUntilIdle()

        val state = viewModel.state.value
        assertFalse(state.isLoading)
        assertEquals(1, state.candidates.size)
        assertEquals("Casa retrofit leve", state.candidates.first().title)
        assertEquals("https://example.com/casa", state.candidates.first().sourceUrl)
        assertEquals(76, state.candidates.first().analysis.score)
    }

    @Test
    fun confirmDueDiligenceUpdatesCandidateInState() = runTest {
        val repository = FakeRepository(
            response = RealEstateCandidatesResponse(items = listOf(candidate(id = 7, score = 61))),
            updatedCandidate = candidate(id = 7, score = 88, status = "Diligencia OK"),
        )
        val viewModel = RealEstateRadarViewModel(repository)

        viewModel.refresh()
        advanceUntilIdle()
        viewModel.confirmDueDiligence(7, occupancyStatus = "desocupado", hasRegistration = true)
        advanceUntilIdle()

        val state = viewModel.state.value
        assertEquals(7, repository.updatedId)
        assertTrue(repository.patch.keys.contains("occupancy_status"))
        assertTrue(repository.patch.keys.contains("has_registration"))
        assertEquals("Diligencia OK", state.candidates.first().status)
        assertEquals(88, state.candidates.first().analysis.score)
    }

    private class FakeRepository(
        private val response: RealEstateCandidatesResponse,
        private val updatedCandidate: RealEstateCandidate = response.items.first(),
    ) : InvestmentRepository {
        var updatedId: Int? = null
        var patch: JsonObject = JsonObject(emptyMap())

        override suspend fun realEstateCandidates(): RealEstateCandidatesResponse = response

        override suspend fun updateRealEstateCandidate(
            candidateId: Int,
            patch: JsonObject,
        ): RealEstateCandidate {
            updatedId = candidateId
            this.patch = patch
            return updatedCandidate
        }
    }

    private fun candidate(
        id: Int,
        score: Int,
        status: String = "Em estudo",
    ): RealEstateCandidate = RealEstateCandidate(
        id = id,
        title = "Casa retrofit leve",
        sourceUrl = "https://example.com/casa",
        origin = "Venda direta vendedor",
        strategy = "Retrofit",
        status = status,
        analysis = RealEstateCandidateAnalysis(score = score, confidence = 45),
    )
}
