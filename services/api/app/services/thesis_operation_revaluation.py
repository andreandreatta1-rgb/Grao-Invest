from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from app.services.thesis_postmortem import (
    PostmortemShadowProfile,
    candidate_postmortem_conditions,
    is_postmortem_signature_blocked,
    postmortem_shadow_penalty_points,
)


class OperationRevaluation(TypedDict):
    executive_status: str
    executive_status_label: str
    thesis_validity: str
    suggested_action: str
    confidence_initial_pct: float
    confidence_now_pct: float
    confidence_delta_pct: float
    next_trigger: str
    revaluation_reason: str
    learning_signal: str
    risk_flags: list[str]
    postmortem_penalty_points: float
    matched_postmortem_rules: list[str]
    blocked_by_postmortem: bool


def _float_value(item: Mapping[str, object], key: str, fallback: float = 0.0) -> float:
    value = item.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return fallback


def _bool_value(item: Mapping[str, object], key: str, fallback: bool = False) -> bool:
    value = item.get(key)
    if isinstance(value, bool):
        return value
    return fallback


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _status_label(status: str) -> str:
    return {
        "mantida": "Mantida",
        "atencao": "Atencao",
        "revisar_saida": "Revisar saida",
        "invalidada": "Invalidada",
        "encerrada": "Encerrada",
    }.get(status, "Atencao")


def _confirmation_penalty(thesis: Mapping[str, object]) -> tuple[float, list[str]]:
    fundamental_available = _bool_value(thesis, "fundamental_available", True)
    news_available = _bool_value(thesis, "news_available", True)
    support_rate_pct = _float_value(thesis, "support_rate_pct")
    penalty = 0.0
    flags: list[str] = []

    if not fundamental_available and not news_available:
        penalty += 7.0
        flags.append("missing_confirmation_inputs")
    elif not fundamental_available or not news_available:
        penalty += 3.0
        flags.append("partial_confirmation_inputs")

    if support_rate_pct < 35.0:
        penalty += 4.0
        flags.append("low_support_rate_band")
    elif support_rate_pct < 45.0:
        penalty += 2.0
        flags.append("moderate_support_rate_band")

    return penalty, flags


