import pytest

from pr_risk_tier.rules import Rule, RulesError, load_rules

VALID = """
size_limit = 400
default_tier = 1
test_paths = ["app/tests/**"]

[[rule]]
id = "docs_only"
tier = 0
paths = ["docs/**", "**/*.md"]

[[rule]]
id = "api_contract"
tier = 2
paths = ["app/schema/**"]
"""


def test_loads_valid_rules():
    rules = load_rules(VALID)

    assert rules.size_limit == 400
    assert rules.default_tier == 1
    assert rules.test_paths == ("app/tests/**",)
    assert rules.rules == (
        Rule(id="docs_only", tier=0, paths=("docs/**", "**/*.md")),
        Rule(id="api_contract", tier=2, paths=("app/schema/**",)),
    )


def test_defaults_when_optional_keys_are_missing():
    rules = load_rules('[[rule]]\nid = "x"\ntier = 3\npaths = ["a/**"]\n')

    assert rules.size_limit == 400
    assert rules.default_tier == 1
    assert rules.test_paths == ()


def test_rejects_rule_without_tier():
    with pytest.raises(RulesError, match="api_contract.*tier"):
        load_rules('[[rule]]\nid = "api_contract"\npaths = ["a/**"]\n')


@pytest.mark.parametrize("value", ["-1", "4", '"2"', "true"])
def test_rejects_tier_outside_range_or_not_integer(value):
    with pytest.raises(RulesError, match="tier"):
        load_rules(f'[[rule]]\nid = "x"\ntier = {value}\npaths = ["a/**"]\n')


def test_rejects_rule_without_paths():
    with pytest.raises(RulesError, match="x.*paths"):
        load_rules('[[rule]]\nid = "x"\ntier = 1\n')


def test_rejects_invalid_toml():
    with pytest.raises(RulesError, match="TOML"):
        load_rules("[[rule]\n")
