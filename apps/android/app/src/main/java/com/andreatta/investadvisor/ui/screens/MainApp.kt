package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ShowChart
import androidx.compose.material.icons.automirrored.filled.TrendingUp
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.HealthAndSafety
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.andreatta.investadvisor.data.AppSession
import com.andreatta.investadvisor.data.FeatureAction
import com.andreatta.investadvisor.data.FeatureInput
import com.andreatta.investadvisor.data.InvestmentRepository
import com.andreatta.investadvisor.data.SessionStore
import com.andreatta.investadvisor.ui.viewmodel.AlertsViewModel
import com.andreatta.investadvisor.ui.viewmodel.AuthViewModel
import com.andreatta.investadvisor.ui.viewmodel.DashboardViewModel
import com.andreatta.investadvisor.ui.viewmodel.FeatureViewModel
import com.andreatta.investadvisor.ui.viewmodel.simpleViewModelFactory

private enum class MainTab(val title: String, val icon: ImageVector) {
    Home("Início", Icons.Default.Dashboard),
    Operacoes("Operar", Icons.Default.AccountBalanceWallet),
    Teses("Teses", Icons.AutoMirrored.Filled.TrendingUp),
    Aprender("Aprender", Icons.Default.Timeline),
    Config("Config", Icons.Default.Settings),
}

private val MainNavBackground = Color(0xFF0A0E1A)
private val MainNavSelected = Color(0xFF00D4AA)
private val MainNavText = Color(0xFFE8EDF7)
private val MainNavMuted = Color(0xFF8A9BC0)
private val MainNavIndicator = Color(0xFF16233D)

@Composable
fun InvestAdvisorApp(
    session: AppSession,
    sessionStore: SessionStore,
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    if (!session.isAuthenticated) {
        val authViewModel: AuthViewModel = viewModel(
            key = "auth",
            factory = simpleViewModelFactory {
                AuthViewModel(repository, sessionStore)
            },
        )
        AuthScreen(authViewModel, modifier)
    } else {
        MainShell(session, sessionStore, repository, modifier)
    }
}

@Composable
private fun MainShell(
    session: AppSession,
    sessionStore: SessionStore,
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    var selectedIndex by rememberSaveable { mutableIntStateOf(0) }
    var selectedFrontName by rememberSaveable { mutableStateOf(AssetFront.Stocks.name) }
    val tabs = MainTab.entries
    val selectedFront = runCatching { AssetFront.valueOf(selectedFrontName) }.getOrDefault(AssetFront.Stocks)

    fun openFront(front: AssetFront) {
        selectedFrontName = front.name
        selectedIndex = tabs.indexOf(MainTab.Operacoes)
    }

    Scaffold(
        containerColor = MainNavBackground,
        bottomBar = {
            NavigationBar(
                containerColor = MainNavBackground,
                contentColor = MainNavText,
                tonalElevation = 0.dp,
            ) {
                tabs.forEachIndexed { index, tab ->
                    NavigationBarItem(
                        selected = selectedIndex == index,
                        onClick = { selectedIndex = index },
                        icon = { Icon(tab.icon, contentDescription = tab.title) },
                        label = { Text(tab.title) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MainNavSelected,
                            selectedTextColor = MainNavText,
                            indicatorColor = MainNavIndicator,
                            unselectedIconColor = MainNavMuted,
                            unselectedTextColor = MainNavMuted,
                        ),
                    )
                }
            }
        },
        modifier = modifier.fillMaxSize(),
    ) { padding ->
        val pageModifier = Modifier
            .padding(padding)
            .fillMaxSize()
        when (tabs[selectedIndex]) {
            MainTab.Home -> HomeDashboardScreen(
                session = session,
                repository = repository,
                onOpenFront = ::openFront,
                modifier = pageModifier,
            )
            MainTab.Operacoes -> {
                if (selectedFront == AssetFront.RealEstate) {
                    RealEstateRadarScreen(repository, pageModifier)
                } else {
                    OperationsScreen(
                        session = session,
                        repository = repository,
                        selectedFront = selectedFront,
                        onFrontSelected = { selectedFrontName = it.name },
                        modifier = pageModifier,
                    )
                }
            }
            MainTab.Teses -> ThesesOverviewScreen(session, repository, pageModifier)
            MainTab.Aprender -> LearningScreen(session, repository, pageModifier)
            MainTab.Config -> SettingsScreen(session, sessionStore, repository, pageModifier)
        }
    }
}

