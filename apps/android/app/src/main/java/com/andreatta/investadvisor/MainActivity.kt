package com.andreatta.investadvisor

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.andreatta.investadvisor.data.AppSession
import com.andreatta.investadvisor.data.RemoteInvestmentRepository
import com.andreatta.investadvisor.data.SessionStore
import com.andreatta.investadvisor.ui.InvestAdvisorTheme
import com.andreatta.investadvisor.ui.screens.InvestAdvisorApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            InvestAdvisorTheme {
                val context = LocalContext.current
                val sessionStore = remember { SessionStore(context) }
                val repository = remember { RemoteInvestmentRepository(sessionStore) }
                val session by sessionStore.session.collectAsState(initial = AppSession())
                InvestAdvisorApp(
                    session = session,
                    sessionStore = sessionStore,
                    repository = repository,
                )
            }
        }
    }
}
