package com.andreatta.investadvisor.ui.screens

import com.andreatta.investadvisor.network.JsonSummary
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.nio.charset.Charset
import java.time.LocalDate
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToInt

data class ThesisDashboardModel(
    val generatedAt: String,
    val kickoffDate: String,
    val overview: ThesisOverview,
    val historical: ThesisPeriodSummary,
    val current: ThesisPeriodSummary,
    val operations: List<ThesisOperationCardModel>,
    val activeOperations: List<ThesisOperationCardModel>,
)

data class ThesisOverview(
    val totalTested: Int,
    val successCount: Int,
    val successRatePct: Double?,
    val avgResultPct: Double?,
    val openCount: Int,
)

data class ThesisPeriodSummary(
    val title: String,
    val thesisCount: Int,
    val expectedPct: Double?,
    val achievedPct: Double?,
    val approvedCount: Int,
)

data class ThesisOperationCardModel(
    val thesisNumber: Int,
    val action: String,
    val phase: String,
    val front: AssetFront,
    val status: String,
    val outcome: String,
    val expectedPct: Double?,
    val resultPct: Double?,
    val entryPrice: Double?,
    val currentPrice: Double?,
    val openDays: Int?,
    val raisedAt: String,
    val latestAt: String,
    val plannedExitAt: String,
    val isOpen: Boolean,
    val operationPlan: String,
    val structuredOperation: String,
    val exitRule: String,
    val thesisReason: String,
    val learningNote: String,
)

data class OperationProgressPresentation(
    val progressPct: Int,
    val label: String,
)

enum class AssetFront(
    val label: String,
    val iconLabel: String,
    val subtitle: String,
    val actionLabel: String,
) {
    Stocks(
        label = "Ações B3",
        iconLabel = "B3",
        subtitle = "Teses com ações brasileiras, preço diário, alvo, stop e acompanhamento de risco.",
        actionLabel = "Ver operações abertas, histórico e aprendizados de Bolsa",
    ),
    Crypto(
        label = "Cripto",
        iconLabel = "₿",
        subtitle = "Ativos digitais separados da Bolsa, com volatilidade maior e leitura 24/7.",
        actionLabel = "Abrir radar de cripto, critérios e próximas teses",
    ),
    RealEstate(
        label = "Imóveis",
        iconLabel = "IM",
        subtitle = "Teses patrimoniais: região, preço justo, liquidez, aluguel, reforma e prazo mais longo.",
        actionLabel = "Avaliar oportunidades imobiliárias e premissas de valor justo",
    ),
}

data class InvestmentFrontCardModel(
    val front: AssetFront,
    val title: String,
    val subtitle: String,
    val iconLabel: String,
    val statusLabel: String,
    val primaryLabel: String,
    val primaryValue: String,
    val secondaryLabel: String,
    val secondaryValue: String,
    val highlightLabel: String,
    val highlightValue: String,
    val actionLabel: String,
    val hasAlert: Boolean,
)

data class ThesisFrontSnapshot(
    val front: AssetFront,
    val overview: ThesisOverview,
    val historical: ThesisPeriodSummary,
    val current: ThesisPeriodSummary,
    val activeOperations: List<ThesisOperationCardModel>,
)

data class HomeFrontChoiceModel(
    val front: AssetFront,
    val title: String,
)

fun homeFrontChoices(): List<HomeFrontChoiceModel> = listOf(
    HomeFrontChoiceModel(AssetFront.Stocks, "B3"),
    HomeFrontChoiceModel(AssetFront.Crypto, "Cripto"),
    HomeFrontChoiceModel(AssetFront.RealEstate, "Imóveis"),
)

fun operationProgressToTarget(operation: ThesisOperationCardModel): OperationProgressPresentation {
    val expected = operation.expectedPct ?: return OperationProgressPresentation(0, "0% da meta")
    val result = operation.resultPct ?: return OperationProgressPresentation(0, "0% da meta")
    val target = abs(expected)
    if (target <= 0.0) return OperationProgressPresentation(0, "0% da meta")

    val favorableResult = if (expected >= 0.0) {
        result.coerceAtLeast(0.0)
    } else {
        (-result).coerceAtLeast(0.0)
    }
    val progress = ((favorableResult / target) * 100.0)
        .roundToInt()
        .coerceIn(0, 100)

    return OperationProgressPresentation(progress, "$progress% da meta")
}

