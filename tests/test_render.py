from pr_risk_tier.evidence import Evidence, FileMix, JobResult, Size

from pr_risk_tier.classify import DEFAULT_REASON_ID, Classification, Reason
from pr_risk_tier.render import MARKER, render_comment
from pr_risk_tier.rules import load_rules

RULES = load_rules(
    """
size_limit = 400

[[rule]]
id = "docs_only"
tier = 0
paths = ["**/*.md"]

[[rule]]
id = "api_contract"
tier = 2
paths = ["src/api/**"]

[[rule]]
id = "security_boundary"
tier = 3
paths = ["src/auth/**"]
"""
)

PASSING_JOB = JobResult("Lint and test", "success", "https://ci/1", ())
SMALL_DIFF = Size(10, 2, 400, enforced=False)
CODE_AND_TEST = FileMix(code=1, tests=1, inert=0)


def _evidence(
    *,
    size=SMALL_DIFF,
    mix=CODE_AND_TEST,
    jobs=(PASSING_JOB,),
    unmatched=(),
):
    return Evidence(size=size, mix=mix, jobs=jobs, unmatched=unmatched)


def _render(classification, **evidence):
    return render_comment(classification, RULES, _evidence(**evidence))


def _section(comment, title):
    start = comment.index(title)
    end = comment.find("\n### ", start + 1)
    return comment[start : end if end != -1 else len(comment)]


def test_comment_starts_with_marker():
    comment = _render(Classification(0, ()))

    assert comment.startswith(MARKER + "\n")


def test_header_shows_tier_and_label():
    comment = _render(Classification(2, (Reason("api_contract", 2, ("a.py",)),)))

    assert "## 📦 Pacote de evidências — Tier 2 · contrato ou dados persistidos" in comment


def test_sections_follow_the_evidence_package_order():
    comment = _render(Classification(3, (Reason("security_boundary", 3, ("src/auth/a.ts",)),)))

    positions = [
        comment.index(title)
        for title in (
            "### Por que tier 3",
            "### Evidência",
            "### Incertezas",
            "### Revisão sugerida",
        )
    ]
    assert positions == sorted(positions)
    assert "rodar localmente" in _section(comment, "### Revisão sugerida")


def test_boundary_table_lists_touched_and_untouched_rules():
    comment = _render(
        Classification(
            3,
            (
                Reason("security_boundary", 3, ("src/auth/a.ts", "src/auth/b.ts")),
                Reason("docs_only", 0, ("README.md",)),
            ),
        )
    )

    section = _section(comment, "### Por que tier 3")
    assert "| Fronteira | Tier | Arquivos alterados |" in section
    assert "| `security_boundary` | 3 | `src/auth/a.ts`, `src/auth/b.ts` |" in section
    assert "| `api_contract` | 2 | — |" in section
    assert "| `docs_only` | 0 | `README.md` |" in section
    assert section.index("security_boundary") < section.index("api_contract")


def test_default_reason_row_is_explained_in_portuguese():
    comment = _render(Classification(1, (Reason(DEFAULT_REASON_ID, 1, ("x.py",)),)))

    assert "| sem regra específica | 1 | `x.py` |" in comment


def test_long_file_lists_are_truncated():
    files = tuple(f"docs/{index}.md" for index in range(8))
    comment = _render(Classification(0, (Reason("docs_only", 0, files),)))

    assert "`docs/4.md` e mais 3 |" in comment
    assert "`docs/5.md`" not in comment


def test_empty_pull_request_says_no_files():
    comment = _render(Classification(0, ()), mix=FileMix(0, 0, 0), size=Size(0, 0, 400, False))

    assert "Nenhum arquivo alterado." in comment


def test_ci_jobs_show_conclusion_and_failed_step_with_log_link():
    failing = JobResult("Lint, typecheck, test, audit", "failure", "https://ci/2", ("npm audit",))
    skipped = JobResult("Deploy", "skipped", "https://ci/3", ())
    comment = _render(Classification(1, ()), jobs=(PASSING_JOB, failing, skipped))

    section = _section(comment, "### Evidência")
    assert "| CI · Lint and test | ✅ passou |" in section
    assert (
        "| CI · Lint, typecheck, test, audit | ❌ falhou em `npm audit` · [log](https://ci/2) |"
        in section
    )
    assert "| CI · Deploy | ⏭️ pulado |" in section


def test_unavailable_ci_is_flagged_as_unknown():
    comment = _render(Classification(1, ()), jobs=None)

    assert "| CI | ⚠️ indisponível |" in _section(comment, "### Evidência")
    assert "`actions: read`" in _section(comment, "### Incertezas")


def test_failed_ci_is_flagged_as_unknown():
    failing = JobResult("ci", "failure", "https://ci/2", ("npm audit",))
    comment = _render(Classification(1, ()), jobs=(failing,))

    assert "CI com falha em `ci` (`npm audit`)" in _section(comment, "### Incertezas")


def test_size_within_enforced_limit():
    comment = _render(Classification(2, ()), size=Size(131, 1, 400, enforced=True))

    assert "| Tamanho do diff | 132 linhas (+131 −1) · limite do tier 2: 400 ✅ |" in comment


def test_size_over_enforced_limit_is_flagged():
    comment = _render(Classification(3, ()), size=Size(500, 12, 400, enforced=True))

    assert "512 linhas (+500 −12) · ⚠️ acima do limite do tier 3: 400" in comment
    assert "considere fatiar" in _section(comment, "### Incertezas")


def test_size_without_limit_says_so():
    comment = _render(Classification(1, ()), size=Size(900, 0, 400, enforced=False))

    assert "900 linhas (+900 −0) · tier 1 não tem limite rígido" in comment
    assert "fatiar" not in comment


def test_file_mix_row():
    comment = _render(Classification(1, ()), mix=FileMix(code=2, tests=0, inert=4))

    assert "| Arquivos | 2 de código · 0 de teste · 4 sem efeito em execução |" in comment


def test_code_without_tests_is_flagged():
    comment = _render(Classification(1, ()), mix=FileMix(code=2, tests=0, inert=0))

    assert "2 arquivo(s) de código sem nenhum teste alterado" in _section(comment, "### Incertezas")


def test_unmatched_pattern_is_flagged():
    comment = _render(Classification(1, ()), unmatched=(("api_contract", "app/schema/**"),))

    assert "Padrão `app/schema/**` da regra `api_contract` não casa nenhum arquivo" in comment


def test_nothing_detected_still_reminds_what_machine_cannot_know():
    comment = _render(Classification(1, ()))

    section = _section(comment, "### Incertezas")
    assert "Nada detectado automaticamente." in section
    assert "intenção" in section
