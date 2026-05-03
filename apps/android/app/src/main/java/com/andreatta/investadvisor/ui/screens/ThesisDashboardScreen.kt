package com.andreatta.investadvisor.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Error
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.andreatta.investadvisor.R
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.ui.UiState
import java.text.NumberFormat
import java.util.Locale

private val AppBg = Color(0xFF0A0E1A)
private val CardBg = Color(0xFF141C30)
private val CardBg2 = Color(0xFF1A2340)
private val GreenAccent = Color(0xFF00D4AA)
private val GreenStrong = Color(0xFF00FF9D)
private val RedAccent = Color(0xFFFF4D6A)
private val GoldAccent = Color(0xFFF5C842)
private val BlueAccent = Color(0xFF4F8EF7)
private val MutedText = Color(0xFF8A9BC0)
private val DimText = Color(0xFF4A5A7A)
private val CardBorder = Color.White.copy(alpha = 0.07f)

@Composable
fun ThesisDashboardState(
    state: UiState<JsonSummary>,
    modifier: Modifier = Modifier,
    selectedFront: AssetFront? = null,
    onFrontSelected: ((AssetFront) -> Unit)? = null,
) {
    when (state) {
        UiState.Idle -> ThesisInfoPanel("Toque em Atualizar para carregar as teses.", modifier)
        UiState.Loading -> ThesisLoadingPanel(modifier)
        is UiState.Error -> ThesisErrorPanel(state.message, modifier)
        is UiState.Success -> {
            val model = state.data.toThesisDashboardModel()
            if (model == null) {
                SummaryState(state, "Sem dados de teses.", modifier)
            } else {
                ThesisDashboardContent(model, modifier, selectedFront, onFrontSelected)
            }
        }
    }
}

@Composable
fun ThesisFrontHubState(
    state: UiState<JsonSummary>,
    onOpenFront: (AssetFront) -> Unit,
    modifier: Modifier = Modifier,
) {
    when (state) {
        UiState.Idle -> ThesisInfoPanel("Toque em Atualizar para carregar o hub.", modifier)
        UiState.Loading -> ThesisLoadingPanel(modifier)
        is UiState.Error -> ThesisErrorPanel(state.message, modifier)
        is UiState.Success -> {
            val model = state.data.toThesisDashboardModel()
            if (model == null) {
                SummaryState(state, "Sem dados para o hub.", modifier)
            } else {
                ThesisFrontHubContent(model, onOpenFront, modifier)
            }
        }
    }
}

@Composable
fun ThesisListState(
    state: UiState<JsonSummary>,
    modifier: Modifier = Modifier,
) {
    when (state) {
        UiState.Idle -> ThesisInfoPanel("Toque em Atualizar para carregar as teses.", modifier)
        UiState.Loading -> ThesisLoadingPanel(modifier)
        is UiState.Error -> ThesisErrorPanel(state.message, modifier)
        is UiState.Success -> {
            val model = state.data.toThesisDashboardModel()
            if (model == null) {
                SummaryState(state, "Sem dados de teses.", modifier)
            } else {
                ThesisListContent(model, modifier)
            }
        }
    }
}

