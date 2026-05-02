package com.andreatta.investadvisor.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors: ColorScheme = lightColorScheme(
    primary = Color(0xFF0F6B5F),
    onPrimary = Color.White,
    secondary = Color(0xFF4E5E6A),
    tertiary = Color(0xFF8B5E34),
    background = Color(0xFFF7F8FA),
    surface = Color.White,
    error = Color(0xFFB3261E),
)

private val DarkColors: ColorScheme = darkColorScheme(
    primary = Color(0xFF6FD2C3),
    secondary = Color(0xFFB9C8D4),
    tertiary = Color(0xFFE2B37F),
    background = Color(0xFF101416),
    surface = Color(0xFF171D20),
    error = Color(0xFFFFB4AB),
)

@Composable
fun InvestAdvisorTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
