package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.andreatta.investadvisor.data.AppSession
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.data.SessionStore
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(
    session: AppSession,
    sessionStore: SessionStore,
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    var baseUrl by rememberSaveable(session.baseUrl) { mutableStateOf(session.baseUrl) }
    var showLogout by rememberSaveable { mutableStateOf(false) }
    var healthMessage by rememberSaveable { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    if (showLogout) {
        AlertDialog(
            onDismissRequest = { showLogout = false },
            title = { Text("Sair da conta") },
            text = { Text("A sessao local sera removida deste aparelho.") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showLogout = false
                        scope.launch { sessionStore.logout() }
                    },
                ) {
                    Text("Sair")
                }
            },
            dismissButton = {
                TextButton(onClick = { showLogout = false }) {
                    Text("Cancelar")
                }
            },
        )
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionHeader("Configuracoes", "Sessao, API e seguranca local.")
        DisclaimerBar()
        OutlinedTextField(
            value = baseUrl,
            onValueChange = { baseUrl = it },
            label = { Text("Base API URL") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(
                onClick = { scope.launch { sessionStore.updateBaseUrl(baseUrl) } },
                modifier = Modifier.weight(1f),
            ) {
                Icon(Icons.Default.Save, contentDescription = null)
                Text("Salvar URL", modifier = Modifier.padding(start = 8.dp))
            }
            Button(
                onClick = {
                    scope.launch {
                        healthMessage = runCatching { repository.health().rows.joinToString(" | ") }
                            .getOrElse { it.message ?: "Falha no healthcheck" }
                    }
                },
                modifier = Modifier.weight(1f),
            ) {
                Text("Health")
            }
        }
        if (healthMessage.isNotBlank()) {
            Text(healthMessage)
        }
        Text("Usuario: ${session.email}")
        Text("User ID: ${session.userId ?: "-"}")
        Button(onClick = { showLogout = true }, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null)
            Text("Sair", modifier = Modifier.padding(start = 8.dp))
        }
    }
}