@Composable
private fun ThesisListContent(
    model: ThesisDashboardModel,
    modifier: Modifier = Modifier,
) {
    var currentFrontName by rememberSaveable { mutableStateOf(AssetFront.Stocks.name) }
    var query by rememberSaveable { mutableStateOf("") }
    var openOnly by rememberSaveable { mutableStateOf(true) }
    val currentFront = runCatching { AssetFront.valueOf(currentFrontName) }.getOrDefault(AssetFront.Stocks)
    val frontOperations = model.operations.filter { it.front == currentFront }
    val visibleOperations = thesisOperationsForTab(frontOperations, query, openOnly)

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(
            text = "Teses",
            style = MaterialTheme.typography.headlineSmall,
            color = Color.White,
            fontWeight = FontWeight.ExtraBold,
        )
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Buscar tese, ação ou motivo") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AssetFront.entries.forEach { front ->
                val accent = front.accentColor()
                FilterChip(
                    selected = currentFront == front,
                    onClick = { currentFrontName = front.name },
                    label = { Text(front.label) },
                    colors = FilterChipDefaults.filterChipColors(
                        containerColor = CardBg,
                        labelColor = MutedText,
                        selectedContainerColor = accent.copy(alpha = 0.18f),
                        selectedLabelColor = accent,
                    ),
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            FilterChip(
                selected = openOnly,
                onClick = { openOnly = true },
                label = { Text("Abertas") },
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = CardBg,
                    labelColor = MutedText,
                    selectedContainerColor = GreenAccent.copy(alpha = 0.18f),
                    selectedLabelColor = GreenAccent,
                ),
            )
            FilterChip(
                selected = !openOnly,
                onClick = { openOnly = false },
                label = { Text("Encerradas") },
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = CardBg,
                    labelColor = MutedText,
                    selectedContainerColor = RedAccent.copy(alpha = 0.16f),
                    selectedLabelColor = RedAccent,
                ),
            )
        }

        Text(
            text = "${visibleOperations.size} ${if (openOnly) "abertas" else "encerradas"} em ${currentFront.label}",
            style = MaterialTheme.typography.bodySmall,
            color = MutedText,
        )

        if (visibleOperations.isEmpty()) {
            ThesisInfoPanel("Nenhuma tese encontrada para o filtro atual.")
        } else {
            visibleOperations.forEach { operation ->
                ThesisListOperationCard(operation)
            }
        }
    }
}

@Composable
private fun ThesisListOperationCard(operation: ThesisOperationCardModel) {
    val sideColor = operation.directionColor()
    OutlinedCard(
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, CardBorder),
        colors = CardDefaults.outlinedCardColors(containerColor = Color.Transparent, contentColor = Color.White),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(modifier = Modifier.background(Brush.linearGradient(listOf(CardBg2, CardBg)))) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(132.dp)
                    .background(sideColor),
            )
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(14.dp),
            ) {
                Row(
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "#${operation.thesisNumber}  ${operation.action}",
                            color = Color.White,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        Text(
                            text = if ((operation.expectedPct ?: 0.0) >= 0.0) "Tese bull" else "Tese bear",
                            color = sideColor,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    Text(
                        text = fmtSignedPct(operation.resultPct),
                        color = resultColor(operation.resultPct),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.ExtraBold,
                    )
                }
                Text(
                    text = operation.thesisReason.ifBlank { operation.operationPlan },
                    color = MutedText,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                OperationProgressBar(
                    progressPct = operationProgressToTarget(operation).progressPct,
                    label = operationProgressToTarget(operation).label,
                    accent = sideColor,
                )
            }
        }
    }
}

@Composable
fun FrontSelectionHomeScreen(
    onOpenFront: (AssetFront) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .fillMaxSize()
            .background(AppBg)
            .padding(22.dp),
    ) {
        Text(
            text = "Grão Invest",
            style = MaterialTheme.typography.headlineMedium,
            color = Color.White,
            fontWeight = FontWeight.ExtraBold,
        )
        Spacer(Modifier.height(24.dp))
        homeFrontChoices().forEach { choice ->
            FrontHubCard(choice.toFallbackCard(), onClick = { onOpenFront(choice.front) })
            Spacer(Modifier.height(14.dp))
        }
    }
}

private fun HomeFrontChoiceModel.toFallbackCard(): InvestmentFrontCardModel = InvestmentFrontCardModel(
    front = front,
    title = title,
    subtitle = front.subtitle,
    iconLabel = front.iconLabel,
    statusLabel = "abrir",
    primaryLabel = "Teses",
    primaryValue = "-",
    secondaryLabel = "Acerto",
    secondaryValue = "-",
    highlightLabel = "Abertas",
    highlightValue = "-",
    actionLabel = front.actionLabel,
    hasAlert = false,
)

