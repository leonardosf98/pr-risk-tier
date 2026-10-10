import json

from pr_risk_tier.agent_block import (
    AgentReport,
    Invariant,
    check_invariants,
    parse_agent_block,
)

VALID = {
    "intent": "Permitir importar talhão por shapefile",
    "summary": "Novo modo Arquivo no formulário de área.",
    "consumers": ["src/components/LocationForm.vue"],
    "invariants": [
        {"rule": "Não salva geometria antiga", "test": "tests/test_form.py::test_keeps_old"}
    ],
    "unknowns": ["Só testado no Chrome."],
}


def _body(payload) -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"## Descrição\n\nTexto da PR.\n\n<!-- pr-risk-tier\n{text}\n-->\n"


def test_body_without_block_is_absent():
    assert parse_agent_block(None) is None
    assert parse_agent_block("") is None
    assert parse_agent_block("<!-- outro comentário -->") is None
    assert parse_agent_block("<!-- pr-risk-tier:comment -->") is None


def test_valid_block_becomes_report():
    block = parse_agent_block(_body(VALID))

    assert block.errors == ()
    assert block.report == AgentReport(
        intent="Permitir importar talhão por shapefile",
        summary="Novo modo Arquivo no formulário de área.",
        consumers=("src/components/LocationForm.vue",),
        invariants=(Invariant("Não salva geometria antiga", "tests/test_form.py::test_keeps_old"),),
        unknowns=("Só testado no Chrome.",),
    )


def test_optional_fields_default_to_empty():
    block = parse_agent_block(_body({"intent": "a", "summary": "b"}))

    assert block.report == AgentReport("a", "b", (), (), ())


def test_broken_json_reports_position_in_portuguese():
    block = parse_agent_block(_body('{"intent": "a",\n "summary": }'))

    assert block.report is None
    assert len(block.errors) == 1
    assert "JSON inválido" in block.errors[0]
    assert "linha 2" in block.errors[0]


def test_block_must_be_an_object():
    block = parse_agent_block(_body("[]"))

    assert block.report is None
    assert block.errors == ("O bloco deve ser um objeto JSON.",)


def test_each_problem_becomes_one_error():
    block = parse_agent_block(
        _body(
            {
                "summary": "b",
                "unknowns": "nenhuma",
                "consumers": [1],
                "invariants": [{"rule": "r"}, "x"],
            }
        )
    )

    assert block.report is None
    assert block.errors == (
        "'intent' é obrigatório e deve ser um texto.",
        "'consumers' deve ser uma lista de textos.",
        "'unknowns' deve ser uma lista de textos.",
        "Invariante #1: 'test' é obrigatório e deve ser um texto.",
        "Invariante #2: deve ser um objeto com 'rule' e 'test'.",
    )


def test_invariant_with_existing_test_has_no_problem(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_form.py").write_text("def test_keeps_old():\n    pass\n")

    [check] = check_invariants((Invariant("r", "tests/test_form.py::test_keeps_old"),), tmp_path)

    assert check.problem is None


def test_invariant_problems(tmp_path):
    (tmp_path / "a.spec.ts").write_text("it('keeps the typed name', () => {})\n")
    (tmp_path.parent / "outside.py").write_text("def test_x(): pass\n")

    checks = check_invariants(
        (
            Invariant("r1", "missing.py::test_x"),
            Invariant("r2", "a.spec.ts::keeps the old name"),
            Invariant("r3", "a.spec.ts"),
            Invariant("r4", "../outside.py::test_x"),
            Invariant("r5", "a.spec.ts::keeps the typed name"),
        ),
        tmp_path,
    )

    assert [check.problem for check in checks] == [
        "arquivo não encontrado",
        "teste não encontrado no arquivo",
        "formato esperado: arquivo::nome do teste",
        "arquivo não encontrado",
        None,
    ]


def test_blank_texts_are_rejected():
    block = parse_agent_block(
        _body({"intent": "  ", "summary": "b", "invariants": [{"rule": " ", "test": "a::b"}]})
    )

    assert block.errors == (
        "'intent' é obrigatório e deve ser um texto.",
        "Invariante #1: 'rule' é obrigatório e deve ser um texto.",
    )