@Composable
private fun HomeDashboardScreen(
    session: AppSession,
    repository: InvestmentRepository,
    onOpenFront: (AssetFront) -> Unit,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<DashboardViewModel>(
        key = "dashboard-home",
        factory = simpleViewModelFactory { DashboardViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()

    LaunchedEffect(session.userId) {
        session.userId?.let { viewModel.refresh(it) }
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        ThesisFrontHubState(
            state = state,
            onOpenFront = onOpenFront,
        )
    }
}

@Composable
private fun ThesesOverviewScreen(
    session: AppSession,
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<DashboardViewModel>(
        key = "dashboard-theses",
        factory = simpleViewModelFactory { DashboardViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()

    LaunchedEffect(session.userId) {
        session.userId?.let { viewModel.refresh(it) }
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        ThesisListState(state = state)
    }
}

@Composable
private fun OperationsScreen(
    session: AppSession,
    repository: InvestmentRepository,
    selectedFront: AssetFront,
    onFrontSelected: (AssetFront) -> Unit,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<DashboardViewModel>(
        key = "dashboard-operations",
        factory = simpleViewModelFactory { DashboardViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()

    LaunchedEffect(session.userId) {
        session.userId?.let { viewModel.refresh(it) }
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionHeader("Operações", "Acompanhamento das teses abertas por frente.")
        DisclaimerBar()
        RefreshButton("Atualizar", onClick = { session.userId?.let { viewModel.refresh(it) } })
        ThesisDashboardState(
            state = state,
            selectedFront = selectedFront,
            onFrontSelected = onFrontSelected,
        )
    }
}

@Composable
private fun LearningScreen(
    session: AppSession,
    repository: InvestmentRepository,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<DashboardViewModel>(
        key = "dashboard-learning",
        factory = simpleViewModelFactory { DashboardViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()

    LaunchedEffect(session.userId) {
        session.userId?.let { viewModel.refresh(it) }
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionHeader("Aprendizados", "Dor e remédio: o que o mecanismo está incorporando.")
        DisclaimerBar()
        RefreshButton("Atualizar", onClick = { session.userId?.let { viewModel.refresh(it) } })
        ThesisLearningState(state)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun FeatureScreen(
    title: String,
    subtitle: String,
    actions: List<FeatureAction>,
    session: AppSession,
    repository: InvestmentRepository,
    defaultInstrument: String = "PETR4",
    defaultQuantity: String = "10",
    defaultCapital: String = "100000",
    defaultRiskProfile: String = "moderado",
    topContent: (@Composable () -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val viewModel = viewModel<FeatureViewModel>(
        key = title,
        factory = simpleViewModelFactory { FeatureViewModel(repository) },
    )
    val state by viewModel.state.collectAsState()
    var instrument by rememberSaveable(title) { mutableStateOf(defaultInstrument) }
    var quantity by rememberSaveable(title) { mutableStateOf(defaultQuantity) }
    var signalId by rememberSaveable(title) { mutableStateOf("1") }
    var runId by rememberSaveable(title) { mutableStateOf("1") }
    var capital by rememberSaveable(title) { mutableStateOf(defaultCapital) }
    var riskProfile by rememberSaveable(title) { mutableStateOf(defaultRiskProfile) }
    var pending by remember { mutableStateOf<FeatureAction?>(null) }

    fun input(): FeatureInput = FeatureInput(
        userId = session.userId ?: 0,
        instrument = instrument.trim().uppercase().ifBlank { "PETR4" },
        quantity = quantity.toIntOrNull() ?: 10,
        signalId = signalId.toIntOrNull() ?: 1,
        runId = runId.toIntOrNull() ?: 1,
        capitalBrl = capital.toDoubleOrNull() ?: 100000.0,
        riskProfile = riskProfile,
    )

    fun run(action: FeatureAction) {
        if (action.requiresConfirmation()) {
            pending = action
        } else {
            viewModel.run(action, input())
        }
    }

    pending?.let { action ->
        AlertDialog(
            onDismissRequest = { pending = null },
            title = { Text("Confirmar ${action.label}") },
            text = {
                Text("Esta ação altera estado operacional simulado ou de risco para ${instrument.uppercase()}.")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        pending = null
                        viewModel.run(action, input())
                    },
                ) {
                    Text("Confirmar")
                }
            },
            dismissButton = {
                TextButton(onClick = { pending = null }) {
                    Text("Cancelar")
                }
            },
        )
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionHeader(title, subtitle)
        DisclaimerBar()
        topContent?.invoke()
        OutlinedTextField(
            value = instrument,
            onValueChange = { instrument = it },
            label = { Text("Ticker") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedTextField(
                value = quantity,
                onValueChange = { quantity = it.filter(Char::isDigit) },
                label = { Text("Quantidade") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = signalId,
                onValueChange = { signalId = it.filter(Char::isDigit) },
                label = { Text("Signal ID") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedTextField(
                value = runId,
                onValueChange = { runId = it.filter(Char::isDigit) },
                label = { Text("Run ID") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = capital,
                onValueChange = { capital = it.filter { ch -> ch.isDigit() || ch == '.' } },
                label = { Text("Capital BRL") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
        }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("conservador", "moderado", "arrojado").forEach { profile ->
                FilterChip(
                    selected = riskProfile == profile,
                    onClick = { riskProfile = profile },
                    label = { Text(profile) },
                )
            }
        }
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            actions.forEach { action ->
                ActionButton(action.label, onClick = { run(action) })
            }
        }
        SummaryState(state, idleText = "Escolha uma ação para consultar ou executar.")
    }
}

private fun FeatureAction.requiresConfirmation(): Boolean = when (this) {
    FeatureAction.PaperOrder,
    FeatureAction.ActivateKillSwitch,
    FeatureAction.ReleaseKillSwitch,
    FeatureAction.FetchIntraday,
    FeatureAction.AllocatePortfolio,
    FeatureAction.Rebalance,
    -> true
    else -> false
}
