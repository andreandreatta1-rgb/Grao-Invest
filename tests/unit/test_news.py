from __future__ import annotations

from app.services.news import classify_news, compute_anti_hype_score


def test_anti_hype_penalizes_sensational_social_content() -> None:
    credibility, anti_hype = compute_anti_hype_score(
        "PETR4 dispara em segredo imperdivel de ultima chance",
        "social",
    )
    assert credibility == 30.0
    assert anti_hype < 40


def test_classify_news_returns_structured_sentiment() -> None:
    classified = classify_news(
        "PETR4",
        "Petrobras aprova dividendo extraordinario e guidance positivo",
        "official",
    )
    assert classified["sector"] == "energia"
    assert classified["theme"] in {"proventos", "resultados"}
    assert classified["sentiment_label"] == "positive"
    assert float(classified["magnitude_score"]) > 0.3
