package com.andreatta.investadvisor.ui.screens

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import java.util.Locale

private val GraoBg = Color(0xFF0A0E1A)
private val GraoBg2 = Color(0xFF0F1628)
private val GraoCard = Color(0xFF141C30)
private val GraoCard2 = Color(0xFF1A2340)
private val GraoGreen = Color(0xFF00D4AA)
private val GraoGreen2 = Color(0xFF00FF9D)
private val GraoRed = Color(0xFFFF4D6A)
private val GraoGold = Color(0xFFF5C842)
private val GraoBlue = Color(0xFF4F8EF7)
private val GraoText2 = Color(0xFF8A9BC0)
private val GraoText3 = Color(0xFF5A6A8A)
private val GraoBorder = Color.White.copy(alpha = 0.07f)
private val ptBr = Locale("pt", "BR")

@Composable
fun GraoInvestPrototypeScreen(modifier: Modifier = Modifier) {
    var activeTab by rememberSaveable { mutableStateOf(GraoPrototypeTab.Teses) }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(GraoBg),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            PrototypeHeader(
                activeTab = activeTab,
                onTabChange = { activeTab = it },
            )
            Column(
                verticalArrangement = Arrangement.spacedBy(14.dp),
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp)
                    .padding(bottom = 20.dp),
            ) {
                when (activeTab) {
                    GraoPrototypeTab.Teses -> TesesPrototypeScreen()
                    GraoPrototypeTab.Mercado -> MercadoPrototypeScreen()
                    GraoPrototypeTab.Analisar -> AnalisarPrototypeScreen()
                }
            }
        }
    }
}

@Composable
private fun PrototypeHeader(
    activeTab: GraoPrototypeTab,
    onTabChange: (GraoPrototypeTab) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    listOf(GraoCard, GraoBg.copy(alpha = 0f)),
                ),
            )
            .padding(horizontal = 24.dp)
            .padding(top = 18.dp, bottom = 16.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(Brush.linearGradient(listOf(GraoGreen, GraoGreen2))),
                ) {
                    Text("G", color = GraoBg, fontWeight = FontWeight.Black)
                }
                Text(
                    text = "Grão Invest",
                    style = MaterialTheme.typography.titleMedium,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                )
            }
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(38.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .border(1.dp, GraoBorder, RoundedCornerShape(12.dp))
                    .background(GraoCard2),
            ) {
                Icon(Icons.Default.Notifications, contentDescription = "Notificações", tint = Color.White)
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(top = 8.dp, end = 8.dp)
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(GraoGreen),
                )
            }
        }
        Spacer(Modifier.height(20.dp))
        TabBar(activeTab = activeTab, onTabChange = onTabChange)
    }
}

@Composable
private fun TabBar(
    activeTab: GraoPrototypeTab,
    onTabChange: (GraoPrototypeTab) -> Unit,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(GraoCard)
            .padding(4.dp),
    ) {
        graoPrototypeTabs.forEach { tab ->
            val selected = activeTab == tab
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(12.dp))
                    .background(
                        if (selected) {
                            Brush.linearGradient(listOf(Color(0xFF1A3A6A), Color(0xFF1F4580)))
                        } else {
                            Brush.linearGradient(listOf(Color.Transparent, Color.Transparent))
                        },
                    )
                    .clickable { onTabChange(tab) }
                    .padding(vertical = 10.dp),
            ) {
                Text(
                    text = tab.label,
                    color = if (selected) Color.White else GraoText2,
                    fontWeight = FontWeight.SemiBold,
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        }
    }
}

@Composable
private fun TesesPrototypeScreen() {
    SummaryCard()
    graoPrototypeTrades.forEach { trade ->
        TradeCard(trade)
    }
}

