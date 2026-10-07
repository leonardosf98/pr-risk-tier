from pr_risk_tier.classify import DEFAULT_REASON_ID, Reason, classify
from pr_risk_tier.rules import load_rules

RULES = load_rules(
    """
default_tier = 1

[[rule]]
id = "docs_only"
tier = 0
paths = ["docs/**", "**/*.md"]

[[rule]]
id = "api_contract"
tier = 2
paths = ["app/schema/**"]

[[rule]]
id = "security_boundary"
tier = 3
paths = ["app/core/auth.py"]
"""
)


def test_docs_only_is_tier_zero():
    result = classify(["docs/a.md", "README.md"], RULES)

    assert result.tier == 0
    assert result.reasons == (Reason("docs_only", 0, ("README.md", "docs/a.md")),)


def test_unmatched_file_falls_back_to_default_tier():
    result = classify(["docs/a.md", "app/services/x.py"], RULES)

    assert result.tier == 1
    assert Reason(DEFAULT_REASON_ID, 1, ("app/services/x.py",)) in result.reasons


def test_contract_file_is_tier_two_with_reason():
    result = classify(["app/schema/location.py"], RULES)

    assert result.tier == 2
    assert result.reasons == (Reason("api_contract", 2, ("app/schema/location.py",)),)


def test_highest_tier_wins_and_all_reasons_are_listed_by_tier():
    result = classify(["app/schema/location.py", "app/core/auth.py", "docs/a.md"], RULES)

    assert result.tier == 3
    assert [reason.rule_id for reason in result.reasons] == [
        "security_boundary",
        "api_contract",
        "docs_only",
    ]


def test_file_matching_several_rules_counts_once_under_the_highest():
    result = classify(["app/schema/README.md"], RULES)

    assert result.tier == 2
    assert result.reasons == (Reason("api_contract", 2, ("app/schema/README.md",)),)


def test_no_files_is_tier_zero_without_reasons():
    result = classify([], RULES)

    assert result.tier == 0
    assert result.reasons == ()
