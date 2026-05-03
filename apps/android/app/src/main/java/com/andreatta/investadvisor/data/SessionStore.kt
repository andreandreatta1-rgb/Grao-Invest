package com.andreatta.investadvisor.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.andreatta.investadvisor.BuildConfig
import com.andreatta.investadvisor.network.ensureTrailingSlash
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.investAdvisorDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "invest_advisor_session",
)

private const val ANONYMOUS_USER_ID = 1
private const val ANONYMOUS_EMAIL = "acesso.anonimo@grao.local"

data class AppSession(
    val token: String = "",
    val userId: Int? = ANONYMOUS_USER_ID,
    val email: String = ANONYMOUS_EMAIL,
    val baseUrl: String = BuildConfig.DEFAULT_BASE_API_URL,
    val disclaimerAccepted: Boolean = true,
) {
    val isAuthenticated: Boolean
        get() = userId != null
}

class SessionStore(context: Context) {
    private val dataStore = context.applicationContext.investAdvisorDataStore

    val session: Flow<AppSession> = dataStore.data.map { prefs ->
        val storedBaseUrl = prefs[BASE_URL]
        AppSession(
            token = prefs[TOKEN].orEmpty(),
            userId = prefs[USER_ID] ?: ANONYMOUS_USER_ID,
            email = prefs[EMAIL] ?: ANONYMOUS_EMAIL,
            baseUrl = sanitizeStoredBaseUrl(storedBaseUrl),
            disclaimerAccepted = prefs[DISCLAIMER_ACCEPTED] ?: true,
        )
    }

    suspend fun saveAuth(userId: Int, email: String, token: String) {
        dataStore.edit { prefs ->
            prefs[USER_ID] = userId
            prefs[EMAIL] = email
            prefs[TOKEN] = token
            prefs[DISCLAIMER_ACCEPTED] = true
        }
    }

    suspend fun updateBaseUrl(baseUrl: String) {
        dataStore.edit { prefs ->
            prefs[BASE_URL] = baseUrl.trim().ensureTrailingSlash()
        }
    }

    suspend fun acceptDisclaimer() {
        dataStore.edit { prefs -> prefs[DISCLAIMER_ACCEPTED] = true }
    }

    suspend fun logout() {
        dataStore.edit { prefs ->
            prefs.remove(TOKEN)
            prefs.remove(USER_ID)
            prefs.remove(EMAIL)
        }
    }

    private companion object {
        val TOKEN = stringPreferencesKey("auth_token")
        val USER_ID = intPreferencesKey("user_id")
        val EMAIL = stringPreferencesKey("email")
        val BASE_URL = stringPreferencesKey("base_url")
        val DISCLAIMER_ACCEPTED = booleanPreferencesKey("disclaimer_accepted")

        fun sanitizeStoredBaseUrl(storedBaseUrl: String?): String {
            val saved = storedBaseUrl?.trim().orEmpty()
            if (saved.isBlank()) return BuildConfig.DEFAULT_BASE_API_URL
            if (!BuildConfig.DEBUG && saved.isLocalDevelopmentUrl()) {
                return BuildConfig.DEFAULT_BASE_API_URL
            }
            return saved.ensureTrailingSlash()
        }

        fun String.isLocalDevelopmentUrl(): Boolean {
            val normalized = trim().lowercase()
            return normalized.startsWith("http://127.") ||
                normalized.startsWith("http://localhost") ||
                normalized.startsWith("http://10.0.2.2") ||
                normalized.startsWith("http://192.168.")
        }
    }
}
