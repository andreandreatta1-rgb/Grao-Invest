package com.andreatta.investadvisor.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

private data class TimeframePlaybook(
    val frame: String,
    val setup: String,
    val entry: String,
    val exit: String,
    val kpi: String,
)

private val MICROTRADE_MATRIX = listOf(
    TimeframePlaybook(
        frame = "1m",
        setup = "Momentum burst",
        entry = "Breakout + volume >= 2x media de 20 candles",
        exit = "Stop -0.40% | alvo +0.60% | timeout 3 candles",
        kpi = "Win rate >= 52% e expectancy liquida > 0",
    ),
    TimeframePlaybook(
        frame = "5m",
        setup = "Pullback em tendencia",
        entry = "Reteste de VWAP/EMA9 com confirmacao",
        exit = "Stop -0.70% | alvo +1.20% | timeout 6 candles",
        kpi = "Profit factor > 1.25 e drawdown controlado",
    ),
    TimeframePlaybook(
        frame = "15m",
        setup = "Range break com follow-through",
        entry = "Fechamento fora da faixa + segunda barra de continuacao",
        exit = "Stop abaixo/acima da faixa | alvo 1.8x risco",
        kpi = "Taxa de falso rompimento < 40%",
    ),
    TimeframePlaybook(
        frame = "1h",
        setup = "Continuacao de tendencia",
        entry = "Alinhamento EMA20 > EMA50 e ADX em alta",
        exit = "Stop tecnico por swing | alvo 2.0x risco",
        kpi = "Expectancy semanal positiva",
    ),
    TimeframePlaybook(
        frame = "4h",
        setup = "Swing curto em cripto lider",
        entry = "Estrutura + fluxo (volume e open interest)",
        exit = "Stop estrutural | alvo progressivo por volatilidade",
        kpi = "Retorno ajustado ao risco > benchmark",
    ),
)

private val SCANNER_RULES = listOf(
    "Filtrar ativos com volume 24h minimo e spread apertado.",
    "Priorizar top liquidez e limitar altcoins de baixa negociacao.",
    "Rankear aceleracao de preco (5m, 15m, 1h) com confirmacao de volume.",
    "Detectar eventos de volatilidade e descartar ativos com slippage alto.",
)

private val RISK_RULES = listOf(
    "Limite de perda diaria: parar ao bater o limite.",
    "Risco por operacao fixo (ex.: 0.5% a 1.0% do capital).",
    "Stop-loss e take-profit obrigatorios em todas as ordens.",
    "Sem aumento de mao apos sequencia de perdas.",
    "Comecar em paper trading antes de capital real.",
)

@Composable
fun MicrotradesPlaybookPanel(modifier: Modifier = Modifier) {
    Column(
        verticalArrangement = Arrangement.spacedBy(10.dp),
        modifier = modifier.fillMaxWidth(),
    ) {
        Card(
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
            ),
        ) {
            Text(
                text = "Microtrades fica separado da carteira principal. Use esta area para validar edge, custo e disciplina operacional.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(12.dp),
            )
        }

        OutlinedCard {
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.padding(12.dp),
            ) {
                Text(
                    text = "Matriz de timeframes",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                MICROTRADE_MATRIX.forEach { row ->
                    TimeframeRow(row)
                }
            }
        }

        OutlinedCard {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(12.dp),
            ) {
                Text(
                    text = "Scanner de oportunidades (cripto 24/7)",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                SCANNER_RULES.forEach { rule ->
                    Text(
                        text = "- $rule",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }

        OutlinedCard {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(12.dp),
            ) {
                Text(
                    text = "Guardrails obrigatorios",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                RISK_RULES.forEach { rule ->
                    Text(
                        text = "- $rule",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
    }
}

@Composable
private fun TimeframeRow(row: TimeframePlaybook) {
    OutlinedCard {
        Column(
            verticalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.padding(10.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = row.frame,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = row.setup,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                )
            }
            Text(
                text = "Entrada: ${row.entry}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                text = "Saida: ${row.exit}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                text = "KPI: ${row.kpi}",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
