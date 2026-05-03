package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.network.RealEstateCandidate
import com.andreatta.investadvisor.network.RealEstatePendingItem
import com.andreatta.investadvisor.ui.viewmodel.RealEstateRadarUiState
import com.andreatta.investadvisor.ui.viewmodel.RealEstateRadarViewModel
import com.andreatta.investadvisor.ui.viewmodel.simpleViewModelFactory

enum class RealEstateScoreTone {
    Strong,
    Watch,
    Risk,
}

data class RealEstateScorePresentation(
    val score: Int,
    val scoreText: String,
    val label: String,
    val tone: RealEstateScoreTone,
)

enum class RealEstateCandidateSection(val title: String) {
    Diligence("Para diligencia"),
    Negotiate("Negociar ou monitorar"),
    Discarded("Descartados"),
}

fun realEstateScorePresentation(score: Int): RealEstateScorePresentation {
    val normalizedScore = score.coerceIn(0, 100)
    val tone = when {
        normalizedScore >= 75 -> RealEstateScoreTone.Strong
        normalizedScore >= 50 -> RealEstateScoreTone.Watch
        else -> RealEstateScoreTone.Risk
    }
    val label = when (tone) {
        RealEstateScoreTone.Strong -> "Forte"
        RealEstateScoreTone.Watch -> "Atencao"
        RealEstateScoreTone.Risk -> "Risco"
    }

    return RealEstateScorePresentation(
        score = normalizedScore,
        scoreText = normalizedScore.toString(),
        label = label,
        tone = tone,
    )
}

fun realEstateCandidateSection(status: String?): RealEstateCandidateSection {
    val normalized = status.orEmpty().lowercase()
    return when {
        normalized.contains("descart") -> RealEstateCandidateSection.Discarded
        normalized.contains("pend") || normalized.contains("dilig") ||
            normalized.contains("forte") -> RealEstateCandidateSection.Diligence
        else -> RealEstateCandidateSection.Negotiate
    }
}

