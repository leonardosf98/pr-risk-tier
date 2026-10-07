import argparse
import sys
from pathlib import Path

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

CONFIG_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr_risk_tier")
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--numstat", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--repo-files", type=Path)
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
    evidence = Evidence(
        size=measure(changes, rules, classification.tier),
        mix=file_mix(paths, rules),
        jobs=_read_jobs(args.jobs),
        unmatched=_unmatched(rules, args.repo_files),
    )
    args.output.write_text(render_comment(classification, rules, evidence), encoding="utf-8")
    return 0


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
