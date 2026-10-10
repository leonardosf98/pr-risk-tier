import argparse
import sys
from pathlib import Path

from pr_risk_tier.agent_block import check_invariants, parse_agent_block
from pr_risk_tier.classify import classify
from pr_risk_tier.evidence import (
    Evidence,
    file_mix,
    measure,
    parse_jobs,
    parse_numstat,
    unmatched_patterns,
)
from pr_risk_tier.render import render_comment
from pr_risk_tier.rules import RulesError, load_rules

EVIDENCE_ERROR = 1
CONFIG_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr_risk_tier")
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--numstat", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--repo-files", type=Path)
    parser.add_argument("--body", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Arquivo de regras não encontrado: {args.rules}", file=sys.stderr)
        return CONFIG_ERROR
    except RulesError as error:
        print(f"{args.rules}: {error}", file=sys.stderr)
        return CONFIG_ERROR

    changes = parse_numstat(args.numstat.read_text(encoding="utf-8"))
    paths = [change.path for change in changes]
    classification = classify(paths, rules)
    agent = parse_agent_block(_read_optional(args.body))
    checks = (
        check_invariants(agent.report.invariants, args.repo_root) if agent and agent.report else ()
    )
    evidence = Evidence(
        size=measure(changes, rules, classification.tier),
        mix=file_mix(paths, rules),
        jobs=_read_jobs(args.jobs),
        unmatched=_unmatched(rules, args.repo_files),
        agent=agent,
        invariant_checks=checks,
    )
    args.output.write_text(render_comment(classification, rules, evidence), encoding="utf-8")

    problems = [*(agent.errors if agent else ()), *_invariant_problems(checks)]
    for problem in problems:
        print(f"::error::pr-risk-tier: {problem}", file=sys.stderr)
    return EVIDENCE_ERROR if problems else 0


def _read_optional(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _invariant_problems(checks) -> list[str]:
    return [
        f"invariante '{check.invariant.rule}' cita `{check.invariant.test}`: {check.problem}"
        for check in checks
        if check.problem is not None
    ]


def _read_jobs(path: Path | None):
    if path is None or not path.is_file():
        return None
    return parse_jobs(path.read_text(encoding="utf-8"))


def _unmatched(rules, path: Path | None):
    if path is None or not path.is_file():
        return ()
    return unmatched_patterns(rules, path.read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    sys.exit(main())