@Composable
fun ThesisLearningState(
    state: UiState<JsonSummary>,
    modifier: Modifier = Modifier,
) {
    when (state) {
        UiState.Idle -> ThesisInfoPanel("Toque em Atualizar para carregar aprendizados.", modifier)
        UiState.Loading -> ThesisLoadingPanel(modifier)
        is UiState.Error -> ThesisErrorPanel(state.message, modifier)
        is UiState.Success -> {
            val model = state.data.toThesisDashboardModel()
            val lessons = model
                ?.operations
                .orEmpty()
                .filter { it.learningNote.isNotBlank() || it.thesisReason.isNotBlank() }
                .distinctBy { it.learningNote.ifBlank { it.thesisReason } }
                .take(8)

            if (lessons.isEmpty()) {
                ThesisInfoPanel("Ainda não há aprendizados consolidados para mostrar.")
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = modifier.fillMaxWidth()) {
                    lessons.forEach { operation ->
                        LearningCard(operation)
                    }
                }
            }
        }
    }
}

@Composable
private fun ThesisFrontHubContent(
    model: ThesisDashboardModel,
    onOpenFront: (AssetFront) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(
            text = "Grão Invest",
            style = MaterialTheme.typography.headlineMedium,
            color = Color.White,
            fontWeight = FontWeight.ExtraBold,
        )
        model.frontCards().forEach { card ->
            FrontHubCard(card, onClick = { onOpenFront(card.front) })
        }
    }
}

@Composable
private fun ThesisDashboardContent(
    model: ThesisDashboardModel,
    modifier: Modifier = Modifier,
    selectedFront: AssetFront? = null,
    onFrontSelected: ((AssetFront) -> Unit)? = null,
) {
    var internalFrontName by rememberSaveable { mutableStateOf(selectedFront?.name ?: AssetFront.Stocks.name) }
    val currentFront = selectedFront ?: runCatching { AssetFront.valueOf(internalFrontName) }.getOrDefault(AssetFront.Stocks)
    val snapshot = model.snapshot(currentFront)

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AssetFront.entries.forEach { front ->
                val accent = front.accentColor()
                FilterChip(
                    selected = currentFront == front,
                    onClick = {
                        internalFrontName = front.name
                        onFrontSelected?.invoke(front)
                    },
                    label = { Text(front.label) },
                    colors = FilterChipDefaults.filterChipColors(
                        containerColor = CardBg,
                        labelColor = MutedText,
                        selectedContainerColor = accent.copy(alpha = 0.18f),
                        selectedLabelColor = accent,
                    ),
                )
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            ThesisKpiCard(
                label = "Teses testadas",
                value = fmtInt(snapshot.overview.totalTested),
                sub = snapshot.front.label,
                accent = snapshot.front.accentColor(),
                modifier = Modifier.weight(1f),
            )
            ThesisKpiCard(
                label = "Sucesso",
                value = fmtPct(snapshot.overview.successRatePct),
                sub = "${fmtInt(snapshot.overview.successCount)} aprovadas",
                accent = Color(0xFF22C55E),
                modifier = Modifier.weight(1f),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            ThesisKpiCard(
                label = "Ganho medio",
                value = fmtSignedPct(snapshot.overview.avgResultPct),
                sub = "por tese resolvida",
                accent = resultColor(snapshot.overview.avgResultPct),
                modifier = Modifier.weight(1f),
            )
            ThesisKpiCard(
                label = "Abertas",
                value = fmtInt(snapshot.overview.openCount),
                sub = "em acompanhamento",
                accent = Color(0xFFF59E0B),
                modifier = Modifier.weight(1f),
            )
        }

        Text(
            text = "Operações em monitoramento - ${snapshot.front.label}",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
            modifier = Modifier.padding(top = 4.dp),
        )

        if (snapshot.activeOperations.isEmpty()) {
            ThesisInfoPanel("Nenhuma tese em monitoramento para ${snapshot.front.label} no momento.")
        } else {
            snapshot.activeOperations.forEach { operation ->
                ActiveOperationCard(operation)
            }
        }
    }
}

