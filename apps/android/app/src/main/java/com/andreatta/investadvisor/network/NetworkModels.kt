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

data class JsonSummary(
    val title: String,
    val rows: List<String>,
    val raw: JsonElement? = null,
)
