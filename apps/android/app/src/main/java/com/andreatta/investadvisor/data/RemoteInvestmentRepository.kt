package com.andreatta.investadvisor.data

import com.andreatta.investadvisor.network.ApiClientFactory
import com.andreatta.investadvisor.network.AuthResponse
import com.andreatta.investadvisor.network.InvestApi
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.network.LoginRequest
import com.andreatta.investadvisor.network.MfaSetupRequest
import com.andreatta.investadvisor.network.MfaVerifyRequest
import com.andreatta.investadvisor.network.SignupRequest
import kotlinx.coroutines.flow.first
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject
import retrofit2.Response

class RemoteInvestmentRepository(
    private val sessionStore: SessionStore,
    private val apiFactory: (AppSession) -> InvestApi = { session ->
        ApiClientFactory.create(session.baseUrl, tokenProvider = { session.token })
    },
) : InvestmentRepository {
    override suspend fun login(email: String, password: String, otpCode: String?): AuthResponse {
        return api().login(LoginRequest(email, password, otpCode.takeUnless { it.isNullOrBlank() }))
            .requireBody("login")
    }

    override suspend fun signup(
        tenantName: String,
        fullName: String,
        email: String,
        password: String,
    ): AuthResponse {
        return api().signup(
            SignupRequest(
                tenantName = tenantName,
                fullName = fullName,
                email = email,
                password = password,
                acceptedTerms = true,
                acceptedPrivacy = true,
            ),
        ).requireBody("cadastro")
    }

    override suspend fun mfaSetup(userId: Int): AuthResponse {
        return api().mfaSetup(MfaSetupRequest(userId)).requireBody("mfa setup")
    }

    override suspend fun mfaVerify(userId: Int, otpCode: String): AuthResponse {
        return api().mfaVerify(MfaVerifyRequest(userId, otpCode)).requireBody("mfa verify")
    }

    override suspend fun health(): JsonSummary {
        return summarize("Health", api().health().requireBody("health"))
    }

    override suspend fun dashboardSummary(userId: Int): JsonSummary {
        return summarize("Dashboard", api().dashboardSummary(userId).requireBody("dashboard"))
    }

    override suspend fun reportSummary(userId: Int): JsonSummary {
        return summarize("Relatorio", api().reportSummary(userId).requireBody("relatorio"))
    }

    override suspend fun loadFeature(action: FeatureAction, input: FeatureInput): JsonSummary {
        val api = api()
        val result = when (action) {
            FeatureAction.FeedHealth -> api.feedHealth(input.userId).requireBody(action.label)
            FeatureAction.MarketCoverage -> api.marketCoverage(input.userId).requireBody(action.label)
            FeatureAction.MarketTicks -> JsonArray(
                api.marketTicks(input.instrument).requireBody(action.label),
            )
            FeatureAction.News -> JsonArray(api.news(input.instrument).requireBody(action.label))
            FeatureAction.Fundamentals -> api.fundamentals(input.instrument).requireBody(action.label)
            FeatureAction.Indicators -> api.indicators(input.instrument).requireBody(action.label)
            FeatureAction.FetchIntraday -> api.fetchIntraday(
                buildJsonObject {
                    put("user_id", input.userId)
                    put("provider_name", "finnhub")
                    putJsonArray("instruments") { add(JsonPrimitive(input.instrument)) }
                    put("auto_recompute_indicators", true)
                },
            ).requireBody(action.label)
            FeatureAction.GenerateSignal -> api.generateSignal(userInstrumentBody(input)).requireBody(action.label)
            FeatureAction.ListSignals -> JsonArray(
                api.signals(input.userId, status = "all", limit = 20).requireBody(action.label),
            )
            FeatureAction.CurrentMonitor -> api.currentMonitor(thesisBody(input)).requireBody(action.label)
            FeatureAction.LatestMonitor -> api.latestMonitor().requireBody(action.label)
            FeatureAction.CaseStudy -> api.caseStudy(thesisBody(input)).requireBody(action.label)
            FeatureAction.PaperOrder -> api.paperOrderFromSignal(
                input.signalId,
                buildJsonObject {
                    put("user_id", input.userId)
                    put("quantity", input.quantity.coerceAtLeast(1))
                },
            ).requireBody(action.label)
            FeatureAction.AllocatePortfolio -> api.allocatePortfolio(
                buildJsonObject {
                    put("user_id", input.userId)
                    put("capital_brl", input.capitalBrl.coerceAtLeast(1000.0))
                    put("risk_profile", input.riskProfile)
                    put("universe", "multiasset")
                },
            ).requireBody(action.label)
            FeatureAction.LatestAllocation -> api.latestAllocation().requireBody(action.label)
            FeatureAction.Rebalance -> api.rebalance(
                buildJsonObject {
                    put("user_id", input.userId)
                },
            ).requireBody(action.label)
            FeatureAction.RunBacktest -> api.runBacktest(
                buildJsonObject {
                    put("user_id", input.userId)
                    put("instrument", input.instrument)
                    put("quantity", input.quantity.coerceAtLeast(1))
                },
            ).requireBody(action.label)
            FeatureAction.BacktestDetail -> api.backtestDetail(input.runId).requireBody(action.label)
            FeatureAction.CircuitBreaker -> api.circuitBreaker(input.instrument).requireBody(action.label)
            FeatureAction.ActiveKillSwitches -> JsonArray(api.killSwitches().requireBody(action.label))
            FeatureAction.ActivateKillSwitch -> api.updateKillSwitch(killSwitchBody(input, "active"))
                .requireBody(action.label)
            FeatureAction.ReleaseKillSwitch -> api.updateKillSwitch(killSwitchBody(input, "released"))
                .requireBody(action.label)
            FeatureAction.GamePlaybook -> api.gamePlaybook(gameBody(input, count = 5)).requireBody(action.label)
            FeatureAction.GameSimulation -> api.gameSimulation(gameBody(input, count = 10)).requireBody(action.label)
            FeatureAction.CreateAlertRule -> api.createAlertRule(
                buildJsonObject {
                    put("user_id", input.userId)
                    put("rule_type", "signal_confidence")
                    put("instrument", input.instrument)
                    put("threshold_value", 0.6)
                },
            ).requireBody(action.label)
        }
        return summarize(action.label, result)
    }

    override suspend fun whatsappSettings(userId: Int): JsonSummary {
        return summarize("WhatsApp", api().whatsappSettings(userId).requireBody("whatsapp"))
    }

    override suspend fun saveWhatsappSettings(input: WhatsAppSettingsInput): JsonSummary {
        val body = buildJsonObject {
            put("user_id", input.userId)
            put("phone_number", input.phoneNumber)
            if (input.displayName.isNullOrBlank()) {
                put("display_name", JsonNull)
            } else {
                put("display_name", input.displayName)
            }
            put("opt_in", input.optIn)
            putJsonObject("categories") {
                put("thesis_new", input.thesisNew)
                put("thesis_update", input.thesisUpdate)
                put("stock_alert", input.stockAlert)
                put("daily_digest", input.dailyDigest)
            }
            putJsonObject("thresholds") {
                put("thesis_confidence_pct", input.thesisConfidencePct)
                put("thesis_expected_pct", 0.0)
                put("thesis_progress_delta_pct", 20.0)
                put("stock_price_move_pct", input.stockPriceMovePct)
                put("news_magnitude", input.newsMagnitude)
                put("signal_confidence", input.thesisConfidencePct / 100.0)
            }
        }
        return summarize("WhatsApp salvo", api().saveWhatsappSettings(body).requireBody("whatsapp save"))
    }

    override suspend fun sendWhatsappTest(userId: Int): JsonSummary {
        return summarize(
            "Teste WhatsApp",
            api().sendWhatsappTest(buildJsonObject { put("user_id", userId) }).requireBody("whatsapp test"),
        )
    }

    override suspend fun alertEvents(userId: Int): JsonSummary {
        return summarize("Historico de alertas", JsonArray(api().alertEvents(userId).requireBody("alertas")))
    }

    private suspend fun api(): InvestApi {
        val session = sessionStore.session.first()
        return apiFactory(session)
    }

    private fun userInstrumentBody(input: FeatureInput): JsonObject = buildJsonObject {
        put("user_id", input.userId)
        put("instrument", input.instrument)
    }

    private fun thesisBody(input: FeatureInput): JsonObject = buildJsonObject {
        put("user_id", input.userId)
        putJsonArray("instruments") { add(JsonPrimitive(input.instrument)) }
        put("horizon_bars", 8)
    }

    private fun gameBody(input: FeatureInput, count: Int): JsonObject = buildJsonObject {
        put("user_id", input.userId)
        putJsonArray("instruments") { add(JsonPrimitive(input.instrument)) }
        put("horizon_bars", 8)
        put("thesis_count", count)
        put("player_initial_capital", input.capitalBrl.coerceAtLeast(1000.0))
    }

    private fun killSwitchBody(input: FeatureInput, status: String): JsonObject = buildJsonObject {
        put("scope_type", "instrument")
        put("scope_id", input.instrument)
        put("status", status)
        put("reason", "Acao confirmada no app Android")
    }
}

