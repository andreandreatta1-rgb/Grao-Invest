package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.ui.UiState

const val DISCLAIMER_TEXT = "Conteúdo educacional; não é recomendação de investimento."

private val SharedCard = Color(0xFF141C30)
private val SharedText = Color.White
private val SharedMuted = Color(0xFF8A9BC0)
private val SharedTeal = Color(0xFF00D4AA)

@Composable
fun DisclaimerBar(modifier: Modifier = Modifier) {
    AssistChip(
        onClick = {},
        label = { Text(DISCLAIMER_TEXT) },
        leadingIcon = {
            Icon(Icons.Default.CheckCircle, contentDescription = null)
        },
        colors = AssistChipDefaults.assistChipColors(
            containerColor = SharedCard,
            labelColor = SharedMuted,
            leadingIconContentColor = SharedTeal,
        ),
        modifier = modifier.fillMaxWidth(),
    )
}

@Composable
fun SectionHeader(title: String, subtitle: String? = null, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
            color = SharedText,
        )
        if (!subtitle.isNullOrBlank()) {
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = SharedMuted,
            )
        }
    }
}

@Composable
fun SummaryState(
    state: UiState<JsonSummary>,
    idleText: String,
    modifier: Modifier = Modifier,
) {
    when (state) {
        UiState.Idle -> EmptyPanel(idleText, modifier)
        UiState.Loading -> LoadingPanel(modifier)
        is UiState.Error -> ErrorPanel(state.message, modifier)
        is UiState.Success -> SummaryPanel(state.data, modifier)
    }
}

@Composable
fun ActionButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    ElevatedButton(
        onClick = onClick,
        enabled = enabled,
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 10.dp),
        modifier = modifier,
    ) {
        Icon(Icons.Default.PlayArrow, contentDescription = null)
        Text(text = label, modifier = Modifier.padding(start = 8.dp))
    }
}

@Composable
fun RefreshButton(label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    ElevatedButton(
        onClick = onClick,
        colors = ButtonDefaults.elevatedButtonColors(
            containerColor = SharedCard,
            contentColor = SharedTeal,
        ),
        modifier = modifier,
    ) {
        Icon(Icons.Default.Refresh, contentDescription = null)
        Text(text = label, modifier = Modifier.padding(start = 8.dp))
    }
}

@Composable
private fun LoadingPanel(modifier: Modifier = Modifier) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.outlinedCardColors(containerColor = SharedCard, contentColor = SharedText),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.padding(16.dp),
        ) {
            CircularProgressIndicator(color = SharedTeal)
            Text("Carregando dados...", color = SharedText)
        }
    }
}

@Composable
private fun EmptyPanel(text: String, modifier: Modifier = Modifier) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.outlinedCardColors(containerColor = SharedCard, contentColor = SharedText),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = SharedMuted,
            modifier = Modifier.padding(16.dp),
        )
    }
}

@Composable
private fun ErrorPanel(message: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer,
        ),
        shape = RoundedCornerShape(8.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top,
            modifier = Modifier.padding(16.dp),
        ) {
            Icon(Icons.Default.Error, contentDescription = null)
            Text(text = message)
        }
    }
}

@Composable
private fun SummaryPanel(summary: JsonSummary, modifier: Modifier = Modifier) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.outlinedCardColors(containerColor = SharedCard, contentColor = SharedText),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(16.dp),
        ) {
            Text(
                text = summary.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = SharedText,
            )
            summary.rows.forEach { row ->
                Text(
                    text = row,
                    style = MaterialTheme.typography.bodyMedium,
                    color = SharedMuted,
                )
            }
        }
    }
}
