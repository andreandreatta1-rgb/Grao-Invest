package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Checkbox
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.andreatta.investadvisor.data.AppSession
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.data.WhatsAppSettingsInput
import com.andreatta.investadvisor.ui.viewmodel.AlertsViewModel
import com.andreatta.investadvisor.ui.viewmodel.simpleViewModelFactory

@Composable
fun AlertsScreen(
    session: AppSession,
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<AlertsViewModel>(
        key = "alerts",
        factory = simpleViewModelFactory { AlertsViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()
    var phone by rememberSaveable { mutableStateOf("+5511971062620") }
    var displayName by rememberSaveable { mutableStateOf("Andre") }
    var optIn by rememberSaveable { mutableStateOf(true) }
    var thesisNew by rememberSaveable { mutableStateOf(true) }
    var thesisUpdate by rememberSaveable { mutableStateOf(true) }
    var stockAlert by rememberSaveable { mutableStateOf(true) }
    var dailyDigest by rememberSaveable { mutableStateOf(true) }
    var confidence by rememberSaveable { mutableStateOf("55") }
    var movePct by rememberSaveable { mutableStateOf("3") }
    var newsMagnitude by rememberSaveable { mutableStateOf("0.75") }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionHeader("Alertas", "WhatsApp, regras e historico auditavel.")
        DisclaimerBar()

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            Text("Opt-in WhatsApp", modifier = Modifier.weight(1f))
            Switch(checked = optIn, onCheckedChange = { optIn = it })
        }
        OutlinedTextField(
            value = phone,
            onValueChange = { phone = it },
            label = { Text("Numero WhatsApp") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = displayName,
            onValueChange = { displayName = it },
            label = { Text("Nome exibido") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        CategoryToggle("Nova tese", thesisNew) { thesisNew = it }
        CategoryToggle("Evolucao da tese", thesisUpdate) { thesisUpdate = it }
        CategoryToggle("Alerta de acao", stockAlert) { stockAlert = it }
        CategoryToggle("Resumo diario", dailyDigest) { dailyDigest = it }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedTextField(
                value = confidence,
                onValueChange = { confidence = numeric(it) },
                label = { Text("Confianca tese %") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = movePct,
                onValueChange = { movePct = numeric(it) },
                label = { Text("Variacao %") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.weight(1f),
            )
        }
        OutlinedTextField(
            value = newsMagnitude,
            onValueChange = { newsMagnitude = numeric(it) },
            label = { Text("Magnitude noticia") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth(),
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            ActionButton("Carregar", onClick = {
                session.userId?.let { viewModel.loadWhatsapp(it) }
            }, modifier = Modifier.weight(1f))
            ActionButton("Salvar", onClick = {
                session.userId?.let { userId ->
                    viewModel.saveWhatsapp(
                        WhatsAppSettingsInput(
                            userId = userId,
                            phoneNumber = phone,
                            displayName = displayName.takeIf { it.isNotBlank() },
                            optIn = optIn,
                            thesisNew = thesisNew,
                            thesisUpdate = thesisUpdate,
                            stockAlert = stockAlert,
                            dailyDigest = dailyDigest,
                            thesisConfidencePct = confidence.toDoubleOrNull() ?: 55.0,
                            stockPriceMovePct = movePct.toDoubleOrNull() ?: 3.0,
                            newsMagnitude = newsMagnitude.toDoubleOrNull() ?: 0.75,
                        ),
                    )
                }
            }, modifier = Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            ActionButton("Enviar teste", onClick = {
                session.userId?.let { viewModel.testWhatsapp(it) }
            }, modifier = Modifier.weight(1f))
            ActionButton("Historico", onClick = {
                session.userId?.let { viewModel.loadEvents(it) }
            }, modifier = Modifier.weight(1f))
        }
        SummaryState(state, idleText = "Configure o canal ou consulte eventos recentes.")
    }
}

@Composable
private fun CategoryToggle(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Checkbox(checked = checked, onCheckedChange = onChange)
        Text(label, modifier = Modifier.padding(top = 12.dp))
    }
}

private fun numeric(value: String): String = value.filter { it.isDigit() || it == '.' }
