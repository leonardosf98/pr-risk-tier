import json

from pr_risk_tier.__main__ import main
from pr_risk_tier.render import MARKER

RULES = """
test_paths = ["src/**/__tests__/**"]

[[rule]]
id = "api_contract"
tier = 2
paths = ["src/api/**"]
"""

JOBS = {
    "jobs": [
        {
            "name": "ci",
            "status": "completed",
            "conclusion": "failure",
            "html_url": "https://ci/2",
            "steps": [{"name": "npm audit", "conclusion": "failure"}],
        },
        {"name": "evidence", "status": "in_progress", "conclusion": None, "html_url": "u"},
    ]
}


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def _run(tmp_path, *extra, numstat="7\t1\tsrc/api/locations.ts\n\n2\t0\tsrc/views/Home.vue\n"):
    output = tmp_path / "evidence.md"
    code = main(
        [
            "--rules",
            _write(tmp_path, "rules.toml", RULES),
            "--numstat",
            _write(tmp_path, "numstat.txt", numstat),
            "--output",
            str(output),
            *extra,
        ]
    )
    return code, output


def test_writes_comment_and_exits_zero(tmp_path):
    code, output = _run(tmp_path)

    assert code == 0
    comment = output.read_text()
    assert comment.startswith(MARKER)
    assert "Tier 2" in comment
    assert "`src/views/Home.vue`" in comment
    assert "10 linhas (+9 −1) · limite do tier 2: 400 ✅" in comment
    assert "2 arquivo(s) de código sem nenhum teste alterado" in comment
    assert "``" not in comment


def test_jobs_file_feeds_ci_evidence(tmp_path):
    jobs = _write(tmp_path, "jobs.json", json.dumps(JOBS))

    code, output = _run(tmp_path, "--jobs", jobs)

    comment = output.read_text()
    assert code == 0
    assert "❌ falhou em `npm audit`" in comment
    assert "evidence" not in comment.split("### Evidência")[1].split("### Incertezas")[0]


def test_missing_jobs_file_means_ci_unavailable(tmp_path):
    code, output = _run(tmp_path, "--jobs", str(tmp_path / "absent.json"))

    assert code == 0
    assert "| CI | ⚠️ indisponível |" in output.read_text()


def test_repo_files_feed_unmatched_patterns(tmp_path):
    repo_files = _write(tmp_path, "repo-files.txt", "src/views/Home.vue\nREADME.md\n")

    _, output = _run(tmp_path, "--repo-files", repo_files)

    assert "Padrão `src/api/**` da regra `api_contract`" in output.read_text()


def _block(invariant_test: str) -> str:
    payload = {
        "intent": "Importar talhão",
        "summary": "Novo modo.",
        "invariants": [{"rule": "Não salva geometria antiga", "test": invariant_test}],
        "unknowns": ["Só no Chrome."],
    }
    return f"Descrição\n\n<!-- pr-risk-tier\n{json.dumps(payload)}\n-->\n"


def _repo(tmp_path):
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "tests/test_form.py").write_text("def test_keeps_old():\n    pass\n")
    return str(root)


def test_missing_body_flags_undeclared_unknowns(tmp_path):
    code, output = _run(tmp_path)

    assert code == 0
    assert "Incertezas não declaradas por quem escreveu a PR" in output.read_text()


def test_valid_block_with_existing_test_exits_zero(tmp_path):
    body = _write(tmp_path, "body.md", _block("tests/test_form.py::test_keeps_old"))

    code, output = _run(tmp_path, "--body", body, "--repo-root", _repo(tmp_path))

    comment = output.read_text()
    assert code == 0
    assert "**Intenção:** Importar talhão" in comment
    assert "🔎 teste existe, ainda não provado: `tests/test_form.py::test_keeps_old`" in comment


def test_invariant_citing_missing_test_fails_but_writes_comment(tmp_path, capsys):
    body = _write(tmp_path, "body.md", _block("tests/test_form.py::test_imaginary"))

    code, output = _run(tmp_path, "--body", body, "--repo-root", _repo(tmp_path))

    assert code == 1
    assert "❌ teste não encontrado no arquivo" in output.read_text()
    assert "test_imaginary" in capsys.readouterr().err


def test_invalid_block_fails_but_writes_comment(tmp_path):
    body = _write(tmp_path, "body.md", "<!-- pr-risk-tier\n{oops}\n-->")

    code, output = _run(tmp_path, "--body", body, "--repo-root", _repo(tmp_path))

    assert code == 1
    assert "❌ Bloco do agente inválido" in output.read_text()


def test_invalid_rules_exit_non_zero_with_message(tmp_path, capsys):
    output = tmp_path / "evidence.md"

    code = main(
        [
            "--rules",
            _write(tmp_path, "rules.toml", '[[rule]]\nid = "x"\n'),
            "--numstat",
            _write(tmp_path, "numstat.txt", ""),
            "--output",
            str(output),
        ]
    )

    assert code == 2
    assert "tier" in capsys.readouterr().err
    assert not output.exists()


def test_missing_rules_file_exit_non_zero(tmp_path, capsys):
    numstat = _write(tmp_path, "numstat.txt", "")

    code = main(["--rules", str(tmp_path / "nope.toml"), "--numstat", numstat, "--output", "x.md"])

    assert code == 2
    assert "nope.toml" in capsys.readouterr().err
