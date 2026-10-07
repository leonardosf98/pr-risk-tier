import json

from pr_risk_tier.evidence import (
    FileChange,
    FileMix,
    JobResult,
    Size,
    file_mix,
    measure,
    parse_jobs,
    parse_numstat,
    unmatched_patterns,
)
from pr_risk_tier.rules import load_rules

RULES = load_rules(
    """
size_limit = 400
test_paths = ["tests/**", "**/*.spec.ts"]

[[rule]]
id = "docs_only"
tier = 0
paths = ["docs/**", "**/*.md"]

[[rule]]
id = "api_contract"
tier = 2
paths = ["src/api/**", "app/schema/**"]
"""
)


def test_numstat_lines_become_file_changes():
    changes = parse_numstat("10\t2\tsrc/api/a.ts\n\n0\t5\tREADME.md\n")

    assert changes == (
        FileChange("src/api/a.ts", 10, 2, binary=False),
        FileChange("README.md", 0, 5, binary=False),
    )


def test_binary_numstat_line_counts_zero_lines():
    changes = parse_numstat("-\t-\tdocs/logo.png\n3\t1\tsrc/x.ts\n")

    assert changes[0] == FileChange("docs/logo.png", 0, 0, binary=True)
    assert measure(changes, RULES, tier=1).total == 4


def test_size_limit_is_enforced_only_from_tier_two():
    changes = (FileChange("src/x.ts", 300, 150, binary=False),)

    assert measure(changes, RULES, tier=1) == Size(300, 150, 400, enforced=False)
    assert not measure(changes, RULES, tier=1).over_limit
    assert measure(changes, RULES, tier=2).over_limit


def test_size_at_limit_is_not_over():
    changes = (FileChange("src/x.ts", 400, 0, binary=False),)

    assert not measure(changes, RULES, tier=3).over_limit


def test_file_mix_separates_code_tests_and_inert_files():
    paths = [
        "src/api/a.ts",
        "src/views/B.vue",
        "src/views/__x__/B.spec.ts",
        "tests/test_a.py",
        "docs/a.md",
    ]

    assert file_mix(paths, RULES) == FileMix(code=2, tests=2, inert=1)


def test_test_file_inside_contract_folder_counts_as_test():
    assert file_mix(["src/api/a.spec.ts"], RULES) == FileMix(code=0, tests=1, inert=0)


def _jobs_payload(*jobs):
    return json.dumps({"total_count": len(jobs), "jobs": list(jobs)})


def test_completed_jobs_keep_name_conclusion_url_and_failed_steps():
    payload = _jobs_payload(
        {
            "name": "Lint, typecheck, test, audit",
            "status": "completed",
            "conclusion": "failure",
            "html_url": "https://github.com/o/r/actions/runs/1/job/2",
            "steps": [
                {"name": "Unit tests", "conclusion": "success"},
                {"name": "npm audit", "conclusion": "failure"},
            ],
        },
        {
            "name": "Deploy",
            "status": "completed",
            "conclusion": "skipped",
            "html_url": "https://github.com/o/r/actions/runs/1/job/3",
            "steps": [],
        },
    )

    assert parse_jobs(payload) == (
        JobResult(
            "Lint, typecheck, test, audit",
            "failure",
            "https://github.com/o/r/actions/runs/1/job/2",
            ("npm audit",),
        ),
        JobResult("Deploy", "skipped", "https://github.com/o/r/actions/runs/1/job/3", ()),
    )


def test_jobs_still_running_are_ignored():
    payload = _jobs_payload(
        {"name": "Evidence", "status": "in_progress", "conclusion": None, "html_url": "u"},
    )

    assert parse_jobs(payload) == ()


def test_job_without_steps_has_no_failed_steps():
    payload = _jobs_payload(
        {"name": "ci", "status": "completed", "conclusion": "failure", "html_url": "u"},
    )

    assert parse_jobs(payload) == (JobResult("ci", "failure", "u", ()),)


def test_unreadable_jobs_payload_is_unavailable():
    assert parse_jobs("not json") is None
    assert parse_jobs(json.dumps({"message": "Resource not accessible"})) is None
    assert parse_jobs(json.dumps([])) is None


def test_patterns_that_match_no_repository_file_are_reported():
    repo_files = ["docs/a.md", "src/api/a.ts"]

    assert unmatched_patterns(RULES, repo_files) == (("api_contract", "app/schema/**"),)


def test_every_pattern_matching_means_nothing_to_report():
    repo_files = ["docs/a.md", "src/api/a.ts", "app/schema/user.py"]

    assert unmatched_patterns(RULES, repo_files) == ()
