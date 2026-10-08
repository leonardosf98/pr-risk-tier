import json
from collections.abc import Iterable
from dataclasses import dataclass

from pr_risk_tier.classify import strongest_rule
from pr_risk_tier.globs import matches
from pr_risk_tier.rules import Rules

ENFORCED_FROM_TIER = 2


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int
    deleted: int
    binary: bool


@dataclass(frozen=True)
class Size:
    added: int
    deleted: int
    limit: int
    enforced: bool

    @property
    def total(self) -> int:
        return self.added + self.deleted

    @property
    def over_limit(self) -> bool:
        return self.enforced and self.total > self.limit


@dataclass(frozen=True)
class FileMix:
    code: int
    tests: int
    inert: int


@dataclass(frozen=True)
class JobResult:
    name: str
    conclusion: str
    url: str
    failed_steps: tuple[str, ...]


@dataclass(frozen=True)
class Evidence:
    size: Size
    mix: FileMix
    jobs: tuple[JobResult, ...] | None
    unmatched: tuple[tuple[str, str], ...] = ()


def parse_numstat(text: str) -> tuple[FileChange, ...]:
    changes = []
    for line in text.splitlines():
        if not line.strip():
            continue
        added, deleted, path = line.split("\t", 2)
        binary = added == "-"
        changes.append(
            FileChange(path, 0 if binary else int(added), 0 if binary else int(deleted), binary)
        )
    return tuple(changes)


def measure(changes: Iterable[FileChange], rules: Rules, tier: int) -> Size:
    changes = tuple(changes)
    return Size(
        added=sum(change.added for change in changes),
        deleted=sum(change.deleted for change in changes),
        limit=rules.size_limit,
        enforced=tier >= ENFORCED_FROM_TIER,
    )


def file_mix(paths: Iterable[str], rules: Rules) -> FileMix:
    code = tests = inert = 0
    for path in paths:
        if any(matches(path, pattern) for pattern in rules.test_paths):
            tests += 1
        elif strongest_rule(path, rules)[1] == 0:
            inert += 1
        else:
            code += 1
    return FileMix(code=code, tests=tests, inert=inert)


def parse_jobs(text: str) -> tuple[JobResult, ...] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        return None
    return tuple(
        JobResult(
            name=job["name"],
            conclusion=job["conclusion"],
            url=job["html_url"],
            failed_steps=tuple(
                step["name"] for step in job.get("steps", []) if step["conclusion"] == "failure"
            ),
        )
        for job in data["jobs"]
        if job.get("status") == "completed"
    )


def unmatched_patterns(rules: Rules, repo_files: Iterable[str]) -> tuple[tuple[str, str], ...]:
    repo_files = tuple(repo_files)
    return tuple(
        (rule.id, pattern)
        for rule in rules.rules
        for pattern in rule.paths
        if not any(matches(path, pattern) for path in repo_files)
    )
