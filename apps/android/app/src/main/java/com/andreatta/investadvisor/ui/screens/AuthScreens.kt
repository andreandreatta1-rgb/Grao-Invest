package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Login
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.andreatta.investadvisor.ui.UiState
import com.andreatta.investadvisor.ui.viewmodel.AuthViewModel

@Composable
fun AuthScreen(viewModel: AuthViewModel, modifier: Modifier = Modifier) {
    var signupMode by rememberSaveable { mutableStateOf(false) }
    var tenantName by rememberSaveable { mutableStateOf("Minha carteira") }
    var fullName by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var otp by rememberSaveable { mutableStateOf("") }
    var accepted by rememberSaveable { mutableStateOf(true) }
    val state by viewModel.state.collectAsState()

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        SectionHeader(
            title = "Grao Invest",
            subtitle = "Assistente educacional de renda variavel e multiativos.",
        )
        DisclaimerBar()

        if (signupMode) {
            OutlinedTextField(
                value = tenantName,
                onValueChange = { tenantName = it },
                label = { Text("Nome do tenant") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = fullName,
                onValueChange = { fullName = it },
                label = { Text("Nome completo") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Senha") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        if (!signupMode) {
            OutlinedTextField(
                value = otp,
                onValueChange = { otp = it.take(6) },
                label = { Text("Codigo MFA opcional") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
        }

        Row {
            Checkbox(checked = accepted, onCheckedChange = { accepted = it })
            Text(
                text = "Li e aceito o uso educacional, sem recomendacao de investimento.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 12.dp),
            )
        }

        when (val current = state) {
            UiState.Loading -> LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            is UiState.Error -> Text(
                text = current.message,
                color = MaterialTheme.colorScheme.error,
            )
            is UiState.Success -> Text(
                text = current.data.message,
                color = MaterialTheme.colorScheme.primary,
            )
            UiState.Idle -> Spacer(Modifier.height(1.dp))
        }

        Button(
            enabled = accepted && email.isNotBlank() && password.isNotBlank(),
            onClick = {
                viewModel.clearMessage()
                if (signupMode) {
                    viewModel.signup(tenantName, fullName, email, password)
                } else {
                    viewModel.login(email, password, otp.takeIf { it.isNotBlank() })
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(
                imageVector = if (signupMode) Icons.Default.PersonAdd else Icons.AutoMirrored.Filled.Login,
                contentDescription = null,
            )
            Text(if (signupMode) "Criar conta" else "Entrar", modifier = Modifier.padding(start = 8.dp))
        }

        TextButton(
            onClick = {
                signupMode = !signupMode
                viewModel.clearMessage()
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (signupMode) "Ja tenho conta" else "Criar nova conta")
        }
    }
}
