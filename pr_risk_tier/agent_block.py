import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

BLOCK_PATTERN = re.compile(r"<!--\s*pr-risk-tier\s+(.*?)-->", re.DOTALL)
TEST_SEPARATOR = "::"


@dataclass(frozen=True)
class Invariant:
    rule: str
    test: str


@dataclass(frozen=True)
class AgentReport:
    intent: str
    summary: str
    consumers: tuple[str, ...]
    invariants: tuple[Invariant, ...]
    unknowns: tuple[str, ...]


@dataclass(frozen=True)
class AgentBlock:
    report: AgentReport | None
    errors: tuple[str, ...]


@dataclass(frozen=True)
class InvariantCheck:
    invariant: Invariant
    problem: str | None


def parse_agent_block(body: str | None) -> AgentBlock | None:
    match = BLOCK_PATTERN.search(body or "")
    if match is None:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        return AgentBlock(
            None,
            (f"JSON inválido na linha {error.lineno}, coluna {error.colno}: {error.msg}.",),
        )
    if not isinstance(data, dict):
        return AgentBlock(None, ("O bloco deve ser um objeto JSON.",))

    errors = [
        *_required_text(data, "intent"),
        *_required_text(data, "summary"),
        *_text_list(data, "consumers"),
        *_text_list(data, "unknowns"),
        *_invariant_errors(data.get("invariants", [])),
    ]
    if errors:
        return AgentBlock(None, tuple(errors))
    return AgentBlock(
        AgentReport(
            intent=data["intent"],
            summary=data["summary"],
            consumers=tuple(data.get("consumers", [])),
            invariants=tuple(
                Invariant(item["rule"], item["test"]) for item in data.get("invariants", [])
            ),
            unknowns=tuple(data.get("unknowns", [])),
        ),
        (),
    )


def check_invariants(invariants: Iterable[Invariant], root: Path) -> tuple[InvariantCheck, ...]:
    return tuple(InvariantCheck(invariant, _problem(invariant, root)) for invariant in invariants)


def _problem(invariant: Invariant, root: Path) -> str | None:
    path, separator, name = invariant.test.partition(TEST_SEPARATOR)
    if not separator or not path or not name:
        return "formato esperado: arquivo::nome do teste"
    root = root.resolve()
    file = (root / path).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        return "arquivo não encontrado"
    if name not in file.read_text(encoding="utf-8", errors="replace"):
        return "teste não encontrado no arquivo"
    return None


def _required_text(data: dict, field: str) -> list[str]:
    value = data.get(field)
    if isinstance(value, str) and value.strip():
        return []
    return [f"'{field}' é obrigatório e deve ser um texto."]


def _text_list(data: dict, field: str) -> list[str]:
    value = data.get(field, [])
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return []
    return [f"'{field}' deve ser uma lista de textos."]


def _invariant_errors(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["'invariants' deve ser uma lista."]
    errors = []
    for position, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            errors.append(f"Invariante #{position}: deve ser um objeto com 'rule' e 'test'.")
            continue
        for field in ("rule", "test"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(
                    f"Invariante #{position}: '{field}' é obrigatório e deve ser um texto."
                )
    return errors
