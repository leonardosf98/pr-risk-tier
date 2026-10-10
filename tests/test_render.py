from pr_risk_tier.agent_block import AgentBlock, AgentReport, Invariant, InvariantCheck
from pr_risk_tier.classify import DEFAULT_REASON_ID, Classification, Reason
from pr_risk_tier.evidence import Evidence, FileMix, JobResult, Size
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

INVARIANT = Invariant("Não salva geometria antiga", "tests/test_form.py::test_keeps_old")
REPORT = AgentReport(
    intent="Permitir importar talhão por shapefile",
    summary="Novo modo Arquivo no formulário.",
    consumers=("src/components/LocationForm.vue", "app mobile"),
    invariants=(INVARIANT,),
    unknowns=("Só testado no Chrome.",),
)
VALID_BLOCK = AgentBlock(report=REPORT, errors=())
PASSING_JOB = JobResult("Lint and test", "success", "https://ci/1", ())
SMALL_DIFF = Size(10, 2, 400, enforced=False)
CODE_AND_TEST = FileMix(code=1, tests=1, inert=0)


def _evidence(
    *,
    size=SMALL_DIFF,
    mix=CODE_AND_TEST,
    jobs=(PASSING_JOB,),
    unmatched=(),
    agent=None,
    invariant_checks=(),
):
    return Evidence(
        size=size,
        mix=mix,
        jobs=jobs,
        unmatched=unmatched,
        agent=agent,
        invariant_checks=invariant_checks,
    )


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


def test_missing_agent_block_is_flagged_in_change_and_unknowns():
    comment = _render(Classification(1, ()))

    assert "Pacote do agente ausente" in _section(comment, "### Mudança")
    unknowns = _section(comment, "### Incertezas")
    assert "⚠️ Incertezas não declaradas por quem escreveu a PR." in unknowns
    assert "Nada detectado" not in comment


def test_change_section_comes_first():
    comment = _render(Classification(1, ()), agent=VALID_BLOCK)

    assert comment.index("### Mudança") < comment.index("### Por que tier 1")


def test_agent_report_fills_change_section():
    comment = _render(Classification(1, ()), agent=VALID_BLOCK)

    section = _section(comment, "### Mudança")
    assert "**Intenção:** Permitir importar talhão por shapefile" in section
    assert "Novo modo Arquivo no formulário." in section
    assert "**Quem consome:** src/components/LocationForm.vue · app mobile" in section


def test_declared_and_detected_unknowns_are_grouped():
    comment = _render(
        Classification(1, ()), agent=VALID_BLOCK, mix=FileMix(code=2, tests=0, inert=0)
    )

    section = _section(comment, "### Incertezas")
    declared_at = section.index("**Declaradas por quem escreveu:**")
    detected_at = section.index("**Detectadas pela máquina:**")
    assert declared_at < section.index("- Só testado no Chrome.") < detected_at
    assert section.index("sem nenhum teste alterado") > detected_at


def test_empty_declared_unknowns_from_tier_one_are_suspicious():
    report = AgentReport("a", "b", (), (), ())
    comment = _render(Classification(1, ()), agent=AgentBlock(report, ()))

    assert "Nenhuma incerteza declarada por quem escreveu a PR — desconfie." in comment


def test_empty_declared_unknowns_on_tier_zero_are_fine():
    report = AgentReport("a", "b", (), (), ())
    comment = _render(Classification(0, ()), agent=AgentBlock(report, ()))

    assert "desconfie" not in comment
    assert "Nenhuma incerteza." in _section(comment, "### Incertezas")


def test_invalid_agent_block_lists_errors():
    block = AgentBlock(report=None, errors=("'intent' é obrigatório e deve ser um texto.",))
    comment = _render(Classification(1, ()), agent=block)

    section = _section(comment, "### Mudança")
    assert "❌ Bloco do agente inválido" in section
    assert "- 'intent' é obrigatório e deve ser um texto." in section
    assert "Incertezas não declaradas" in _section(comment, "### Incertezas")


def test_invariants_become_evidence_rows():
    missing = Invariant("Limite de área", "tests/test_limits.py::test_gone")
    comment = _render(
        Classification(1, ()),
        agent=VALID_BLOCK,
        invariant_checks=(
            InvariantCheck(INVARIANT, None),
            InvariantCheck(missing, "teste não encontrado no arquivo"),
        ),
    )

    section = _section(comment, "### Evidência")
    assert (
        "| Invariante · Não salva geometria antiga | ✅ teste encontrado: "
        "`tests/test_form.py::test_keeps_old` |" in section
    )
    assert (
        "| Invariante · Limite de área | ❌ teste não encontrado no arquivo: "
        "`tests/test_limits.py::test_gone` |" in section
    )


def test_agent_block_without_invariants_says_so():
    report = AgentReport("a", "b", (), (), ("x",))
    comment = _render(Classification(1, ()), agent=AgentBlock(report, ()))

    assert "| Invariantes | ⚠️ nenhuma declarada |" in comment
