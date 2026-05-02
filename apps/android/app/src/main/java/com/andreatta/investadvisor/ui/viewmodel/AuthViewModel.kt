package com.andreatta.investadvisor.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.data.SessionStore
import com.andreatta.investadvisor.ui.UiState
import com.andreatta.investadvisor.ui.userMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AuthUiModel(
    val message: String,
)

class AuthViewModel(
    private val repository: InvestmentRepository,
    private val sessionStore: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<AuthUiModel>>(UiState.Idle)
    val state: StateFlow<UiState<AuthUiModel>> = _state.asStateFlow()

    fun login(email: String, password: String, otpCode: String?) {
        viewModelScope.launch {
            _state.value = UiState.Loading
            runCatching { repository.login(email.trim(), password, otpCode) }
                .onSuccess { response ->
                    val token = response.accessToken
                    val userId = response.userId
                    if (token.isNullOrBlank() || userId == null) {
                        _state.value = UiState.Error("Login sem token. Verifique MFA ou credenciais.")
                    } else {
                        sessionStore.saveAuth(userId, response.email ?: email.trim(), token)
                        _state.value = UiState.Success(AuthUiModel("Sessao iniciada."))
                    }
                }
                .onFailure { _state.value = UiState.Error(it.userMessage()) }
        }
    }

    fun signup(tenantName: String, fullName: String, email: String, password: String) {
        viewModelScope.launch {
            _state.value = UiState.Loading
            runCatching { repository.signup(tenantName, fullName, email.trim(), password) }
                .onSuccess {
                    _state.value = UiState.Success(
                        AuthUiModel("Conta criada. Entre com email e senha para abrir sessao."),
                    )
                }
                .onFailure { _state.value = UiState.Error(it.userMessage()) }
        }
    }

    fun clearMessage() {
        _state.value = UiState.Idle
    }
}
