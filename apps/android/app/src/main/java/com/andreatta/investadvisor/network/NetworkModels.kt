package com.andreatta.investadvisor.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

val NetworkJson: Json = Json {
    ignoreUnknownKeys = true
    isLenient = true
    encodeDefaults = true
}

@Serializable
data class SignupRequest(
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("full_name") val fullName: String,
    val email: String,
    val password: String,
    @SerialName("accepted_terms") val acceptedTerms: Boolean,
    @SerialName("accepted_privacy") val acceptedPrivacy: Boolean,
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String,
    @SerialName("otp_code") val otpCode: String? = null,
)

@Serializable
data class MfaSetupRequest(
    @SerialName("user_id") val userId: Int,
)

@Serializable
data class MfaVerifyRequest(
    @SerialName("user_id") val userId: Int,
    @SerialName("otp_code") val otpCode: String,
)

@Serializable
data class AuthResponse(
    @SerialName("user_id") val userId: Int? = null,
    @SerialName("tenant_id") val tenantId: Int? = null,
    val email: String? = null,
    @SerialName("mfa_enabled") val mfaEnabled: Boolean = false,
    @SerialName("token_type") val tokenType: String? = null,
    @SerialName("expires_in") val expiresIn: Int? = null,
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("provisioning_uri") val provisioningUri: String? = null,
    @SerialName("mfa_verified") val mfaVerified: Boolean? = null,
)

@Serializable
data class RealEstateCandidatesResponse(
    val summary: RealEstateSummary = RealEstateSummary(),
    val items: List<RealEstateCandidate> = emptyList(),
)

@Serializable
data class RealEstateSummary(
    val total: Int = 0,
    @SerialName("status_counts") val statusCounts: Map<String, Int> = emptyMap(),
)

@Serializable
data class RealEstateCandidate(
    val id: Int,
    val title: String,
    @SerialName("source_url") val sourceUrl: String = "",
    val origin: String? = null,
    val strategy: String? = null,
    val city: String? = null,
    val neighborhood: String? = null,
    @SerialName("asking_price") val askingPrice: Double? = null,
    val status: String? = null,
    val analysis: RealEstateCandidateAnalysis = RealEstateCandidateAnalysis(),
)

@Serializable
data class RealEstateCandidateAnalysis(
    val score: Int = 0,
    val confidence: Int = 0,
    @SerialName("suggested_status") val suggestedStatus: String? = null,
    @SerialName("next_action") val nextAction: String? = null,
    @SerialName("cash_needed") val cashNeeded: Double? = null,
    @SerialName("max_purchase_price") val maxPurchasePrice: Double? = null,
    @SerialName("price_gap_to_ceiling") val priceGapToCeiling: Double? = null,
    @SerialName("price_ceiling_status") val priceCeilingStatus: String? = null,
    @SerialName("target_roi_pct") val targetRoiPct: Double? = null,
    @SerialName("pending_items") val pendingItems: List<RealEstatePendingItem> = emptyList(),
    val scenarios: RealEstateScenarios = RealEstateScenarios(),
)

@Serializable
data class RealEstatePendingItem(
    val title: String,
    val priority: String,
    val status: String,
)

@Serializable
data class RealEstateScenarios(
    val conservative: RealEstateScenario? = null,
    val base: RealEstateScenario? = null,
    val optimistic: RealEstateScenario? = null,
)

@Serializable
data class RealEstateScenario(
    @SerialName("sale_price") val salePrice: Double? = null,
    @SerialName("net_profit") val netProfit: Double? = null,
    @SerialName("roi_pct") val roiPct: Double? = null,
)

@Serializable
data class RealEstateCandidateRequest(
    val title: String,
    @SerialName("source_url") val sourceUrl: String = "",
    val origin: String,
    val strategy: String,
    val city: String? = null,
    val neighborhood: String? = null,
    @SerialName("asking_price") val askingPrice: Double? = null,
    @SerialName("estimated_sale_price") val estimatedSalePrice: Double? = null,
    @SerialName("estimated_reform_cost") val estimatedReformCost: Double? = null,
    @SerialName("cash_needed") val cashNeeded: Double? = null,
    @SerialName("occupancy_status") val occupancyStatus: String? = null,
    @SerialName("has_registration") val hasRegistration: Boolean? = null,
    @SerialName("has_debt_check") val hasDebtCheck: Boolean? = null,
    val notes: String? = null,
)

data class JsonSummary(
    val title: String,
    val rows: List<String>,
    val raw: JsonElement? = null,
)
