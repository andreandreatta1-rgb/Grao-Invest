from __future__ import annotations

from datetime import datetime


def _is_expected_type(value: object, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "null":
        return value is None
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    raise AssertionError(f"Tipo de schema nao suportado no helper: {expected_type}")


def _assert_type(value: object, raw_type: object, key: str) -> None:
    if isinstance(raw_type, str):
        assert _is_expected_type(value, raw_type), f"Campo {key} com tipo invalido"
        return
    if isinstance(raw_type, list):
        assert any(_is_expected_type(value, item) for item in raw_type), (
            f"Campo {key} com tipo invalido para uniao {raw_type}"
        )
        return
    raise AssertionError(f"Definicao de tipo invalida no schema para {key}")


def _assert_datetime(value: str, key: str) -> None:
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise AssertionError(f"Campo {key} nao esta em formato date-time ISO 8601") from exc


def assert_payload_matches_schema(payload: dict[str, object], schema: dict[str, object]) -> None:
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    additional_properties = schema.get("additionalProperties", True)

    assert required.issubset(set(payload.keys())), "Payload nao contem todos os campos obrigatorios"
    if additional_properties is False:
        allowed = set(properties.keys())
        unexpected = set(payload.keys()) - allowed
        assert not unexpected, (
            "Payload contem campos nao previstos no schema: "
            f"{sorted(unexpected)}"
        )

    for key, rules in properties.items():
        if key not in payload:
            continue
        value = payload[key]
        rule_dict: dict[str, object] = rules if isinstance(rules, dict) else {}

        if "const" in rule_dict:
            assert value == rule_dict["const"], f"Campo {key} diverge do valor constante esperado"

        if "type" in rule_dict:
            _assert_type(value, rule_dict["type"], key)

        if value is None:
            continue

        if "minLength" in rule_dict and isinstance(value, str):
            assert len(value) >= int(rule_dict["minLength"]), f"Campo {key} abaixo do minLength"
        if "minimum" in rule_dict and isinstance(value, (int, float)):
            assert float(value) >= float(rule_dict["minimum"]), f"Campo {key} abaixo do minimo"
        if "exclusiveMinimum" in rule_dict and isinstance(value, (int, float)):
            assert float(value) > float(rule_dict["exclusiveMinimum"]), (
                f"Campo {key} abaixo do exclusiveMinimum"
            )
        if rule_dict.get("format") == "date-time" and isinstance(value, str):
            _assert_datetime(value, key)