fun thesisOperationsForTab(
    operations: List<ThesisOperationCardModel>,
    query: String,
    openOnly: Boolean,
): List<ThesisOperationCardModel> {
    val normalizedQuery = query.trim().lowercase()
    return operations
        .asSequence()
        .filter { it.isOpen == openOnly }
        .filter { operation ->
            normalizedQuery.isBlank() ||
                operation.thesisNumber.toString().contains(normalizedQuery) ||
                operation.action.lowercase().contains(normalizedQuery) ||
                operation.status.lowercase().contains(normalizedQuery) ||
                operation.thesisReason.lowercase().contains(normalizedQuery) ||
                operation.operationPlan.lowercase().contains(normalizedQuery)
        }
        .sortedByDescending { it.thesisNumber }
        .toList()
}
fun JsonSummary.toThesisDashboardModel(): ThesisDashboardModel? {
    val root = raw as? JsonObject ?: return null
    val executive = root.objectOrNull("thesis_executive_summary")
    val overview = root.objectOrNull("thesis_history_overview")
    val operations = root.arrayOrNull("thesis_open_operations").orEmpty()

    val parsedOperations = operations
        .mapNotNull { (it as? JsonObject)?.toThesisOperationCardModel() }
        .sortedByDescending { it.thesisNumber }
    val activeOperations = parsedOperations
        .filter { it.isOpen }

    return ThesisDashboardModel(
        generatedAt = root.stringOrNull("generated_at").orEmpty(),
        kickoffDate = root.stringOrNull("phase_kickoff_date").ifBlank { "2026-04-27" },
        overview = ThesisOverview(
            totalTested = overview?.intOrNull("total_tested") ?: 0,
            successCount = overview?.intOrNull("success_count") ?: 0,
            successRatePct = overview?.doubleOrNull("success_rate_pct"),
            avgResultPct = overview?.doubleOrNull("avg_result_pct"),
            openCount = activeOperations.size,
        ),
        historical = executive
            ?.objectOrNull("historical")
            ?.toPeriodSummary("Histórico")
            ?: ThesisPeriodSummary("Histórico", 0, null, null, 0),
        current = executive
            ?.objectOrNull("current")
            ?.toPeriodSummary("Pós go-live")
            ?: ThesisPeriodSummary("Pós go-live", 0, null, null, 0),
        operations = parsedOperations,
        activeOperations = activeOperations.take(8),
    )
}

fun ThesisDashboardModel.frontCards(): List<InvestmentFrontCardModel> =
    AssetFront.entries.map { front ->
        val snapshot = snapshot(front)
        val hasAlert = snapshot.activeOperations.any { operation ->
            operation.status.contains("atenção", ignoreCase = true) ||
                (operation.resultPct ?: 0.0) < 0.0
        }
        val statusLabel = when {
            front == AssetFront.RealEstate && snapshot.overview.totalTested == 0 -> "novo"
            snapshot.overview.openCount > 0 -> "${snapshot.overview.openCount} abertas"
            snapshot.overview.totalTested > 0 -> "em estudo"
            else -> "preparar"
        }

        InvestmentFrontCardModel(
            front = front,
            title = front.label,
            subtitle = front.subtitle,
            iconLabel = front.iconLabel,
            statusLabel = statusLabel,
            primaryLabel = "Teses",
            primaryValue = snapshot.overview.totalTested.toString(),
            secondaryLabel = "Acerto",
            secondaryValue = snapshot.overview.successRatePct?.let { String.format(ptBrLocale, "%.1f%%", it) } ?: "-",
            highlightLabel = "Abertas",
            highlightValue = snapshot.overview.openCount.toString(),
            actionLabel = front.actionLabel,
            hasAlert = hasAlert,
        )
    }

