from __future__ import annotations

from datetime import timedelta

from app.models import (
    AlertEvent,
    AlertRule,
    BacktestRun,
    CircuitBreakerState,
    NewsAnalysisSnapshot,
    NewsArticle,
    Signal,
)
from app.services.audit import record_audit_event
from app.services.utils import isoformat, to_json, utc_now
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

ALERT_COOLDOWN_MINUTES = 5
THRESHOLD_DEFAULTS = {
    "signal_confidence": 0.6,
    "anti_hype": 45.0,
    "news_magnitude": 0.75,
    "backtest_return": 0.0,
    "backtest_drawdown": 10.0,
    "backtest_win_rate": 50.0,
}


def _within_cooldown(db: Session, rule_id: int) -> bool:
    latest_event = db.scalar(
        select(AlertEvent)
        .where(AlertEvent.alert_rule_id == rule_id)
        .order_by(desc(AlertEvent.id))
        .limit(1)
    )
    if latest_event is None:
        return False
    now = utc_now()
    try:
        event_time = now.fromisoformat(latest_event.created_at)
    except ValueError:
        return False
    return event_time >= (now - timedelta(minutes=ALERT_COOLDOWN_MINUTES))


def _append_event(
    events: list[AlertEvent],
    *,
    db: Session,
    rule: AlertRule,
    event_type: str,
    instrument: str | None,
    payload: dict[str, object],
) -> None:
    if _within_cooldown(db, rule.id):
        return
    event = AlertEvent(
        user_id=rule.user_id,
        alert_rule_id=rule.id,
        event_type=event_type,
        instrument=instrument,
        payload=to_json(payload),
        created_at=isoformat(utc_now()),
    )
    db.add(event)
    events.append(event)


def create_alert_rule(
    db: Session,
    user_id: int,
    rule_type: str,
    instrument: str | None,
    threshold_value: float | None,
) -> AlertRule:
    default_threshold = THRESHOLD_DEFAULTS.get(rule_type)
    effective_threshold = threshold_value if threshold_value is not None else default_threshold
    rule = AlertRule(
        user_id=user_id,
        rule_type=rule_type,
        instrument=instrument.upper() if instrument else None,
        threshold_value=effective_threshold,
        is_active=True,
        created_at=isoformat(utc_now()),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    record_audit_event(
        db,
        "alerts.rule.created",
        {"rule_type": rule.rule_type, "instrument": rule.instrument},
        user_id,
    )
    return rule


def maybe_emit_signal_alerts(db: Session, signal: Signal) -> list[AlertEvent]:
    rules = list(
        db.scalars(
            select(AlertRule)
            .where(AlertRule.user_id == signal.user_id)
            .where(AlertRule.is_active.is_(True))
            .order_by(desc(AlertRule.id))
        )
    )
    events: list[AlertEvent] = []
    for rule in rules:
        if rule.instrument and rule.instrument != signal.instrument:
            continue
        should_fire = False
        if rule.rule_type == "signal_confidence" and rule.threshold_value is not None:
            should_fire = signal.confidence >= rule.threshold_value
        elif rule.rule_type == "anti_hype" and rule.threshold_value is not None:
            should_fire = signal.anti_hype_score <= rule.threshold_value

        if should_fire:
            _append_event(
                events,
                db=db,
                rule=rule,
                event_type=rule.rule_type,
                instrument=signal.instrument,
                payload={
                    "signal_id": signal.id,
                    "confidence": signal.confidence,
                    "anti_hype_score": signal.anti_hype_score,
                },
            )
    if events:
        db.commit()
    return events


def maybe_emit_circuit_breaker_alert(db: Session, state: CircuitBreakerState) -> list[AlertEvent]:
    rules = list(
        db.scalars(
            select(AlertRule)
            .where(AlertRule.rule_type == "circuit_breaker")
            .where(AlertRule.is_active.is_(True))
        )
    )
    if not rules:
        return []
    events: list[AlertEvent] = []
    for rule in rules:
        if rule.instrument is not None and rule.instrument != state.instrument:
            continue
        _append_event(
            events,
            db=db,
            rule=rule,
            event_type="circuit_breaker",
            instrument=state.instrument,
            payload={"status": state.status, "reason": state.reason},
        )
    if events:
        db.commit()
    return events


def maybe_emit_news_alerts(
    db: Session,
    article: NewsArticle,
    analysis: NewsAnalysisSnapshot,
) -> list[AlertEvent]:
    rules = list(
        db.scalars(
            select(AlertRule)
            .where(AlertRule.rule_type == "news_magnitude")
            .where(AlertRule.is_active.is_(True))
            .order_by(desc(AlertRule.id))
        )
    )
    if not rules:
        return []

    events: list[AlertEvent] = []
    for rule in rules:
        if rule.instrument is not None and rule.instrument != article.instrument:
            continue
        threshold = rule.threshold_value if rule.threshold_value is not None else 0.75
        if analysis.magnitude_score < threshold:
            continue
        _append_event(
            events,
            db=db,
            rule=rule,
            event_type="news_magnitude",
            instrument=article.instrument,
            payload={
                "news_article_id": article.id,
                "headline": article.headline,
                "source_name": article.source_name,
                "source_type": article.source_type,
                "credibility_score": article.credibility_score,
                "anti_hype_score": article.anti_hype_score,
                "magnitude_score": analysis.magnitude_score,
                "sentiment_label": analysis.sentiment_label,
                "model_confidence": analysis.model_confidence,
            },
        )
    if events:
        db.commit()
    return events


def maybe_emit_backtest_alerts(
    db: Session,
    run: BacktestRun,
    validation_snapshot: object,
) -> list[AlertEvent]:
    rules = list(
        db.scalars(
            select(AlertRule)
            .where(AlertRule.user_id == run.user_id)
            .where(
                AlertRule.rule_type.in_(
                    ["backtest_return", "backtest_drawdown", "backtest_win_rate"]
                )
            )
            .where(AlertRule.is_active.is_(True))
            .order_by(desc(AlertRule.id))
        )
    )
    if not rules:
        return []

    events: list[AlertEvent] = []
    for rule in rules:
        if rule.instrument is not None and rule.instrument != run.instrument:
            continue

        threshold = rule.threshold_value if rule.threshold_value is not None else 0.0
        metric_value = 0.0
        should_fire = False
        if rule.rule_type == "backtest_return":
            metric_value = run.total_return_pct
            should_fire = metric_value <= threshold
        elif rule.rule_type == "backtest_drawdown":
            metric_value = run.max_drawdown_pct
            should_fire = metric_value >= threshold
        elif rule.rule_type == "backtest_win_rate":
            metric_value = run.win_rate
            should_fire = metric_value <= threshold

        if should_fire:
            _append_event(
                events,
                db=db,
                rule=rule,
                event_type=rule.rule_type,
                instrument=run.instrument,
                payload={
                    "run_id": run.id,
                    "metric_value": round(metric_value, 4),
                    "threshold": threshold,
                    "summary": run.summary,
                    "validation_snapshot": validation_snapshot,
                },
            )
    if events:
        db.commit()
    return events
