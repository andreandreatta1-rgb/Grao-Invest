package com.andreatta.investadvisor.data

import com.andreatta.investadvisor.network.AuthResponse
import com.andreatta.investadvisor.network.JsonSummary
import com.andreatta.investadvisor.network.LoginRequest
import com.andreatta.investadvisor.network.RealEstateCandidate
import com.andreatta.investadvisor.network.RealEstateCandidateRequest
import com.andreatta.investadvisor.network.RealEstateCandidatesResponse
import com.andreatta.investadvisor.network.SignupRequest
import kotlinx.serialization.json.JsonObject

interface InvestmentRepository {
    suspend fun login(email: String, password: String, otpCode: String? = null): AuthResponse {
        unsupported()
    }

    suspend fun signup(
        tenantName: String,
        fullName: String,
        email: String,
        password: String,
    ): AuthResponse {
        unsupported()
    }

    suspend fun mfaSetup(userId: Int): AuthResponse {
        unsupported()
    }

    suspend fun mfaVerify(userId: Int, otpCode: String): AuthResponse {
        unsupported()
    }

    suspend fun health(): JsonSummary {
        unsupported()
    }

    suspend fun dashboardSummary(userId: Int): JsonSummary {
        unsupported()
    }

    suspend fun reportSummary(userId: Int): JsonSummary {
        unsupported()
    }

    suspend fun loadFeature(action: FeatureAction, input: FeatureInput): JsonSummary {
        unsupported()
    }

    suspend fun whatsappSettings(userId: Int): JsonSummary {
        unsupported()
    }

    suspend fun saveWhatsappSettings(input: WhatsAppSettingsInput): JsonSummary {
        unsupported()
    }

    suspend fun sendWhatsappTest(userId: Int): JsonSummary {
        unsupported()
    }

    suspend fun alertEvents(userId: Int): JsonSummary {
        unsupported()
    }

    suspend fun realEstateCandidates(): RealEstateCandidatesResponse {
        unsupported()
    }

    suspend fun createRealEstateCandidate(input: RealEstateCandidateRequest): RealEstateCandidate {
        unsupported()
    }

    suspend fun updateRealEstateCandidate(candidateId: Int, patch: JsonObject): RealEstateCandidate {
        unsupported()
    }

    private fun unsupported(): Nothing = throw UnsupportedOperationException("Nao implementado")
}

data class FeatureInput(
    val userId: Int,
    val instrument: String,
    val quantity: Int,
    val signalId: Int,
    val runId: Int,
    val capitalBrl: Double,
    val riskProfile: String,
)

enum class FeatureAction(val label: String) {
    FeedHealth("Saude do feed"),
    MarketCoverage("Cobertura"),
    MarketTicks("Ticks"),
    News("Noticias"),
    Fundamentals("Fundamentos"),
    Indicators("Indicadores"),
    FetchIntraday("Buscar intraday"),
    GenerateSignal("Gerar sinal"),
    ListSignals("Listar sinais"),
    CurrentMonitor("Monitor atual"),
    LatestMonitor("Ultimo monitor"),
    CaseStudy("Estudo de caso"),
    AiThesisAnalysis("Analise IA da tese"),
    PaperOrder("Criar ordem simulada"),
    AllocatePortfolio("Alocar carteira"),
    LatestAllocation("Ultima alocacao"),
    Rebalance("Rebalancear"),
    RunBacktest("Rodar backtest"),
    BacktestDetail("Consultar backtest"),
    CircuitBreaker("Circuit breaker"),
    ActiveKillSwitches("Kill-switches"),
    ActivateKillSwitch("Ativar kill-switch"),
    ReleaseKillSwitch("Liberar kill-switch"),
    GamePlaybook("Playbook"),
    GameSimulation("Simulacao"),
    CreateAlertRule("Criar regra de alerta"),
}

data class WhatsAppSettingsInput(
    val userId: Int,
    val phoneNumber: String,
    val displayName: String?,
    val optIn: Boolean,
    val thesisNew: Boolean,
    val thesisUpdate: Boolean,
    val stockAlert: Boolean,
    val dailyDigest: Boolean,
    val thesisConfidencePct: Double,
    val stockPriceMovePct: Double,
    val newsMagnitude: Double,
)

fun LoginRequest.toSessionEmail(): String = email
fun SignupRequest.toSessionEmail(): String = email
