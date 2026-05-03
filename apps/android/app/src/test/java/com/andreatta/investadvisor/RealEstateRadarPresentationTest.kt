package com.andreatta.investadvisor

import com.andreatta.investadvisor.ui.screens.RealEstateCandidateSection
import com.andreatta.investadvisor.ui.screens.realEstateCandidateSection
import com.andreatta.investadvisor.ui.screens.realEstateScorePresentation
import org.junit.Assert.assertEquals
import org.junit.Test

class RealEstateRadarPresentationTest {
    @Test
    fun groupsCandidatesByDecisionStage() {
        assertEquals(
            RealEstateCandidateSection.Diligence,
            realEstateCandidateSection("Aberto com pendencias"),
        )
        assertEquals(
            RealEstateCandidateSection.Negotiate,
            realEstateCandidateSection("Em estudo"),
        )
        assertEquals(
            RealEstateCandidateSection.Discarded,
            realEstateCandidateSection("Descartado"),
        )
    }

    @Test
    fun scorePresentationKeepsSimpleDecisionLabels() {
        assertEquals("Forte", realEstateScorePresentation(80).label)
        assertEquals("Atencao", realEstateScorePresentation(60).label)
        assertEquals("Risco", realEstateScorePresentation(30).label)
    }
}