@Composable
private fun SummaryCard() {
    Surface(
        color = Color.Transparent,
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, GraoBlue.copy(alpha = 0.15f), RoundedCornerShape(20.dp)),
    ) {
        Column(
            modifier = Modifier
                .background(
                    Brush.linearGradient(
                        listOf(Color(0xFF0F2A4A), Color(0xFF0D1F3A), Color(0xFF0A1A30)),
                    ),
                )
                .padding(20.dp),
        ) {
            Text(
                "Operações em Aberto · Ações B3",
                color = GraoText2,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    graoPrototypeTrades.size.toString(),
                    color = Color.White,
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.ExtraBold,
                )
                Spacer(Modifier.width(6.dp))
                Text("posições", color = GraoText2, style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.fillMaxWidth()) {
                SummaryStat("Média", "-0,86%", GraoText2, Modifier.weight(1f))
                SummaryStat("Melhor", "+1,07%", GraoGreen2, Modifier.weight(1f))
                SummaryStat("Pior", "-2,30%", GraoRed, Modifier.weight(1f))
                SummaryStat("Exposição", "R$ 128k", GraoGold, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun SummaryStat(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(label, color = GraoText3, style = MaterialTheme.typography.labelSmall)
        Text(
            value,
            color = color,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
    }
}

@Composable
private fun TradeCard(trade: GraoTradeModel) {
    val sideColor = if (trade.direction == GraoTradeDirection.Up) GraoGreen else GraoRed
    Surface(
        color = Color.Transparent,
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, GraoBorder, RoundedCornerShape(20.dp)),
    ) {
        Row(
            modifier = Modifier
                .background(Brush.linearGradient(listOf(GraoCard2, GraoCard)))
                .clickable {}
        ) {
            Box(
                modifier = Modifier
                    .width(3.dp)
                    .fillMaxSize()
                    .background(sideColor),
            )
            Column(
                verticalArrangement = Arrangement.spacedBy(14.dp),
                modifier = Modifier.padding(18.dp),
            ) {
                TradeCardHeader(trade)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    trade.pills.forEach { pill ->
                        StatPill(pill, Modifier.weight(1f))
                    }
                }
                Text(
                    trade.description,
                    color = GraoText2,
                    style = MaterialTheme.typography.bodySmall,
                    lineHeight = MaterialTheme.typography.bodySmall.lineHeight * 1.15,
                )
                AnimatedProgress(trade.progressPct, trade.progressLabel, trade.status)
                Row(
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    StrategyBadge(trade.strategy, trade.strategyTone)
                    Text(
                        text = "Max ${trade.maxGain}  ${trade.riskLabel}",
                        color = GraoText3,
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                    )
                }
            }
        }
    }
}

@Composable
private fun TradeCardHeader(trade: GraoTradeModel) {
    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
        Column {
            Text("#${trade.id}", color = GraoText3, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold)
            Text(
                trade.ticker,
                color = Color.White,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.ExtraBold,
            )
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                PulsingStatusDot(trade.status)
                Text(
                    trade.statusLabel,
                    color = statusColor(trade.status),
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
        Column(horizontalAlignment = Alignment.End) {
            Text(
                formatPct(trade.resultPct),
                color = if (trade.resultPct >= 0) GraoGreen2 else GraoRed,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.ExtraBold,
            )
            Text(trade.resultLabel, color = GraoText3, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun PulsingStatusDot(status: GraoTradeStatus) {
    val transition = rememberInfiniteTransition(label = "statusPulse")
    val alpha by transition.animateFloat(
        initialValue = 1f,
        targetValue = if (status == GraoTradeStatus.Warn) 0.55f else 1f,
        animationSpec = infiniteRepeatable(tween(750), RepeatMode.Reverse),
        label = "statusAlpha",
    )
    val scale by transition.animateFloat(
        initialValue = 1f,
        targetValue = if (status == GraoTradeStatus.Warn) 0.82f else 1f,
        animationSpec = infiniteRepeatable(tween(750), RepeatMode.Reverse),
        label = "statusScale",
    )
    Box(
        modifier = Modifier
            .size(6.dp)
            .scale(scale)
            .clip(CircleShape)
            .background(statusColor(status).copy(alpha = alpha)),
    )
}

@Composable
private fun StatPill(pill: GraoStatPillModel, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .border(1.dp, GraoBorder, RoundedCornerShape(12.dp))
            .background(Color.White.copy(alpha = 0.04f))
            .padding(horizontal = 12.dp, vertical = 10.dp),
    ) {
        Text(
            pill.label.uppercase(ptBr),
            color = GraoText3,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            pill.value,
            color = toneColor(pill.tone),
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun StrategyBadge(label: String, tone: GraoTone) {
    Text(
        text = "▦ $label",
        color = toneColor(tone),
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .border(1.dp, toneColor(tone).copy(alpha = 0.22f), RoundedCornerShape(8.dp))
            .background(toneColor(tone).copy(alpha = 0.08f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
    )
}

@Composable
private fun AnimatedProgress(progressPct: Int, label: String, status: GraoTradeStatus) {
    val animated by animateFloatAsState(
        targetValue = progressPct.coerceIn(0, 100) / 100f,
        animationSpec = tween(700),
        label = "tradeProgress",
    )
    val progressColor = when (status) {
        GraoTradeStatus.Invalid -> GraoRed
        GraoTradeStatus.Warn -> GraoGold
        GraoTradeStatus.Open -> GraoGreen
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(
            modifier = Modifier
                .weight(1f)
                .height(4.dp)
                .clip(RoundedCornerShape(4.dp))
                .background(Color.White.copy(alpha = 0.08f)),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(animated)
                    .height(4.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(progressColor),
            )
        }
        Text(label, color = GraoText3, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun MercadoPrototypeScreen() {
    ScreenHeader("Índices & Ativos", "Tempo real")
    ChartCard()
    ScreenHeader("Ações em destaque")
    graoPrototypeMarketAssets.forEach { asset ->
        MarketItem(asset)
    }
}

@Composable
private fun ScreenHeader(title: String, badge: String? = null) {
    Row(
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(title, color = Color.White, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        badge?.let {
            Text(
                it,
                color = GraoGreen,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .border(1.dp, GraoGreen.copy(alpha = 0.20f), RoundedCornerShape(20.dp))
                    .background(GraoGreen.copy(alpha = 0.12f))
                    .padding(horizontal = 10.dp, vertical = 4.dp),
            )
        }
    }
}

@Composable
private fun ChartCard() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .border(1.dp, GraoBorder, RoundedCornerShape(20.dp))
            .background(Brush.linearGradient(listOf(GraoCard2, GraoCard)))
            .padding(20.dp),
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text("IBOV — Hoje", color = Color.White, fontWeight = FontWeight.Bold)
            Text("+0,82%", color = GraoGreen, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(14.dp))
        Bars(graoPrototypeIntradayBars, listOf("9h", "12h", "15h", "18h17"))
    }
}

@Composable
private fun Bars(values: List<Int>, labels: List<String>) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.Bottom,
        modifier = Modifier
            .fillMaxWidth()
            .height(60.dp),
    ) {
        values.forEach { value ->
            val animated by animateFloatAsState(value / 100f, tween(600), label = "bar$value")
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .height((60 * animated).dp)
                    .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                    .background(if (value > 85) GraoGreen2 else GraoGreen.copy(alpha = 0.45f)),
            )
        }
    }
    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
        labels.forEach { label ->
            Text(label, color = GraoText3, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun MarketItem(asset: GraoMarketAssetModel) {
    Row(
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, GraoBorder, RoundedCornerShape(16.dp))
            .background(Brush.linearGradient(listOf(GraoCard2, GraoCard)))
            .padding(horizontal = 16.dp, vertical = 14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .border(1.dp, toneColor(asset.tone).copy(alpha = 0.20f), RoundedCornerShape(12.dp))
                    .background(toneColor(asset.tone).copy(alpha = 0.10f)),
            ) {
                Text(asset.logo, color = toneColor(asset.tone), fontWeight = FontWeight.ExtraBold)
            }
            Column {
                Text(asset.ticker, color = Color.White, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                Text(asset.name, color = GraoText3, style = MaterialTheme.typography.labelSmall)
            }
        }
        Column(horizontalAlignment = Alignment.End) {
            Text(asset.price, color = Color.White, fontWeight = FontWeight.Bold)
            Text(formatPct(asset.changePct), color = if (asset.changePct >= 0) GraoGreen2 else GraoRed, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun AnalisarPrototypeScreen() {
    ScreenHeader("Desempenho Geral", "Mai 2026")
    AccuracyCard()
    StrategyReturnCard()
    MonthlyEvolutionCard()
}

@Composable
private fun AccuracyCard() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .border(1.dp, GraoBorder, RoundedCornerShape(20.dp))
            .background(Brush.linearGradient(listOf(GraoCard2, GraoCard)))
            .padding(20.dp),
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column {
                Text("Taxa de Acerto", color = Color.White, fontWeight = FontWeight.Bold)
                Text("últimas 30 teses", color = GraoText3, style = MaterialTheme.typography.bodySmall)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("68%", color = GraoGreen2, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
                Text("↑ +4pp mês", color = GraoText3, style = MaterialTheme.typography.labelSmall)
            }
        }
        Spacer(Modifier.height(14.dp))
        AnimatedProgress(68, "", GraoTradeStatus.Open)
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            MiniStat("Ganhos", "20", GraoGreen2, Modifier.weight(1f))
            MiniStat("Perdas", "7", GraoRed, Modifier.weight(1f))
            MiniStat("Abertas", "3", GraoText2, Modifier.weight(1f))
        }
    }
}

@Composable
private fun MiniStat(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(Color.White.copy(alpha = 0.03f))
            .padding(10.dp),
    ) {
        Text(value, color = color, fontWeight = FontWeight.ExtraBold)
        Text(label, color = GraoText3, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun StrategyReturnCard() {
    Column(
        verticalArrangement = Arrangement.spacedBy(10.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .border(1.dp, GraoBorder, RoundedCornerShape(20.dp))
            .background(Brush.linearGradient(listOf(GraoCard2, GraoCard)))
            .padding(20.dp),
    ) {
        Text("Retorno por Estratégia", color = Color.White, fontWeight = FontWeight.Bold)
        graoPrototypeStrategyReturns.forEach { item ->
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(item.label, color = Color.White, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                Text(item.value, color = GraoGreen, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            }
            AnimatedProgress(item.pct, "", GraoTradeStatus.Open)
        }
    }
}

@Composable
private fun MonthlyEvolutionCard() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .border(1.dp, GraoBorder, RoundedCornerShape(20.dp))
            .background(Brush.linearGradient(listOf(GraoCard2, GraoCard)))
            .padding(20.dp),
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text("Evolução Mensal", color = Color.White, fontWeight = FontWeight.Bold)
            Text("2026", color = GraoGreen, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(14.dp))
        Bars(graoPrototypeMonthlyBars, listOf("Jan", "Fev", "Mar", "Abr", "Mai"))
    }
}

private fun statusColor(status: GraoTradeStatus): Color = when (status) {
    GraoTradeStatus.Open -> GraoBlue
    GraoTradeStatus.Warn -> GraoGold
    GraoTradeStatus.Invalid -> GraoRed
}

private fun toneColor(tone: GraoTone): Color = when (tone) {
    GraoTone.Green -> GraoGreen
    GraoTone.Red -> GraoRed
    GraoTone.Gold -> GraoGold
    GraoTone.Blue -> GraoBlue
    GraoTone.Purple -> Color(0xFFA78BFA)
    GraoTone.Date -> GraoText2
    GraoTone.Neutral -> GraoText2
    GraoTone.Default -> Color.White
}

private fun formatPct(value: Double): String =
    String.format(ptBr, "%+.2f%%", value)