fun ThesisDashboardModel.snapshot(front: AssetFront): ThesisFrontSnapshot {
    val scopedOperations = operations.filter { it.front == front }
    val active = scopedOperations
        .filter { it.isOpen }
        .sortedByDescending { it.thesisNumber }
        .take(8)

    return ThesisFrontSnapshot(
        front = front,
        overview = scopedOperations.toOverview(),
        historical = scopedOperations
            .filter { it.phase.equals("historico", ignoreCase = true) }
            .toPeriodSummary("Histórico"),
        current = scopedOperations
            .filter { !it.phase.equals("historico", ignoreCase = true) }
            .toPeriodSummary("Pós go-live"),
        activeOperations = active,
    )
}

private val ptBrLocale = Locale("pt", "BR")

private fun List<ThesisOperationCardModel>.toOverview(): ThesisOverview {
    val resolved = filter { it.resultPct != null }
    val successCount = count { it.isSuccessful() }
    val avgResult = resolved.mapNotNull { it.resultPct }.takeIf { it.isNotEmpty() }?.average()
    return ThesisOverview(
        totalTested = size,
        successCount = successCount,
        successRatePct = if (isNotEmpty()) (successCount.toDouble() / size.toDouble()) * 100.0 else 0.0,
        avgResultPct = avgResult,
        openCount = count { it.isOpen },
    )
}

private fun List<ThesisOperationCardModel>.toPeriodSummary(title: String): ThesisPeriodSummary {
    val expectedValues = mapNotNull { it.expectedPct }
    val achievedValues = mapNotNull { it.resultPct }
    return ThesisPeriodSummary(
        title = title,
        thesisCount = size,
        expectedPct = expectedValues.takeIf { it.isNotEmpty() }?.average(),
        achievedPct = achievedValues.takeIf { it.isNotEmpty() }?.average(),
        approvedCount = count { it.isSuccessful() },
    )
}

private fun ThesisOperationCardModel.isSuccessful(): Boolean {
    return outcome.contains("Alvo", ignoreCase = true) ||
        (status.equals("Fechada", ignoreCase = true) && (resultPct ?: -1.0) >= 0.0)
}

private fun JsonObject.toPeriodSummary(title: String): ThesisPeriodSummary = ThesisPeriodSummary(
    title = title,
    thesisCount = intOrNull("thesis_count") ?: 0,
    expectedPct = doubleOrNull("expected_pct"),
    achievedPct = doubleOrNull("achieved_pct"),
    approvedCount = intOrNull("approved_count") ?: 0,
)

private fun JsonObject.toThesisOperationCardModel(): ThesisOperationCardModel {
    val action = stringOrNull("action").ifBlank { "n/d" }
    val phase = stringOrNull("phase")
    val front = stringOrNull("front").toAssetFrontOrNull() ?: action.toAssetFront()
    val status = stringOrNull("status").ifBlank { "Aberta" }.repairMojibake()
    val raisedAt = stringOrNull("thesis_raised_at").take(10)
    val latestAt = stringOrNull("latest_price_at").take(10)
    val plannedExitAt = stringOrNull("planned_exit_at")
        .take(10)
        .ifBlank { extractPlannedExitDate(stringOrNull("operation_plan")) }
    return ThesisOperationCardModel(
        thesisNumber = intOrNull("thesis_number") ?: 0,
        action = action,
        phase = phase,
        front = front,
        status = status,
        outcome = stringOrNull("outcome").repairMojibake(),
        expectedPct = doubleOrNull("expected_result_pct"),
        resultPct = doubleOrNull("moment_result_pct"),
        entryPrice = doubleOrNull("entry_price_brl"),
        currentPrice = doubleOrNull("current_price_brl"),
        openDays = intOrNull("open_days"),
        raisedAt = raisedAt,
        latestAt = latestAt,
        plannedExitAt = plannedExitAt,
        isOpen = booleanOrNull("is_open") ?: inferOpenState(
            status = status,
            phase = phase,
            plannedExitAt = plannedExitAt,
        ),
        operationPlan = stringOrNull("operation_plan").repairMojibake(),
        structuredOperation = stringOrNull("structured_operation").repairMojibake(),
        exitRule = stringOrNull("exit_rule").repairMojibake(),
        thesisReason = stringOrNull("thesis_reason").repairMojibake(),
        learningNote = stringOrNull("learning_note").repairMojibake(),
    )
}