private fun <T> Response<T>.requireBody(operation: String): T {
    if (isSuccessful) {
        return body() ?: throw IllegalStateException("Resposta vazia em $operation")
    }
    val detail = errorBody()?.string()?.takeIf { it.isNotBlank() }
    throw IllegalStateException("Falha em $operation: HTTP ${code()} ${detail.orEmpty()}".trim())
}

fun summarize(title: String, element: JsonElement): JsonSummary {
    val rows = when (element) {
        is JsonArray -> summarizeArray(element)
        is JsonObject -> summarizeObject(element)
        is JsonPrimitive -> listOf(element.contentOrNull.orEmpty())
        JsonNull -> listOf("Sem dados.")
    }.ifEmpty { listOf("Sem dados para exibir.") }
    return JsonSummary(title = title, rows = rows.take(10), raw = element)
}

private fun summarizeArray(array: JsonArray): List<String> {
    if (array.isEmpty()) return listOf("Nenhum registro retornado.")
    return array.take(8).mapIndexed { index, item ->
        "${index + 1}. ${compact(item)}"
    }
}

private fun summarizeObject(obj: JsonObject): List<String> {
    val preferredKeys = listOf(
        "investor_profile",
        "disclaimer",
        "signal_id",
        "instrument",
        "decision",
        "confidence_score",
        "expected_return_pct",
        "risk_status",
        "summary",
        "run_id",
        "trade_count",
        "win_rate",
        "total_return_pct",
        "max_drawdown_pct",
        "status",
        "phone_number",
        "opt_in",
        "delivery_status",
        "alert_rule_id",
    )
    val preferredRows = preferredKeys.mapNotNull { key ->
        obj[key]?.let { "${key.toUiLabel()}: ${compact(it)}" }
    }
    val metricRows = listOf(
        "open_positions",
        "latest_signals",
        "latest_orders",
        "latest_news",
        "latest_backtests",
        "alert_events",
        "kill_switches",
    ).mapNotNull { key ->
        obj[key]?.jsonArray?.let { "${key.toUiLabel()}: ${it.size}" }
    }
    val fallbackRows = obj.entries
        .filterNot { (key, _) -> preferredKeys.contains(key) }
        .take(8)
        .map { (key, value) -> "${key.toUiLabel()}: ${compact(value)}" }
    return (preferredRows + metricRows + fallbackRows).distinct()
}

private fun compact(element: JsonElement): String = when (element) {
    is JsonObject -> {
        val keyValues = element.entries.take(4).joinToString(" | ") { (key, value) ->
            "${key.toUiLabel()}=${compact(value)}"
        }
        if (keyValues.isBlank()) "{}" else keyValues
    }
    is JsonArray -> "${element.size} itens"
    is JsonPrimitive -> when {
        element.isString -> element.contentOrNull.orEmpty().take(140)
        element.jsonPrimitive.intOrNull != null -> element.jsonPrimitive.intOrNull.toString()
        element.jsonPrimitive.doubleOrNull != null -> "%.2f".format(element.jsonPrimitive.doubleOrNull)
        else -> element.toString()
    }
    JsonNull -> "-"
}

private fun String.toUiLabel(): String = replace("_", " ")
    .replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
