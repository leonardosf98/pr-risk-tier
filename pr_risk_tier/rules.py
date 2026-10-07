import tomllib
from dataclasses import dataclass

TIERS = range(4)


class RulesError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    id: str
    tier: int
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Rules:
    rules: tuple[Rule, ...]
    size_limit: int = 400
    default_tier: int = 1
    test_paths: tuple[str, ...] = ()


def load_rules(text: str) -> Rules:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise RulesError(f"O arquivo de regras não é TOML válido: {error}") from error

    default_tier = data.get("default_tier", 1)
    if not _is_tier(default_tier):
        raise RulesError("'default_tier' deve ser um inteiro de 0 a 3.")

    size_limit = data.get("size_limit", 400)
    if not _is_int(size_limit) or size_limit <= 0:
        raise RulesError("'size_limit' deve ser um inteiro positivo.")

    return Rules(
        rules=tuple(
            _parse_rule(raw, position) for position, raw in enumerate(data.get("rule", []))
        ),
        size_limit=size_limit,
        default_tier=default_tier,
        test_paths=_string_tuple(data.get("test_paths", []), "'test_paths'"),
    )


def _parse_rule(raw: dict, position: int) -> Rule:
    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not rule_id:
        raise RulesError(f"Regra #{position + 1}: campo 'id' ausente.")
    if "tier" not in raw:
        raise RulesError(f"Regra '{rule_id}': campo 'tier' ausente.")
    if not _is_tier(raw["tier"]):
        raise RulesError(f"Regra '{rule_id}': 'tier' deve ser um inteiro de 0 a 3.")
    paths = _string_tuple(raw.get("paths", []), f"Regra '{rule_id}': 'paths'")
    if not paths:
        raise RulesError(f"Regra '{rule_id}': 'paths' deve ter ao menos um padrão.")
    return Rule(id=rule_id, tier=raw["tier"], paths=paths)


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RulesError(f"{label} deve ser uma lista de textos.")
    return tuple(value)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_tier(value: object) -> bool:
    return _is_int(value) and value in TIERS
