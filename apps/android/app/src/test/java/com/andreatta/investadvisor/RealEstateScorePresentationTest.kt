package com.andreatta.investadvisor

import com.andreatta.investadvisor.ui.screens.RealEstateScoreTone
import com.andreatta.investadvisor.ui.screens.realEstateScorePresentation
import org.junit.Assert.assertEquals
import org.junit.Test

class RealEstateScorePresentationTest {
    @Test
    fun classifiesScoreForVisualEmphasis() {
        assertEquals(RealEstateScoreTone.Strong, realEstateScorePresentation(88).tone)
        assertEquals(RealEstateScoreTone.Watch, realEstateScorePresentation(62).tone)
        assertEquals(RealEstateScoreTone.Risk, realEstateScorePresentation(32).tone)
    }

    @Test
    fun clampsScoreBeforeFormatting() {
        assertEquals("100", realEstateScorePresentation(140).scoreText)
        assertEquals("0", realEstateScorePresentation(-10).scoreText)
    }
}
