package com.andreatta.investadvisor.ui

sealed interface UiState<out T> {
    data object Idle : UiState<Nothing>
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T) : UiState<T>
    data class Error(val message: String) : UiState<Nothing>
}

fun Throwable.userMessage(): String = message?.takeIf { it.isNotBlank() }
    ?: "Nao foi possivel concluir a operacao."
