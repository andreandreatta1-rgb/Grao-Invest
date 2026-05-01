from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.services.thesis_policy import (
    ThesisPolicyState,
    load_policy_state,
    save_policy_state,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa ciclo shadow da politica de tese (A/B + verificacao de estabilidade) "
            "e promove politica automaticamente quando atingir criterios definidos."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--instruments",
        type=str,
        default="",
        help="Lista separada por virgula de instrumentos para o ciclo.",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=12,
        help="Janela de barras do experimento A/B.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=1200,
        help="Quantidade maxima de teses candidatas no A/B.",
    )
    parser.add_argument(
        "--shadow-policy",
        type=str,
        default="anti_blindspot_v3_soft",
        help="Politica candidata em shadow.",
    )
    parser.add_argument(
        "--min-discovery-pct",
        type=float,
        default=50.0,
        help="Discovery minimo (%%) para considerar ciclo aprovado.",
    )
    parser.add_argument(
        "--min-success-uplift-pp",
        type=float,
        default=10.0,
        help="Uplift minimo de success rate (p.p.) para ciclo aprovado.",
    )
    parser.add_argument(
        "--min-selected-count",
        type=int,
        default=50,
        help="Quantidade minima de teses selecionadas para ciclo aprovado.",
    )
    parser.add_argument(
        "--required-stable-cycles",
        type=int,
        default=2,
        help="Quantidade de ciclos aprovados consecutivos para promover politica.",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("data/thesis_policy_state.json"),
        help="Arquivo de estado da politica (json).",
    )
    parser.add_argument(
        "--ab-output-file",
        type=Path,
        default=Path("data/thesis_ab_experiment_latest.json"),
        help="Arquivo de saida do experimento A/B (json).",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/thesis_shadow_cycle_latest.json"),
        help="Arquivo de saida consolidado do ciclo shadow (json).",
    )
    return parser.parse_args()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _run_ab_experiment(
    *,
    repo_root: Path,
    user_id: int,
    instruments_raw: str,
    horizon_bars: int,
    max_candidates: int,
    output_file: Path,
) -> None:
    script_path = Path(__file__).resolve().parent / "run_thesis_ab_experiment.py"
    command = [
        sys.executable,
        str(script_path),
        "--user-id",
        str(user_id),
        "--horizon-bars",
        str(horizon_bars),
        "--max-candidates",
        str(max_candidates),
        "--output-file",
        str(output_file),
    ]
    instruments = instruments_raw.strip()
    if instruments:
        command.extend(["--instruments", instruments])
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = (
            "Falha ao executar run_thesis_ab_experiment.py.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        raise SystemExit(message)


def _float_value(payload: dict[str, object], key: str, fallback: float = 0.0) -> float:
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return fallback


def _int_value(payload: dict[str, object], key: str, fallback: int = 0) -> int:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return fallback


def _update_state(
    *,
    state: ThesisPolicyState,
    shadow_policy: str,
    run_at: str,
    evaluated_candidates: int,
    selected_count: int,
    success_rate_pct: float,
    discovery_rate_pct: float,
    success_uplift_pp: float,
    discovery_delta_pp: float,
    passed: bool,
    min_discovery_pct: float,
    min_success_uplift_pp: float,
    min_selected_count: int,
    required_stable_cycles: int,
) -> tuple[ThesisPolicyState, bool]:
    already_promoted = state["active_policy"] == shadow_policy
    if state["shadow_policy"] != shadow_policy:
        state["stable_pass_count"] = 0

    state["shadow_policy"] = shadow_policy
    state["shadow_status"] = "promoted" if already_promoted else "running"
    state["promotion_criteria"] = {
        "min_discovery_pct": min_discovery_pct,
        "min_success_uplift_pp": min_success_uplift_pp,
        "min_selected_count": min_selected_count,
        "required_stable_cycles": required_stable_cycles,
    }

    if passed:
        state["stable_pass_count"] += 1
    else:
        state["stable_pass_count"] = 0

    state["cycle_history"].append(
        {
            "run_at": run_at,
            "shadow_policy": shadow_policy,
            "evaluated_candidates": evaluated_candidates,
            "selected_count": selected_count,
            "success_rate_pct": round(success_rate_pct, 4),
            "discovery_rate_pct": round(discovery_rate_pct, 4),
            "success_uplift_pp": round(success_uplift_pp, 4),
            "discovery_delta_pp": round(discovery_delta_pp, 4),
            "passed": passed,
        }
    )
    state["cycle_history"] = state["cycle_history"][-50:]

    promoted_now = False
    if (
        state["stable_pass_count"] >= required_stable_cycles
        and state["active_policy"] != shadow_policy
    ):
        state["active_policy"] = shadow_policy
        state["shadow_status"] = "promoted"
        promoted_now = True

    state["updated_at"] = run_at
    return state, promoted_now


def main() -> None:
    args = parse_args()
    if args.horizon_bars < 3:
        raise SystemExit("--horizon-bars deve ser maior ou igual a 3.")
    if args.max_candidates <= 0:
        raise SystemExit("--max-candidates deve ser maior que zero.")
    if args.min_selected_count <= 0:
        raise SystemExit("--min-selected-count deve ser maior que zero.")
    if args.required_stable_cycles <= 0:
        raise SystemExit("--required-stable-cycles deve ser maior que zero.")

    repo_root = Path(__file__).resolve().parents[1]
    ab_output_file = args.ab_output_file
    if not ab_output_file.is_absolute():
        ab_output_file = repo_root / ab_output_file
    state_file = args.state_file
    if not state_file.is_absolute():
        state_file = repo_root / state_file
    output_file = args.output_file
    if not output_file.is_absolute():
        output_file = repo_root / output_file

    _run_ab_experiment(
        repo_root=repo_root,
        user_id=args.user_id,
        instruments_raw=args.instruments,
        horizon_bars=args.horizon_bars,
        max_candidates=args.max_candidates,
        output_file=ab_output_file,
    )

    ab_payload = json.loads(ab_output_file.read_text(encoding="utf-8"))
    variants_raw = ab_payload.get("variants")
    comparison_raw = ab_payload.get("comparison")
    if not isinstance(variants_raw, dict) or not isinstance(comparison_raw, dict):
        raise SystemExit("Arquivo de A/B invalido: campos variants/comparison ausentes.")

    baseline_raw = variants_raw.get("baseline")
    shadow_raw = variants_raw.get(args.shadow_policy)
    vs_baseline_raw = comparison_raw.get("vs_baseline")
    if not isinstance(baseline_raw, dict) or not isinstance(shadow_raw, dict):
        raise SystemExit("Politica baseline/shadow nao encontrada no resultado A/B.")
    if not isinstance(vs_baseline_raw, dict):
        raise SystemExit("Comparativo vs_baseline ausente no resultado A/B.")
    shadow_vs_baseline = vs_baseline_raw.get(args.shadow_policy)
    if not isinstance(shadow_vs_baseline, dict):
        raise SystemExit("Comparativo da politica shadow nao encontrado no resultado A/B.")

    evaluated_candidates = _int_value(ab_payload.get("meta", {}), "evaluated_candidates")
    if evaluated_candidates <= 0:
        evaluated_candidates = _int_value(
            {"evaluated_candidates": _int_value(baseline_raw, "selected_count")},
            "evaluated_candidates",
        )

    shadow_selected_count = _int_value(shadow_raw, "selected_count")
    shadow_success_rate_pct = _float_value(shadow_raw, "success_rate_pct")
    shadow_discovery_rate_pct = _float_value(shadow_raw, "discovery_rate_pct")
    success_uplift_pp = _float_value(shadow_vs_baseline, "success_rate_uplift_pp")
    discovery_delta_pp = _float_value(shadow_vs_baseline, "discovery_rate_delta_pp")
    baseline_success_rate_pct = _float_value(baseline_raw, "success_rate_pct")
    baseline_discovery_rate_pct = _float_value(baseline_raw, "discovery_rate_pct")

    state_before = load_policy_state(state_file)
    active_before = state_before["active_policy"]
    evaluation_mode = "candidate"
    maintenance_min_discovery_pct = min(
        args.min_discovery_pct,
        max(30.0, baseline_discovery_rate_pct * 0.9),
    )
    maintenance_min_success_pct = max(0.0, baseline_success_rate_pct - 2.0)
    if active_before == args.shadow_policy:
        evaluation_mode = "maintenance"
        passed = (
            shadow_discovery_rate_pct >= maintenance_min_discovery_pct
            and shadow_success_rate_pct >= maintenance_min_success_pct
            and shadow_selected_count >= args.min_selected_count
        )
    else:
        passed = (
            shadow_discovery_rate_pct >= args.min_discovery_pct
            and success_uplift_pp >= args.min_success_uplift_pp
            and shadow_selected_count >= args.min_selected_count
        )

    run_at = _utc_now_iso()
    state = state_before
    state, promoted_now = _update_state(
        state=state,
        shadow_policy=args.shadow_policy,
        run_at=run_at,
        evaluated_candidates=evaluated_candidates,
        selected_count=shadow_selected_count,
        success_rate_pct=shadow_success_rate_pct,
        discovery_rate_pct=shadow_discovery_rate_pct,
        success_uplift_pp=success_uplift_pp,
        discovery_delta_pp=discovery_delta_pp,
        passed=passed,
        min_discovery_pct=args.min_discovery_pct,
        min_success_uplift_pp=args.min_success_uplift_pp,
        min_selected_count=args.min_selected_count,
        required_stable_cycles=args.required_stable_cycles,
    )
    save_policy_state(state, state_file)

    output_payload = {
        "generated_at": run_at,
        "shadow_policy": args.shadow_policy,
        "ab_output_file": str(ab_output_file),
        "state_file": str(state_file),
        "baseline": {
            "success_rate_pct": round(baseline_success_rate_pct, 4),
            "discovery_rate_pct": round(baseline_discovery_rate_pct, 4),
        },
        "shadow_metrics": {
            "selected_count": shadow_selected_count,
            "success_rate_pct": round(shadow_success_rate_pct, 4),
            "discovery_rate_pct": round(shadow_discovery_rate_pct, 4),
            "success_uplift_pp": round(success_uplift_pp, 4),
            "discovery_delta_pp": round(discovery_delta_pp, 4),
            "evaluated_candidates": evaluated_candidates,
        },
        "promotion": {
            "passed_cycle": passed,
            "promoted_now": promoted_now,
            "evaluation_mode": evaluation_mode,
            "active_policy_after_cycle": state["active_policy"],
            "shadow_status": state["shadow_status"],
            "stable_pass_count": state["stable_pass_count"],
            "required_stable_cycles": args.required_stable_cycles,
            "criteria": state["promotion_criteria"],
            "effective_thresholds": {
                "min_selected_count": args.min_selected_count,
                "min_discovery_pct": (
                    maintenance_min_discovery_pct
                    if evaluation_mode == "maintenance"
                    else args.min_discovery_pct
                ),
                "min_success_uplift_pp": (
                    args.min_success_uplift_pp
                    if evaluation_mode == "candidate"
                    else 0.0
                ),
                "min_success_rate_pct": (
                    maintenance_min_success_pct
                    if evaluation_mode == "maintenance"
                    else 0.0
                ),
            },
        },
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(output_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    print(f"Arquivo de estado atualizado: {state_file}")
    print(f"Arquivo de ciclo shadow: {output_file}")
    print(
        "Resumo shadow: "
        f"policy={args.shadow_policy} | "
        f"baseline_success={baseline_success_rate_pct:.4f}% | "
        f"shadow_success={shadow_success_rate_pct:.4f}% | "
        f"baseline_discovery={baseline_discovery_rate_pct:.4f}% | "
        f"shadow_discovery={shadow_discovery_rate_pct:.4f}% | "
        f"stable={state['stable_pass_count']}/{args.required_stable_cycles} | "
        f"active_policy={state['active_policy']}"
    )


if __name__ == "__main__":
    main()
