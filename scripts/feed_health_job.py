from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.audit import record_audit_event
from app.services.feed_health import provider_feed_health, universe_coverage_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Job de monitoramento de saude do feed e cobertura de universo."
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="User ID opcional para trilha de auditoria.",
    )
    parser.add_argument(
        "--stale-threshold-seconds",
        type=int,
        default=1800,
        help="Limite de staleness do ingest para alerta.",
    )
    parser.add_argument(
        "--latency-threshold-seconds",
        type=int,
        default=120,
        help="Limite de lag mercado->ingest para alerta.",
    )
    parser.add_argument(
        "--max-coverage-rows",
        type=int,
        default=100,
        help="Maximo de linhas detalhadas de cobertura.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        providers = provider_feed_health(
            db,
            stale_threshold_seconds=args.stale_threshold_seconds,
            latency_threshold_seconds=args.latency_threshold_seconds,
        )
        coverage = universe_coverage_snapshot(db, max_rows=args.max_coverage_rows)

        alerts = [
            row
            for row in providers
            if row["health_status"] in {"critical", "warning"}
        ]
        if alerts:
            record_audit_event(
                db,
                "market.feed.health.alert",
                {
                    "alert_count": len(alerts),
                    "providers": alerts,
                    "thresholds": {
                        "stale_threshold_seconds": args.stale_threshold_seconds,
                        "latency_threshold_seconds": args.latency_threshold_seconds,
                    },
                },
                args.user_id,
            )
        else:
            record_audit_event(
                db,
                "market.feed.health.ok",
                {
                    "provider_count": len(providers),
                    "thresholds": {
                        "stale_threshold_seconds": args.stale_threshold_seconds,
                        "latency_threshold_seconds": args.latency_threshold_seconds,
                    },
                },
                args.user_id,
            )

    payload = {
        "providers": providers,
        "coverage": coverage,
        "summary": {
            "provider_count": len(providers),
            "alert_count": len(alerts),
            "healthy_count": sum(
                1 for item in providers if item["health_status"] == "healthy"
            ),
        },
        "thresholds": {
            "stale_threshold_seconds": args.stale_threshold_seconds,
            "latency_threshold_seconds": args.latency_threshold_seconds,
        },
    }
    output_path = Path(__file__).resolve().parents[1] / "data" / "feed_health_latest.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {output_path}")
    print(
        "Resumo health: "
        f"providers={payload['summary']['provider_count']} | "
        f"alerts={payload['summary']['alert_count']} | "
        f"healthy={payload['summary']['healthy_count']}"
    )


if __name__ == "__main__":
    main()
