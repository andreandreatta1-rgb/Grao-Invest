from __future__ import annotations

import pytest
from app.services.utils import anti_recommendation_text, assert_compliant_copy


def test_forbidden_terms_are_removed() -> None:
    text = anti_recommendation_text("Compre agora porque e lucro certo.")
    assert "Compre" not in text
    assert "lucro certo" not in text.lower()
    assert_compliant_copy(text)


def test_guardrail_rejects_forbidden_terms() -> None:
    with pytest.raises(ValueError):
        assert_compliant_copy("Este texto pede para compre PETR4")
