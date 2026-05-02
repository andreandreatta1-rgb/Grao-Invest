from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Literal, TypedDict

from app.models import AssistantDecision as AssistantDecisionRecord
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

DecisionStatus = Literal["pending", "answered", "dismissed"]
DecisionPriority = Literal["low", "normal", "high"]


class DecisionOption(TypedDict):
    option_id: str
    label: str


class DecisionAnswer(TypedDict, total=False):
    option_id: str
    option_label: str
    free_text: str
    answered_at: str


class AssistantDecisionPayload(TypedDict, total=False):
    decision_id: str
    user_id: int
    title: str
    context: str
    question: str
    options: list[DecisionOption]
    priority: DecisionPriority
    status: DecisionStatus
    created_at: str
    updated_at: str
    answer: DecisionAnswer


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _read_json_object(raw_value: str | None) -> dict[str, object]:
    if not raw_value:
        return {}
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _read_options(raw_value: str | None) -> list[DecisionOption]:
    if not raw_value:
        return []
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    options: list[DecisionOption] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        option_id = item.get("option_id")
        label = item.get("label")
        if not isinstance(option_id, str) or not isinstance(label, str):
            continue
        options.append({"option_id": option_id, "label": label})
    return options


def _normalize_options(options: list[dict[str, object]]) -> list[DecisionOption]:
    normalized: list[DecisionOption] = []
    for index, item in enumerate(options):
        option_id = str(item.get("option_id") or chr(65 + index)).strip().upper()
        label = str(item.get("label") or "").strip()
        if not option_id or not label:
            continue
        normalized.append({"option_id": option_id[:12], "label": label[:160]})
    if not normalized:
        raise ValueError("Ao menos uma opcao de decisao e obrigatoria.")
    return normalized[:5]


def _priority(value: str) -> DecisionPriority:
    if value in {"low", "normal", "high"}:
        return value  # type: ignore[return-value]
    return "normal"


def _status(value: str) -> DecisionStatus:
    if value in {"pending", "answered", "dismissed"}:
        return value  # type: ignore[return-value]
    return "pending"


def _decision_to_payload(record: AssistantDecisionRecord) -> AssistantDecisionPayload:
    payload: AssistantDecisionPayload = {
        "decision_id": record.decision_id,
        "user_id": record.user_id,
        "title": record.title,
        "context": record.context,
        "question": record.question,
        "options": _read_options(record.options_json),
        "priority": _priority(record.priority),
        "status": _status(record.status),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    answer = _read_json_object(record.answer_json)
    if answer:
        payload["answer"] = {
            key: str(value)
            for key, value in answer.items()
            if key in {"option_id", "option_label", "free_text", "answered_at"}
        }
    return payload


def create_decision(
    *,
    db: Session,
    user_id: int,
    title: str,
    context: str,
    question: str,
    options: list[dict[str, object]],
    priority: str = "normal",
) -> AssistantDecisionPayload:
    now = _utc_now_iso()
    normalized_options = _normalize_options(options)
    record = AssistantDecisionRecord(
        decision_id=f"DEC-{uuid.uuid4().hex[:10].upper()}",
        user_id=user_id,
        title=title.strip()[:160],
        context=context.strip()[:1000],
        question=question.strip()[:400],
        options_json=json.dumps(normalized_options, ensure_ascii=True),
        priority=_priority(priority),
        status="pending",
        answer_json="{}",
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _decision_to_payload(record)


def decision_inbox_payload(*, db: Session, user_id: int) -> dict[str, object]:
    decisions = list(
        db.scalars(
            select(AssistantDecisionRecord)
            .where(AssistantDecisionRecord.user_id == user_id)
            .order_by(desc(AssistantDecisionRecord.id))
        )
    )
    pending_count = sum(1 for item in decisions if item.status == "pending")
    answered_count = sum(1 for item in decisions if item.status == "answered")
    high_priority_count = sum(
        1 for item in decisions if item.status == "pending" and item.priority == "high"
    )
    return {
        "generated_at": _utc_now_iso(),
        "user_id": user_id,
        "summary": {
            "total_count": len(decisions),
            "pending_count": pending_count,
            "answered_count": answered_count,
            "high_priority_count": high_priority_count,
        },
        "decisions": [_decision_to_payload(item) for item in decisions[:50]],
    }


def answer_decision(
    *,
    db: Session,
    user_id: int,
    decision_id: str,
    option_id: str | None = None,
    free_text: str | None = None,
) -> AssistantDecisionPayload:
    clean_option_id = str(option_id or "").strip().upper()
    clean_free_text = str(free_text or "").strip()
    if not clean_option_id and not clean_free_text:
        raise ValueError("Informe uma opcao ou um texto livre para responder.")

    record = db.scalar(
        select(AssistantDecisionRecord)
        .where(AssistantDecisionRecord.decision_id == decision_id)
        .limit(1)
    )
    if record is None:
        raise ValueError("Decisao nao encontrada.")
    if record.user_id != user_id:
        raise ValueError("Decisao nao pertence ao usuario autenticado.")

    options = _read_options(record.options_json)
    option_label = ""
    if clean_option_id:
        for option in options:
            if option.get("option_id") == clean_option_id:
                option_label = str(option.get("label") or "")
                break
        if not option_label:
            raise ValueError("Opcao de decisao invalida.")

    now = _utc_now_iso()
    answer: DecisionAnswer = {"answered_at": now}
    if clean_option_id:
        answer["option_id"] = clean_option_id
        answer["option_label"] = option_label
    if clean_free_text:
        answer["free_text"] = clean_free_text[:1000]
    record.status = "answered"
    record.answer_json = json.dumps(answer, ensure_ascii=True)
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return _decision_to_payload(record)


def seed_away_plan_decision(*, db: Session, user_id: int) -> AssistantDecisionPayload:
    existing = db.scalar(
        select(AssistantDecisionRecord)
        .where(
            AssistantDecisionRecord.user_id == user_id,
            AssistantDecisionRecord.status == "pending",
            AssistantDecisionRecord.title == "Plano para as proximas 5 horas",
        )
        .order_by(desc(AssistantDecisionRecord.id))
        .limit(1)
    )
    if existing is not None:
        return _decision_to_payload(existing)
    return create_decision(
        db=db,
        user_id=user_id,
        title="Plano para as proximas 5 horas",
        context=(
            "Voce ficara longe do notebook. A ideia e manter o motor trabalhando, "
            "mas pedir sua decisao se aparecer uma escolha com impacto."
        ),
        question="Qual nivel de autonomia voce aprova enquanto acompanha pelo celular?",
        options=[
            {
                "option_id": "A",
                "label": "Rodar monitor intensivo e pedir decisao se houver alerta relevante",
            },
            {
                "option_id": "B",
                "label": "Apenas observar e gerar reporte no final",
            },
            {
                "option_id": "C",
                "label": "Pausar acoes novas; manter somente a app acessivel",
            },
        ],
        priority="high",
    )
