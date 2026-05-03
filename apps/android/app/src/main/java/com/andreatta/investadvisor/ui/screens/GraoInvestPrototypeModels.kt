package com.andreatta.investadvisor.ui.screens

enum class GraoPrototypeTab(val label: String) {
    Teses("Teses"),
    Mercado("Mercado"),
    Analisar("Analisar"),
}

enum class GraoTradeDirection {
    Up,
    Down,
}

enum class GraoTradeStatus {
    Open,
    Warn,
    Invalid,
}

enum class GraoTone {
    Default,
    Green,
    Red,
    Gold,
    Blue,
    Purple,
    Date,
    Neutral,
}

data class GraoPrototypeNavItem(
    val tab: GraoPrototypeTab?,
    val label: String,
    val icon: String,
)

data class GraoStatPillModel(
    val label: String,
    val value: String,
    val tone: GraoTone = GraoTone.Default,
)

data class GraoTradeModel(
    val id: Int,
    val ticker: String,
    val direction: GraoTradeDirection,
    val status: GraoTradeStatus,
    val statusLabel: String,
    val resultPct: Double,
    val resultLabel: String,
    val pills: List<GraoStatPillModel>,
    val description: String,
    val progressPct: Int,
    val progressLabel: String,
    val strategy: String,
    val strategyTone: GraoTone,
    val maxGain: String,
    val riskLabel: String,
)

data class GraoMarketAssetModel(
    val ticker: String,
    val name: String,
    val price: String,
    val changePct: Double,
    val logo: String,
    val tone: GraoTone,
)

data class GraoStrategyReturnModel(
    val label: String,
    val value: String,
    val pct: Int,
    val tone: GraoTone,
)

val graoPrototypeTabs: List<GraoPrototypeTab> = GraoPrototypeTab.entries

val graoPrototypeBottomNavItems: List<GraoPrototypeNavItem> = listOf(
    GraoPrototypeNavItem(GraoPrototypeTab.Teses, "Teses", "▤"),
    GraoPrototypeNavItem(GraoPrototypeTab.Mercado, "Mercado", "↗"),
    GraoPrototypeNavItem(GraoPrototypeTab.Analisar, "Analisar", "⌁"),
    GraoPrototypeNavItem(null, "Perfil", "●"),
)

val graoPrototypeTrades: List<GraoTradeModel> = listOf(
    GraoTradeModel(
        id = 1595,
        ticker = "B3SA3",
        direction = GraoTradeDirection.Down,
        status = GraoTradeStatus.Invalid,
        statusLabel = "Aberta · Invalidada",
        resultPct = -2.30,
        resultLabel = "vs entrada",
        pills = listOf(
            GraoStatPillModel("Entrada", "R$ 17,04"),
            GraoStatPillModel("Esperado", "+0,66%", GraoTone.Green),
            GraoStatPillModel("Data", "30/03/26", GraoTone.Date),
        ),
        description = "Venda até 2026-04-22. Plano: capturar queda de 17,04 em direção a 16,64. Monitorar suporte técnico.",
        progressPct = 44,
        progressLabel = "44% da meta",
        strategy = "Bear Put Spread",
        strategyTone = GraoTone.Blue,
        maxGain = "+5,20%",
        riskLabel = "Perda lim.",
    ),
    GraoTradeModel(
        id = 1594,
        ticker = "SUZB3",
        direction = GraoTradeDirection.Up,
        status = GraoTradeStatus.Warn,
        statusLabel = "Aberta · Atenção",
        resultPct = -1.35,
        resultLabel = "vs entrada",
        pills = listOf(
            GraoStatPillModel("Entrada", "R$ 48,51"),
            GraoStatPillModel("Esperado", "+2,34%", GraoTone.Green),
            GraoStatPillModel("Data", "14/04/26", GraoTone.Date),
        ),
        description = "Compra até 2026-04-20. Plano: buscar alta de 48,51 para perto de 51,35. Se cair abaixo de 47,80, revisar.",
        progressPct = 20,
        progressLabel = "20% da meta",
        strategy = "Bull Call Spread",
        strategyTone = GraoTone.Purple,
        maxGain = "+5,40%",
        riskLabel = "Perda lim.",
    ),
    GraoTradeModel(
        id = 1593,
        ticker = "BPAC11",
        direction = GraoTradeDirection.Up,
        status = GraoTradeStatus.Warn,
        statusLabel = "Aberta · Atenção",
        resultPct = 1.07,
        resultLabel = "vs entrada",
        pills = listOf(
            GraoStatPillModel("Entrada", "R$ 63,25"),
            GraoStatPillModel("Esperado", "+3,15%", GraoTone.Green),
            GraoStatPillModel("Data", "14/04/26", GraoTone.Date),
        ),
        description = "Compra visando alta para R$ 65,24. Momentum positivo. Suporte em 62,80 deve ser mantido.",
        progressPct = 34,
        progressLabel = "34% da meta",
        strategy = "Compra Direta",
        strategyTone = GraoTone.Green,
        maxGain = "+6,80%",
        riskLabel = "Stop -2%",
    ),
)

val graoPrototypeMarketAssets: List<GraoMarketAssetModel> = listOf(
    GraoMarketAssetModel("B3SA3", "B3 S.A. Brasil Bolsa Balcão", "R$ 16,65", -2.30, "B3", GraoTone.Blue),
    GraoMarketAssetModel("SUZB3", "Suzano S.A.", "R$ 47,86", -1.35, "SZ", GraoTone.Purple),
    GraoMarketAssetModel("BPAC11", "BTG Pactual", "R$ 63,93", 1.07, "BP", GraoTone.Green),
    GraoMarketAssetModel("PETR4", "Petróleo Brasileiro", "R$ 38,42", 0.53, "PT", GraoTone.Gold),
    GraoMarketAssetModel("VALE3", "Vale S.A.", "R$ 62,15", -0.88, "VL", GraoTone.Red),
)

val graoPrototypeStrategyReturns: List<GraoStrategyReturnModel> = listOf(
    GraoStrategyReturnModel("Bull Call Spread", "+8,4%", 84, GraoTone.Blue),
    GraoStrategyReturnModel("Bear Put Spread", "+3,1%", 31, GraoTone.Purple),
    GraoStrategyReturnModel("Compra Direta", "+1,2%", 12, GraoTone.Gold),
)

val graoPrototypeIntradayBars: List<Int> = listOf(30, 45, 35, 60, 50, 75, 65, 80, 70, 90, 85, 95)
val graoPrototypeMonthlyBars: List<Int> = listOf(55, 72, 48, 85, 60)