private fun String.toAssetFront(): AssetFront {
    val normalized = uppercase().trim()
    return if (
        normalized.endsWith("USDT") ||
        normalized.endsWith("USDC") ||
        normalized == "BTC" ||
        normalized == "ETH" ||
        normalized == "SOL"
    ) {
        AssetFront.Crypto
    } else {
        AssetFront.Stocks
    }
}

private fun String.toAssetFrontOrNull(): AssetFront? {
    val normalized = repairMojibake()
        .trim()
        .lowercase()
        .replace("á", "a")
        .replace("ã", "a")
        .replace("ç", "c")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("õ", "o")
    return when (normalized) {
        "acoes", "acoes b3", "stocks", "b3" -> AssetFront.Stocks
        "cripto", "crypto", "cryptocurrency" -> AssetFront.Crypto
        "imoveis", "imovel", "real_estate", "real estate", "realestate" -> AssetFront.RealEstate
        else -> null
    }
}

private fun JsonObject.objectOrNull(key: String): JsonObject? = get(key)?.let { element ->
    runCatching { element.jsonObject }.getOrNull()
}

private fun JsonObject.arrayOrNull(key: String): JsonArray? = get(key)?.let { element ->
    runCatching { element.jsonArray }.getOrNull()
}

private fun JsonObject.stringOrNull(key: String): String {
    val element = get(key) ?: return ""
    if (element == JsonNull) return ""
    return runCatching { element.jsonPrimitive.content }.getOrNull().orEmpty()
}

private fun JsonObject.doubleOrNull(key: String): Double? {
    val element = get(key) ?: return null
    if (element == JsonNull) return null
    return when (element) {
        is JsonPrimitive -> element.doubleOrNull
        else -> null
    }
}

private fun JsonObject.intOrNull(key: String): Int? {
    val element = get(key) ?: return null
    if (element == JsonNull) return null
    return when (element) {
        is JsonPrimitive -> element.intOrNull ?: element.doubleOrNull?.toInt()
        else -> null
    }
}

private fun JsonObject.booleanOrNull(key: String): Boolean? {
    val element = get(key) ?: return null
    if (element == JsonNull) return null
    return when (element) {
        is JsonPrimitive -> element.content.lowercase().let { value ->
            when (value) {
                "true" -> true
                "false" -> false
                else -> null
            }
        }
        else -> null
    }
}

private fun inferOpenState(
    status: String,
    phase: String,
    plannedExitAt: String,
): Boolean {
    if (status.equals("Fechada", ignoreCase = true)) return false
    if (phase.equals("historico", ignoreCase = true)) return false
    val plannedExitDate = parseLocalDate(plannedExitAt)
    if (plannedExitDate != null && plannedExitDate.isBefore(LocalDate.now())) {
        return false
    }
    return status.startsWith("Aberta", ignoreCase = true)
}

private fun extractPlannedExitDate(operationPlan: String): String {
    val marker = "ate "
    val normalized = operationPlan
        .repairMojibake()
        .lowercase()
        .replace("até", "ate")
    val index = normalized.indexOf(marker)
    if (index < 0) return ""
    val candidate = normalized.substring(index + marker.length).take(10)
    return if (parseLocalDate(candidate) != null) candidate else ""
}

private fun parseLocalDate(value: String): LocalDate? =
    runCatching { LocalDate.parse(value.trim()) }.getOrNull()

private fun String.repairMojibake(): String {
    if (!contains("Ã") && !contains("Â")) return this
    return runCatching {
        String(toByteArray(Charset.forName("ISO-8859-1")), Charsets.UTF_8)
    }.getOrDefault(this)
}
