from collections.abc import Iterable
from dataclasses import dataclass

from pr_risk_tier.globs import matches
from pr_risk_tier.rules import Rules

DEFAULT_REASON_ID = "default"


@dataclass(frozen=True)
class Reason:
    rule_id: str
    tier: int
    files: tuple[str, ...]


@dataclass(frozen=True)
class Classification:
    tier: int
    reasons: tuple[Reason, ...]


def classify(files: Iterable[str], rules: Rules) -> Classification:
    grouped: dict[tuple[str, int], list[str]] = {}
    for path in sorted(set(files)):
        grouped.setdefault(_strongest_rule(path, rules), []).append(path)

    reasons = tuple(
        sorted(
            (Reason(rule_id, tier, tuple(paths)) for (rule_id, tier), paths in grouped.items()),
            key=lambda reason: (-reason.tier, reason.rule_id),
        )
    )
    return Classification(tier=max((reason.tier for reason in reasons), default=0), reasons=reasons)


def _strongest_rule(path: str, rules: Rules) -> tuple[str, int]:
    matched = [rule for rule in rules.rules if any(matches(path, p) for p in rule.paths)]
    if not matched:
        return DEFAULT_REASON_ID, rules.default_tier
    strongest = max(matched, key=lambda rule: rule.tier)
    return strongest.id, strongest.tier
