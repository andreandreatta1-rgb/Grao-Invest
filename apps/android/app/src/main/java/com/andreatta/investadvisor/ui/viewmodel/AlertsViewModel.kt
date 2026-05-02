package com.andreatta.investadvisor.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.data.WhatsAppSettingsInput
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.ui.UiState
import com.andreatta.investadvisor.ui.userMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AlertsViewModel(
    private val repository: InvestmentRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<JsonSummary>>(UiState.Idle)
    val state: StateFlow<UiState<JsonSummary>> = _state.asStateFlow()

    fun loadWhatsapp(userId: Int) {
        execute { repository.whatsappSettings(userId) }
    }

    fun saveWhatsapp(input: WhatsAppSettingsInput) {
        execute { repository.saveWhatsappSettings(input) }
    }

    fun testWhatsapp(userId: Int) {
        execute { repository.sendWhatsappTest(userId) }
    }

    fun loadEvents(userId: Int) {
        execute { repository.alertEvents(userId) }
    }

    private fun execute(block: suspend () -> JsonSummary) {
        viewModelScope.launch {
            _state.value = UiState.Loading
            runCatching { block() }
                .onSuccess { _state.value = UiState.Success(it) }
                .onFailure { _state.value = UiState.Error(it.userMessage()) }
        }
    }
}
