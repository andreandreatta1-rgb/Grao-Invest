package com.andreatta.investadvisor.network

import kotlinx.serialization.json.JsonObject
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface InvestApi {
    @GET("health")
    suspend fun health(): Response<JsonObject>

    @POST("api/auth/signup")
    suspend fun signup(@Body body: SignupRequest): Response<AuthResponse>

    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): Response<AuthResponse>

    @POST("api/auth/mfa/setup")
    suspend fun mfaSetup(@Body body: MfaSetupRequest): Response<AuthResponse>

    @POST("api/auth/mfa/verify")
    suspend fun mfaVerify(@Body body: MfaVerifyRequest): Response<AuthResponse>

    @GET("api/dashboard/summary/{user_id}")
    suspend fun dashboardSummary(@Path("user_id") userId: Int): Response<JsonObject>

    @GET("api/reports/summary/{user_id}")
    suspend fun reportSummary(@Path("user_id") userId: Int): Response<JsonObject>

    @GET("api/market/feed/health")
    suspend fun feedHealth(@Query("user_id") userId: Int): Response<JsonObject>

    @GET("api/market/universe/coverage")
    suspend fun marketCoverage(@Query("user_id") userId: Int): Response<JsonObject>

    @GET("api/market/ticks/{instrument}")
    suspend fun marketTicks(@Path("instrument") instrument: String): Response<List<JsonObject>>

    @GET("api/news/{instrument}")
    suspend fun news(@Path("instrument") instrument: String): Response<List<JsonObject>>

    @GET("api/fundamentals/{instrument}")
    suspend fun fundamentals(@Path("instrument") instrument: String): Response<JsonObject>

    @GET("api/analysis/indicators/{instrument}")
    suspend fun indicators(@Path("instrument") instrument: String): Response<JsonObject>

    @POST("api/market/intraday/fetch-live")
    suspend fun fetchIntraday(@Body body: JsonObject): Response<JsonObject>

    @POST("api/signals/generate")
    suspend fun generateSignal(@Body body: JsonObject): Response<JsonObject>

    @GET("api/signals")
    suspend fun signals(
        @Query("user_id") userId: Int,
        @Query("status") status: String = "active",
        @Query("limit") limit: Int = 20,
    ): Response<List<JsonObject>>

    @POST("api/paper/orders/from-signal/{signal_id}")
    suspend fun paperOrderFromSignal(
        @Path("signal_id") signalId: Int,
        @Body body: JsonObject,
    ): Response<JsonObject>

    @POST("api/backtests/run")
    suspend fun runBacktest(@Body body: JsonObject): Response<JsonObject>

    @GET("api/backtests/{run_id}")
    suspend fun backtestDetail(@Path("run_id") runId: Int): Response<JsonObject>

    @GET("api/risk/circuit-breaker/{instrument}")
    suspend fun circuitBreaker(@Path("instrument") instrument: String): Response<JsonObject>

    @POST("api/risk/kill-switch")
    suspend fun updateKillSwitch(@Body body: JsonObject): Response<JsonObject>

    @GET("api/risk/kill-switch")
    suspend fun killSwitches(): Response<List<JsonObject>>

    @POST("api/portfolio/allocate")
    suspend fun allocatePortfolio(@Body body: JsonObject): Response<JsonObject>

    @GET("api/portfolio/allocation/latest")
    suspend fun latestAllocation(): Response<JsonObject>

    @POST("api/portfolio/rebalance")
    suspend fun rebalance(@Body body: JsonObject): Response<JsonObject>

    @POST("api/theses/current-monitor")
    suspend fun currentMonitor(@Body body: JsonObject): Response<JsonObject>

    @GET("api/theses/current-monitor/latest")
    suspend fun latestMonitor(): Response<JsonObject>

    @POST("api/theses/case-study")
    suspend fun caseStudy(@Body body: JsonObject): Response<JsonObject>

    @POST("api/theses/ai-analysis")
    suspend fun aiThesisAnalysis(@Body body: JsonObject): Response<JsonObject>

    @POST("api/theses/game-playbook")
    suspend fun gamePlaybook(@Body body: JsonObject): Response<JsonObject>

    @POST("api/theses/game-simulation")
    suspend fun gameSimulation(@Body body: JsonObject): Response<JsonObject>

    @GET("api/real-estate/candidates")
    suspend fun realEstateCandidates(): Response<RealEstateCandidatesResponse>

    @POST("api/real-estate/candidates")
    suspend fun createRealEstateCandidate(
        @Body body: RealEstateCandidateRequest,
    ): Response<RealEstateCandidate>

    @PATCH("api/real-estate/candidates/{candidate_id}")
    suspend fun updateRealEstateCandidate(
        @Path("candidate_id") candidateId: Int,
        @Body body: JsonObject,
    ): Response<RealEstateCandidate>

    @GET("api/alerts/events/{user_id}")
    suspend fun alertEvents(@Path("user_id") userId: Int): Response<List<JsonObject>>

    @POST("api/alerts/rules")
    suspend fun createAlertRule(@Body body: JsonObject): Response<JsonObject>

    @GET("api/notifications/whatsapp")
    suspend fun whatsappSettings(@Query("user_id") userId: Int): Response<JsonObject>

    @PUT("api/notifications/whatsapp")
    suspend fun saveWhatsappSettings(@Body body: JsonObject): Response<JsonObject>

    @POST("api/notifications/whatsapp/test")
    suspend fun sendWhatsappTest(@Body body: JsonObject): Response<JsonObject>
}
