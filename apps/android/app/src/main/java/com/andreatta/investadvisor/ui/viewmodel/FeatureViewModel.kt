package com.andreatta.investadvisor.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.andreatta.investadvisor.data.FeatureAction
import com.andreatta.investadvisor.data.FeatureInput
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.ui.UiState
import com.andreatta.investadvisor.ui.userMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class FeatureViewModel(
    private val repository: InvestmentRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<JsonSummary>>(UiState.Idle)
    val state: StateFlow<UiState<JsonSummary>> = _state.asStateFlow()

    fun run(action: FeatureAction, input: FeatureInput) {
        viewModelScope.launch {
            _state.value = UiState.Loading
            runCatching { repository.loadFeature(action, input) }
                .onSuccess { _state.value = UiState.Success(it) }
                .onFailure { _state.value = UiState.Error(it.userMessage()) }
        }
    }
}