@Composable
fun RealEstateRadarScreen(
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<RealEstateRadarViewModel>(
        key = "real-estate-radar",
        factory = simpleViewModelFactory { RealEstateRadarViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionHeader(
            title = "ImÃ³veis e Projetos",
            subtitle = "Radar para leilÃ£o, venda direta, retrofit e house flipping.",
        )
        DisclaimerBar()
        RadarSummary(state)
        RefreshButton("Atualizar radar", onClick = viewModel::refresh)
        RadarState(
            state = state,
            onConfirmVacancy = { id ->
                viewModel.confirmDueDiligence(id, occupancyStatus = "desocupado")
            },
            onConfirmDocuments = { id ->
                viewModel.confirmDueDiligence(id, hasRegistration = true, hasDebtCheck = true)
            },
        )
    }
}

@Composable
private fun RadarSummary(state: RealEstateRadarUiState) {
    OutlinedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(12.dp),
        ) {
            SummaryMetric(
                label = "Oportunidades",
                value = state.summary.total.takeIf { it > 0 }?.toString()
                    ?: state.candidates.size.toString(),
                modifier = Modifier.weight(1f),
            )
            SummaryMetric(
                label = "Score mÃ©dio",
                value = averageScore(state.candidates),
                modifier = Modifier.weight(1f),
            )
            SummaryMetric(
                label = "Pendencias",
                value = state.candidates.sumOf { it.analysis.pendingItems.size }.toString(),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun SummaryMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun RadarState(
    state: RealEstateRadarUiState,
    onConfirmVacancy: (Int) -> Unit,
    onConfirmDocuments: (Int) -> Unit,
) {
    when {
        state.isLoading && state.candidates.isEmpty() -> {
            OutlinedCard(modifier = Modifier.fillMaxWidth()) {
                Text("Carregando radar imobiliÃ¡rio...", modifier = Modifier.padding(16.dp))
            }
        }
        state.errorMessage != null -> {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer,
                    contentColor = MaterialTheme.colorScheme.onErrorContainer,
                ),
            ) {
                Text(state.errorMessage, modifier = Modifier.padding(16.dp))
            }
        }
        state.candidates.isEmpty() -> {
            OutlinedCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Nenhuma oportunidade imobiliÃ¡ria encontrada no radar neste momento.",
                    modifier = Modifier.padding(16.dp),
                )
            }
        }
        else -> {
            state.actionMessage?.let { message ->
                AssistChip(onClick = {}, label = { Text(message) })
            }
            RealEstateCandidateSection.entries.forEach { section ->
                val sectionCandidates = state.candidates.filter {
                    realEstateCandidateSection(it.status) == section
                }
                if (sectionCandidates.isNotEmpty()) {
                    Text(
                        text = section.title,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    sectionCandidates.forEach { candidate ->
                        CandidateCard(
                            candidate = candidate,
                            onConfirmVacancy = { onConfirmVacancy(candidate.id) },
                            onConfirmDocuments = { onConfirmDocuments(candidate.id) },
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CandidateCard(
    candidate: RealEstateCandidate,
    onConfirmVacancy: () -> Unit,
    onConfirmDocuments: () -> Unit,
) {
    val uriHandler = LocalUriHandler.current
    OutlinedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(14.dp),
        ) {
            Text(
                text = candidate.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                candidate.origin?.takeIf { it.isNotBlank() }?.let { SmallTag(it) }
                candidate.strategy?.takeIf { it.isNotBlank() }?.let { SmallTag(it) }
                candidate.status?.takeIf { it.isNotBlank() }?.let { SmallTag(it) }
            }
            ScoreBlock(candidate)
            CandidateMoneyBlock(candidate)
            candidate.analysis.nextAction?.takeIf { it.isNotBlank() }?.let { action ->
                Text(
                    text = "PrÃ³xima aÃ§Ã£o: $action",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold,
                )
            }
            PendingItems(candidate.analysis.pendingItems)
            if (candidate.sourceUrl.isNotBlank()) {
                OutlinedButton(
                    onClick = { uriHandler.openUri(candidate.sourceUrl) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Abrir anÃºncio")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(onClick = onConfirmVacancy, modifier = Modifier.weight(1f)) {
                    Text("Desocupado")
                }
                ElevatedButton(onClick = onConfirmDocuments, modifier = Modifier.weight(1f)) {
                    Text("Docs OK")
                }
            }
        }
    }
}

@Composable
private fun ScoreBlock(candidate: RealEstateCandidate) {
    val score = realEstateScorePresentation(candidate.analysis.score)
    val confidence = candidate.analysis.confidence.coerceIn(0, 100)
    val scoreColor = score.tone.toneColor()
    OutlinedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, scoreColor.copy(alpha = 0.48f)),
        colors = CardDefaults.outlinedCardColors(
            containerColor = scoreColor.copy(alpha = 0.09f),
        ),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.padding(12.dp),
        ) {
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column {
                    Text(
                        text = "Score",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = score.scoreText,
                        style = MaterialTheme.typography.displaySmall,
                        color = scoreColor,
                        fontWeight = FontWeight.ExtraBold,
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = score.label,
                        style = MaterialTheme.typography.titleSmall,
                        color = scoreColor,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "ConfianÃ§a $confidence%",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            LinearProgressIndicator(
                progress = { score.score / 100f },
                color = scoreColor,
                trackColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.40f),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(7.dp),
            )
        }
    }
}

@Composable
private fun CandidateMoneyBlock(candidate: RealEstateCandidate) {
    val base = candidate.analysis.scenarios.base
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "AnÃ¡lise financeira",
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.SemiBold,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            FinancialMetricTile("PreÃ§o pedido", candidate.askingPrice?.let { money(it) } ?: "-", Modifier.weight(1f))
            FinancialMetricTile("Caixa estimado", candidate.analysis.cashNeeded?.let { money(it) } ?: "-", Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            FinancialMetricTile("Venda base", base?.salePrice?.let { money(it) } ?: "-", Modifier.weight(1f))
            FinancialMetricTile(
                label = "ROI base",
                value = base?.roiPct?.let { "%.1f%%".format(it) } ?: "-",
                modifier = Modifier.weight(1f),
                valueColor = realEstateResultColor(base?.roiPct),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            FinancialMetricTile(
                label = "Preco teto",
                value = candidate.analysis.maxPurchasePrice?.let { money(it) } ?: "-",
                modifier = Modifier.weight(1f),
                valueColor = ceilingStatusColor(candidate.analysis.priceGapToCeiling),
            )
            FinancialMetricTile(
                label = "Dif. teto",
                value = candidate.analysis.priceGapToCeiling?.let { money(it) } ?: "-",
                modifier = Modifier.weight(1f),
                valueColor = ceilingStatusColor(candidate.analysis.priceGapToCeiling),
            )
        }
        candidate.analysis.priceCeilingStatus?.takeIf { it.isNotBlank() }?.let { status ->
            Text(
                text = "Teto: $status com ROI alvo de ${
                    candidate.analysis.targetRoiPct?.let { "%.0f%%".format(it) } ?: "20%"
                }",
                style = MaterialTheme.typography.bodySmall,
                color = ceilingStatusColor(candidate.analysis.priceGapToCeiling),
                fontWeight = FontWeight.SemiBold,
            )
        }
        base?.netProfit?.let { profit ->
            Text(
                text = "Lucro lÃ­quido estimado: ${money(profit)}",
                style = MaterialTheme.typography.bodySmall,
                color = realEstateResultColor(profit),
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}

@Composable
private fun FinancialMetricTile(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    valueColor: Color = MaterialTheme.colorScheme.onSurface,
) {
    Card(
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.72f)),
        modifier = modifier,
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Text(
                text = label.uppercase(),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodyMedium,
                color = valueColor,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun PendingItems(items: List<RealEstatePendingItem>) {
    if (items.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            text = "PendÃªncias",
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.SemiBold,
        )
        items.take(4).forEach { item ->
            PendingItemRow(item)
        }
    }
}

@Composable
private fun PendingItemRow(item: RealEstatePendingItem) {
    val color = pendingStatusColor(item)
    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(color.copy(alpha = 0.10f))
            .padding(horizontal = 10.dp, vertical = 8.dp),
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(RoundedCornerShape(99.dp))
                .background(color),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = item.title,
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = "${item.priority} Â· ${item.status}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun SmallTag(text: String) {
    AssistChip(onClick = {}, label = { Text(text) })
}

private fun averageScore(candidates: List<RealEstateCandidate>): String {
    if (candidates.isEmpty()) return "-"
    return candidates.map { it.analysis.score }.average().toInt().toString()
}

private fun money(value: Double): String = "R$ ${"%,.0f".format(value)}"

private fun realEstateResultColor(value: Double?): Color = when {
    value == null -> Color.Unspecified
    value >= 0.0 -> Color(0xFF00D4AA)
    else -> Color(0xFFFF4D6A)
}

private fun pendingStatusColor(item: RealEstatePendingItem): Color {
    val status = item.status.lowercase()
    val priority = item.priority.lowercase()
    return when {
        status.contains("ok") || status.contains("conclu") -> Color(0xFF00D4AA)
        priority == "p0" || status.contains("aberta") -> Color(0xFFFF4D6A)
        else -> Color(0xFFF5C842)
    }
}

private fun ceilingStatusColor(gapToCeiling: Double?): Color = when {
    gapToCeiling == null -> Color.Unspecified
    gapToCeiling <= 0.0 -> Color(0xFF00D4AA)
    else -> Color(0xFFFF4D6A)
}

private fun RealEstateScoreTone.toneColor(): Color = when (this) {
    RealEstateScoreTone.Strong -> Color(0xFF00D4AA)
    RealEstateScoreTone.Watch -> Color(0xFFF5C842)
    RealEstateScoreTone.Risk -> Color(0xFFFF4D6A)
}