@Composable
private fun FrontHubCard(
    card: InvestmentFrontCardModel,
    onClick: () -> Unit,
) {
    val accent = card.front.accentColor()
    OutlinedCard(
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, accent.copy(alpha = 0.26f)),
        colors = CardDefaults.outlinedCardColors(containerColor = Color.Transparent, contentColor = Color.White),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(14.dp),
            modifier = Modifier
                .background(
                    Brush.linearGradient(
                        listOf(accent.copy(alpha = 0.22f), CardBg2, CardBg),
                    ),
                )
                .padding(18.dp),
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(74.dp)
                        .clip(RoundedCornerShape(22.dp))
                        .border(1.dp, accent.copy(alpha = 0.30f), RoundedCornerShape(22.dp))
                        .background(accent.copy(alpha = 0.12f)),
                ) {
                    Image(
                        painter = painterResource(card.front.iconResId()),
                        contentDescription = "Abrir ${card.title}",
                        modifier = Modifier
                            .size(58.dp)
                            .clip(RoundedCornerShape(18.dp)),
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = card.title,
                        style = MaterialTheme.typography.headlineSmall,
                        color = Color.White,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        text = "Toque para abrir",
                        style = MaterialTheme.typography.bodySmall,
                        color = MutedText,
                    )
                }
                StatusPill(card.statusLabel, accent, card.hasAlert)
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                FrontMetric(card.primaryLabel, card.primaryValue, accent, Modifier.weight(1f))
                FrontMetric(card.secondaryLabel, card.secondaryValue, accent, Modifier.weight(1f))
                FrontMetric(card.highlightLabel, card.highlightValue, accent, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun FrontMetric(label: String, value: String, accent: Color, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .border(1.dp, CardBorder, RoundedCornerShape(12.dp))
            .background(Color.White.copy(alpha = 0.04f))
            .padding(horizontal = 10.dp, vertical = 9.dp),
    ) {
        Text(
            text = label.uppercase(brLocale),
            style = MaterialTheme.typography.labelSmall,
            color = DimText,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = accent,
            fontWeight = FontWeight.ExtraBold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun StatusPill(label: String, accent: Color, alert: Boolean) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(100.dp))
            .background(if (alert) Color(0x33F59E0B) else accent.copy(alpha = 0.16f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
    ) {
        Text(
            text = label.uppercase(brLocale),
            style = MaterialTheme.typography.labelSmall,
            color = if (alert) Color(0xFFF59E0B) else accent,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
    }
}

@Composable
private fun LearningCard(operation: ThesisOperationCardModel) {
    OutlinedCard(shape = RoundedCornerShape(12.dp), modifier = Modifier.fillMaxWidth()) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(14.dp)) {
            Text(
                text = "#${operation.thesisNumber}  ${operation.action}",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            DetailBlock("Dor", operation.thesisReason.ifBlank { "Motivo da tese não informado." })
            DetailBlock("Remédio", operation.learningNote.ifBlank { "Aprendizado ainda em consolidação." })
        }
    }
}

@Composable
private fun ThesisKpiCard(
    label: String,
    value: String,
    sub: String,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    OutlinedCard(
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, CardBorder),
        colors = CardDefaults.outlinedCardColors(containerColor = CardBg, contentColor = Color.White),
        modifier = modifier,
    ) {
        Column {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .background(accent),
            )
            Column(
                verticalArrangement = Arrangement.spacedBy(5.dp),
                modifier = Modifier.padding(12.dp),
            ) {
                Text(
                    text = label.uppercase(brLocale),
                    style = MaterialTheme.typography.labelSmall,
                    color = MutedText,
                    maxLines = 1,
                )
                Text(
                    text = value,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.ExtraBold,
                    color = accent,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = sub,
                    style = MaterialTheme.typography.bodySmall,
                    color = DimText,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun PeriodCard(summary: ThesisPeriodSummary, modifier: Modifier = Modifier) {
    OutlinedCard(shape = RoundedCornerShape(8.dp), modifier = modifier) {
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.padding(12.dp),
        ) {
            Text(
                text = summary.title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            MiniMetric("Teses", fmtInt(summary.thesisCount))
            MiniMetric("Esperado", fmtSignedPct(summary.expectedPct))
            MiniMetric("Alcancado", fmtSignedPct(summary.achievedPct))
            MiniMetric("Aprovadas", fmtInt(summary.approvedCount))
        }
    }
}

@Composable
private fun MiniMetric(label: String, value: String) {
    Row(
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun ActiveOperationCard(operation: ThesisOperationCardModel) {
    var expanded by rememberSaveable(operation.thesisNumber) { mutableStateOf(false) }
    val sideColor = operation.directionColor()
    val progress = operationProgressToTarget(operation)
    OutlinedCard(
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, CardBorder),
        colors = CardDefaults.outlinedCardColors(containerColor = Color.Transparent, contentColor = Color.White),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { expanded = !expanded },
    ) {
        Row(
            modifier = Modifier.background(Brush.linearGradient(listOf(CardBg2, CardBg))),
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(if (expanded) 280.dp else 210.dp)
                    .background(sideColor),
            )
            Column(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.padding(14.dp),
            ) {
                Row(
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "#${operation.thesisNumber}  ${operation.action}",
                            style = MaterialTheme.typography.titleMedium,
                            color = Color.White,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            StatusDot(operation.statusColor())
                            Text(
                                text = operation.status,
                                style = MaterialTheme.typography.bodySmall,
                                color = operation.statusColor(),
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                        Text(
                            text = fmtOpenDays(operation.openDays),
                            style = MaterialTheme.typography.bodySmall,
                            color = MutedText,
                        )
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = fmtSignedPct(operation.resultPct),
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.ExtraBold,
                            color = resultColor(operation.resultPct),
                        )
                        Text("vs entrada", style = MaterialTheme.typography.labelSmall, color = DimText)
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    CompactMetric("Entrada", fmtMoney(operation.entryPrice), Modifier.weight(1f))
                    CompactMetric("Atual", fmtMoney(operation.currentPrice), Modifier.weight(1f))
                    CompactMetric("Dias", operation.openDays?.toString() ?: "-", Modifier.weight(1f))
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    CompactMetric("Esperado", fmtSignedPct(operation.expectedPct), Modifier.weight(1f))
                    CompactMetric("% atual", fmtSignedPct(operation.resultPct), Modifier.weight(1f))
                    CompactMetric("Valida ate", operation.plannedExitAt.ifBlank { "-" }, Modifier.weight(1f))
                }

                OperationProgressBar(progress.progressPct, progress.label, sideColor)

                Text(
                    text = operation.operationPlan.ifBlank { "Plano operacional nao informado." },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MutedText,
                    maxLines = if (expanded) Int.MAX_VALUE else 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    OperationStrategyBadge(operation.structuredOperation.ifBlank { "Estratégia em definição" }, operation.front.accentColor())
                    Text(
                        text = if (operation.expectedPct ?: 0.0 >= 0.0) "Bull" else "Bear",
                        style = MaterialTheme.typography.labelSmall,
                        color = sideColor,
                        fontWeight = FontWeight.Bold,
                    )
                }

                if (expanded) {
                    DetailBlock("Sai se", operation.exitRule)
                    DetailBlock("Motivo", operation.thesisReason)
                    DetailBlock("Aprendizado", operation.learningNote)
                }
            }
        }
    }
}

@Composable
private fun OperationProgressBar(progressPct: Int, label: String, accent: Color) {
    val animatedProgress by animateFloatAsState(
        targetValue = progressPct.coerceIn(0, 100) / 100f,
        animationSpec = tween(700),
        label = "operationProgress",
    )
    Row(
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        LinearProgressIndicator(
            progress = { animatedProgress },
            color = accent,
            trackColor = Color.White.copy(alpha = 0.08f),
            modifier = Modifier
                .weight(1f)
                .height(5.dp),
        )
        Text(label, color = DimText, style = MaterialTheme.typography.labelSmall, maxLines = 1)
    }
}

@Composable
private fun OperationStrategyBadge(label: String, accent: Color) {
    Text(
        text = label,
        color = accent,
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .border(1.dp, accent.copy(alpha = 0.22f), RoundedCornerShape(8.dp))
            .background(accent.copy(alpha = 0.08f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
    )
}

@Composable
private fun StatusDot(color: Color) {
    Box(
        modifier = Modifier
            .size(7.dp)
            .clip(RoundedCornerShape(99.dp))
            .background(color),
    )
}

@Composable
private fun CompactMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = modifier,
    ) {
        Column(modifier = Modifier.padding(8.dp)) {
            Text(
                text = label.uppercase(),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun DetailBlock(label: String, value: String) {
    if (value.isBlank()) return
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(
            text = label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ThesisLoadingPanel(modifier: Modifier = Modifier) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, CardBorder),
        colors = CardDefaults.outlinedCardColors(containerColor = CardBg, contentColor = Color.White),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.padding(16.dp),
        ) {
            CircularProgressIndicator(color = GreenAccent)
            Text("Carregando teses...", color = Color.White)
        }
    }
}

@Composable
private fun ThesisInfoPanel(text: String, modifier: Modifier = Modifier) {
    OutlinedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, CardBorder),
        colors = CardDefaults.outlinedCardColors(containerColor = CardBg, contentColor = Color.White),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = MutedText,
            modifier = Modifier.padding(16.dp),
        )
    }
}

@Composable
private fun ThesisErrorPanel(message: String, modifier: Modifier = Modifier) {
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
            androidx.compose.material3.Icon(Icons.Default.Error, contentDescription = null)
            Text(text = message)
        }
    }
}

private val brLocale = Locale("pt", "BR")
private val integerFormat: NumberFormat = NumberFormat.getIntegerInstance(brLocale)
private val moneyFormat: NumberFormat = NumberFormat.getCurrencyInstance(brLocale)

private fun fmtInt(value: Int): String = integerFormat.format(value)

private fun fmtPct(value: Double?): String = value?.let {
    String.format(brLocale, "%.2f%%", it)
} ?: "-"

private fun fmtSignedPct(value: Double?): String = value?.let {
    String.format(brLocale, "%+.2f%%", it)
} ?: "-"

private fun fmtMoney(value: Double?): String = value?.let {
    moneyFormat.format(it)
} ?: "-"

private fun fmtOpenDays(value: Int?): String = when (value) {
    null -> "Tempo em aberto não informado"
    0 -> "Aberta hoje"
    1 -> "Aberta há 1 dia"
    else -> "Aberta há $value dias"
}

private fun ThesisOperationCardModel.directionColor(): Color =
    if ((expectedPct ?: 0.0) < 0.0) RedAccent else GreenAccent

private fun ThesisOperationCardModel.statusColor(): Color = when {
    !isOpen -> MutedText
    status.contains("aten", ignoreCase = true) ||
        status.contains("atenç", ignoreCase = true) -> GoldAccent
    (resultPct ?: 0.0) < 0.0 -> GoldAccent
    else -> BlueAccent
}
@Composable
private fun resultColor(value: Double?): Color = when {
    value == null -> MaterialTheme.colorScheme.onSurface
    value >= 0.0 -> Color(0xFF22C55E)
    else -> Color(0xFFFF5E5E)
}

private fun AssetFront.iconResId(): Int = when (this) {
    AssetFront.Stocks -> R.drawable.front_b3
    AssetFront.Crypto -> R.drawable.front_crypto
    AssetFront.RealEstate -> R.drawable.front_real_estate
}

@Composable
private fun AssetFront.accentColor(): Color = when (this) {
    AssetFront.Stocks -> Color(0xFF00C896)
    AssetFront.Crypto -> Color(0xFF3B9EFF)
    AssetFront.RealEstate -> Color(0xFFC8A444)
}
