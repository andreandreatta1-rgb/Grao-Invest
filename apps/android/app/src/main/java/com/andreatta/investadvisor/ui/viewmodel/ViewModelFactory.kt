package com.andreatta.investadvisor.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider

inline fun <reified T : ViewModel> simpleViewModelFactory(
    crossinline create: () -> T,
): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <VM : ViewModel> create(modelClass: Class<VM>): VM {
        require(modelClass.isAssignableFrom(T::class.java)) {
            "Unexpected ViewModel ${modelClass.name}"
        }
        return create() as VM
    }
}
