import pytest

from pr_risk_tier.globs import matches


@pytest.mark.parametrize(
    ("path", "pattern"),
    [
        ("README.md", "**/*.md"),
        ("docs/a/b.md", "**/*.md"),
        ("docs/a/b.md", "docs/**"),
        ("app/core/auth.py", "app/core/auth.py"),
        ("requirements-dev.txt", "requirements*.txt"),
        ("src/api/__tests__/locations.spec.ts", "**/__tests__/**"),
    ],
)
def test_matches_pattern(path, pattern):
    assert matches(path, pattern)


@pytest.mark.parametrize(
    ("path", "pattern"),
    [
        ("app/x/y.py", "app/*.py"),
        ("docs.md.bak", "**/*.md"),
        ("app/core/auth.py.orig", "app/core/auth.py"),
        ("src/apix/client.ts", "src/api/**"),
        ("requirements/base.txt", "requirements*.txt"),
    ],
)
def test_does_not_match_pattern(path, pattern):
    assert not matches(path, pattern)