def build_operation_revaluation(
    thesis: Mapping[str, object],
    *,
    latest_price: float,
    monitor_status: str,
    unrealized_financial_pct: float,
    progress_to_target_pct: float,
    distance_to_stop_pct: float,
    postmortem_profile: PostmortemShadowProfile | None = None,
) -> OperationRevaluation:
    confidence_initial = _float_value(thesis, "confidence_tese_pct")
    status_lower = monitor_status.strip().lower()
    risk_flags = sorted(candidate_postmortem_conditions(thesis))
    confirmation_penalty, confirmation_flags = _confirmation_penalty(thesis)
    for flag in confirmation_flags:
        if flag not in risk_flags:
            risk_flags.append(flag)

    postmortem_penalty, matched_rules = postmortem_shadow_penalty_points(
        thesis,
        postmortem_profile,
    )
    blocked_by_postmortem = is_postmortem_signature_blocked(thesis, postmortem_profile)

    market_penalty = 0.0
    confidence_bonus = 0.0
    if status_lower in {"stop_alert", "stop", "invalidated"}:
        market_penalty += 18.0
        risk_flags.append("stop_alert")
    if unrealized_financial_pct <= -2.0:
        market_penalty += 6.0
        risk_flags.append("negative_move_gt_2pct")
    elif unrealized_financial_pct < 0.0:
        market_penalty += 2.0
        risk_flags.append("negative_move")
    if distance_to_stop_pct <= 1.0:
        market_penalty += 5.0
        risk_flags.append("near_or_below_stop")
    if status_lower == "target_hit" or progress_to_target_pct >= 100.0:
        confidence_bonus += 6.0
    elif progress_to_target_pct >= 80.0 and unrealized_financial_pct > 0.0:
        confidence_bonus += 4.0
    elif unrealized_financial_pct > 0.0 and distance_to_stop_pct > 3.0:
        confidence_bonus += 1.0

    total_penalty = confirmation_penalty + postmortem_penalty + market_penalty
    confidence_now = round(
        _clamp(confidence_initial - total_penalty + confidence_bonus, 0.0, 95.0),
        4,
    )
    confidence_delta = round(confidence_now - confidence_initial, 4)

    closed_statuses = {"closed", "encerrada", "finished", "exited"}
    if status_lower in closed_statuses:
        executive_status = "encerrada"
    elif status_lower == "target_hit" or progress_to_target_pct >= 85.0:
        executive_status = "revisar_saida"
    elif (
        status_lower == "stop_alert"
        or blocked_by_postmortem
        or confidence_now < 45.0
        or (
            unrealized_financial_pct <= -2.0
            and "missing_confirmation_inputs" in risk_flags
        )
    ):
        executive_status = "invalidada"
    elif confidence_now < 58.0 or unrealized_financial_pct < 0.0 or distance_to_stop_pct <= 2.0:
        executive_status = "atencao"
    else:
        executive_status = "mantida"

    if executive_status == "encerrada":
        thesis_validity = "encerrada"
        suggested_action = "gerar_pos_morte"
        next_trigger = "Registrar resultado final e transformar o erro/acerto em regra."
        reason = "Operacao encerrada; a prioridade agora e pos-morte."
    elif executive_status == "revisar_saida":
        thesis_validity = "valida_com_saida_proxima"
        suggested_action = "avaliar_realizacao_parcial_ou_total"
        next_trigger = "Preco chegou perto do alvo; revisar saida planejada antes de devolver ganho."
        reason = "Tese evoluiu a favor e esta perto do alvo ou ja atingiu o alvo."
    elif executive_status == "invalidada":
        thesis_validity = "perdeu_validade"
        suggested_action = "encerrar_ou_reduzir_risco"
        next_trigger = "Preco/confirmacoes romperam o limite de risco; nao aumentar exposicao."
        reason = "Risco superou a tese inicial: stop, baixa confirmacao ou aprendizado negativo."
    elif executive_status == "atencao":
        thesis_validity = "valida_com_ressalvas"
        suggested_action = "manter_com_alerta"
        next_trigger = "Reavaliar na proxima barra; se piorar, reduzir risco."
        reason = "Tese segue viva, mas preco, distancia do stop ou confianca deterioraram."
    else:
        thesis_validity = "valida"
        suggested_action = "manter_monitoramento"
        next_trigger = "Manter ate alvo/stop ou ate surgir dado contrario relevante."
        reason = "Preco, risco e confirmacoes ainda sustentam a tese."

    if matched_rules or blocked_by_postmortem:
        learning_signal = "Aplicar penalidade aprendida no pos-morte antes de repetir padrao."
    elif executive_status == "invalidada":
        learning_signal = "Transformar invalidacao em regra para reduzir entradas semelhantes."
    elif executive_status == "revisar_saida":
        learning_signal = "Priorizar disciplina de saida quando a tese ja entregou boa parte do alvo."
    elif executive_status == "atencao":
        learning_signal = "Acompanhar se a deterioracao vira padrao recorrente."
    else:
        learning_signal = "Sem mudanca relevante na politica; manter criterio atual."

    return {
        "executive_status": executive_status,
        "executive_status_label": _status_label(executive_status),
        "thesis_validity": thesis_validity,
        "suggested_action": suggested_action,
        "confidence_initial_pct": round(confidence_initial, 4),
        "confidence_now_pct": confidence_now,
        "confidence_delta_pct": confidence_delta,
        "next_trigger": next_trigger,
        "revaluation_reason": reason,
        "learning_signal": learning_signal,
        "risk_flags": sorted(set(risk_flags)),
        "postmortem_penalty_points": round(postmortem_penalty, 4),
        "matched_postmortem_rules": matched_rules,
        "blocked_by_postmortem": blocked_by_postmortem,
    }
