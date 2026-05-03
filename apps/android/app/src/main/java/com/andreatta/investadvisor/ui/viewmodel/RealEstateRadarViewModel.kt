package com.andreatta.investadvisor.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.network.RealEstateCandidate
import com.andreatta.investadvisor.network.RealEstateCandidateRequest
import com.andreatta.investadvisor.network.RealEstateSummary
import com.andreatta.investadvisor.ui.userMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

data class RealEstateRadarUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val summary: RealEstateSummary = RealEstateSummary(),
    val candidates: List<RealEstateCandidate> = emptyList(),
    val actionMessage: String? = null,
)

class RealEstateRadarViewModel(
    private val repository: InvestmentRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(RealEstateRadarUiState())
    val state: StateFlow<RealEstateRadarUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, errorMessage = null)
            runCatching { repository.realEstateCandidates() }
                .onSuccess { response ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        summary = response.summary,
                        candidates = response.items,
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        errorMessage = error.userMessage(),
                    )
                }
        }
    }

    fun createCandidate(input: RealEstateCandidateRequest) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, errorMessage = null)
            runCatching { repository.createRealEstateCandidate(input) }
                .onSuccess { candidate ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        candidates = listOf(candidate) + _state.value.candidates,
                        actionMessage = "Candidato criado",
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        errorMessage = error.userMessage(),
                    )
                }
        }
    }

    fun confirmDueDiligence(
        candidateId: Int,
        occupancyStatus: String? = null,
        hasRegistration: Boolean? = null,
        hasDebtCheck: Boolean? = null,
    ) {
        val patch = buildJsonObject {
            occupancyStatus?.let { put("occupancy_status", it) }
            hasRegistration?.let { put("has_registration", it) }
            hasDebtCheck?.let { put("has_debt_check", it) }
        }
        updateCandidate(candidateId, patch, "Diligencia atualizada")
    }

    private fun updateCandidate(candidateId: Int, patch: JsonObject, message: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, errorMessage = null)
            runCatching { repository.updateRealEstateCandidate(candidateId, patch) }
                .onSuccess { candidate ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        candidates = _state.value.candidates.replace(candidate),
                        actionMessage = message,
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        errorMessage = error.userMessage(),
                    )
                }
        }
    }
}

private fun List<RealEstateCandidate>.replace(candidate: RealEstateCandidate): List<RealEstateCandidate> {
    var replaced = false
    val updated = map { current ->
        if (current.id == candidate.id) {
            replaced = true
            candidate
        } else {
            current
        }
    }
    return if (replaced) updated else listOf(candidate) + updated
}
