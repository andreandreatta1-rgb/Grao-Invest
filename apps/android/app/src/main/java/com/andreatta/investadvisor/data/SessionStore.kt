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

data class AppSession(
    val token: String = "",
    val userId: Int? = null,
    val email: String = "",
    val baseUrl: String = BuildConfig.DEFAULT_BASE_API_URL,
    val disclaimerAccepted: Boolean = false,
) {
    val isAuthenticated: Boolean
        get() = token.isNotBlank() && userId != null
}

class SessionStore(context: Context) {
    private val dataStore = context.applicationContext.investAdvisorDataStore

    val session: Flow<AppSession> = dataStore.data.map { prefs ->
        AppSession(
            token = prefs[TOKEN].orEmpty(),
            userId = prefs[USER_ID],
            email = prefs[EMAIL].orEmpty(),
            baseUrl = prefs[BASE_URL] ?: BuildConfig.DEFAULT_BASE_API_URL,
            disclaimerAccepted = prefs[DISCLAIMER_ACCEPTED] ?: false,
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
    }
}
