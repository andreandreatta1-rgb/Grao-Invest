from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict


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


class AssistantDecision(TypedDict, total=False):
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


def _read_store(store_path: Path) -> list[AssistantDecision]:
    if not store_path.exists():
        return []
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    decisions: list[AssistantDecision] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        decision_id = item.get("decision_id")
        user_id = item.get("user_id")
        title = item.get("title")
        question = item.get("question")
        if not isinstance(decision_id, str):
            continue
        if not isinstance(user_id, int):
            continue
        if not isinstance(title, str):
            continue
        if not isinstance(question, str):
            continue
        decisions.append(item)  # type: ignore[arg-type]
    return decisions


def _write_store(store_path: Path, decisions: list[AssistantDecision]) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(decisions, ensure_ascii=True, indent=2), encoding="utf-8")


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


def create_decision(
    *,
    store_path: Path,
    user_id: int,
    title: str,
    context: str,
    question: str,
    options: list[dict[str, object]],
    priority: str = "normal",
) -> AssistantDecision:
    now = _utc_now_iso()
    clean_priority: DecisionPriority = "normal"
    if priority in {"low", "normal", "high"}:
        clean_priority = priority  # type: ignore[assignment]
    decision: AssistantDecision = {
        "decision_id": f"DEC-{uuid.uuid4().hex[:10].upper()}",
        "user_id": user_id,
        "title": title.strip()[:160],
        "context": context.strip()[:1000],
        "question": question.strip()[:400],
        "options": _normalize_options(options),
        "priority": clean_priority,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    decisions = _read_store(store_path)
    decisions.insert(0, decision)
    _write_store(store_path, decisions)
    return decision


def decision_inbox_payload(*, store_path: Path, user_id: int) -> dict[str, object]:
    decisions = [
        item
        for item in _read_store(store_path)
        if item.get("user_id") == user_id
    ]
    pending_count = sum(1 for item in decisions if item.get("status") == "pending")
    answered_count = sum(1 for item in decisions if item.get("status") == "answered")
    high_priority_count = sum(
        1
        for item in decisions
        if item.get("status") == "pending" and item.get("priority") == "high"
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
        "decisions": decisions[:50],
    }


def answer_decision(
    *,
    store_path: Path,
    user_id: int,
    decision_id: str,
    option_id: str | None = None,
    free_text: str | None = None,
) -> AssistantDecision:
    decisions = _read_store(store_path)
    clean_option_id = str(option_id or "").strip().upper()
    clean_free_text = str(free_text or "").strip()
    if not clean_option_id and not clean_free_text:
        raise ValueError("Informe uma opcao ou um texto livre para responder.")

    for index, item in enumerate(decisions):
        if item.get("decision_id") != decision_id:
            continue
        if item.get("user_id") != user_id:
            raise ValueError("Decisao nao pertence ao usuario autenticado.")
        options = item.get("options") or []
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
        updated: AssistantDecision = {
            **item,
            "status": "answered",
            "answer": answer,
            "updated_at": now,
        }
        decisions[index] = updated
        _write_store(store_path, decisions)
        return updated
    raise ValueError("Decisao nao encontrada.")


def seed_away_plan_decision(*, store_path: Path, user_id: int) -> AssistantDecision:
    decisions = _read_store(store_path)
    for item in decisions:
        if (
            item.get("user_id") == user_id
            and item.get("status") == "pending"
            and item.get("title") == "Plano para as proximas 5 horas"
        ):
            return item
    return create_decision(
        store_path=store_path,
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
